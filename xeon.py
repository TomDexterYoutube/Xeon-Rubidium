import sys
import os
import re
import subprocess
import shutil
import time
import json
import urllib.request
import urllib.error
from pathlib import Path


# Resolve the ~/.xeon directory
XEON_DIR = Path.home() / ".xeon"

COMPILER_SCRIPT = XEON_DIR / "compiler.py"
DEBUGGER_SCRIPT = XEON_DIR / "debug.py"

# Vire — the FFI compatibility layer. A .vire file always compiles to a
# shared library (it has no entry point of its own). Vire's toolchain is
# the same shape as Rubidium's own (compiler.py + debug.py, each importing
# lexer.py/parser.py/rub_ast.py/codegen.py from their own directory) — it
# lives in its own ~/.xeon/vire/ subfolder rather than dumped directly into
# ~/.xeon/, since its lexer.py/parser.py/rub_ast.py/codegen.py would
# otherwise collide with Rubidium's identically-named ones sitting there.
VIRE_DIR = XEON_DIR / "vire"
VIRE_COMPILER_SCRIPT = VIRE_DIR / "compiler.py"
VIRE_DEBUGGER_SCRIPT = VIRE_DIR / "debug.py"

# ─────────────────────────────────────────────────────────────
# Package manager (xeon pkg) config
# ─────────────────────────────────────────────────────────────

PKG_REPO_OWNER  = "TomDexterYoutube"
PKG_REPO_NAME   = "xeon-pkgs"
PKG_REPO_BRANCH = "main"
PKG_RAW_BASE = f"https://raw.githubusercontent.com/{PKG_REPO_OWNER}/{PKG_REPO_NAME}/{PKG_REPO_BRANCH}"
PKG_API_BASE = f"https://api.github.com/repos/{PKG_REPO_OWNER}/{PKG_REPO_NAME}/contents"

# BUGFIX: this used to be "xeon", a repo that doesn't exist (confirmed via
# the GitHub API — 404) — every 'python3 xeon.py update' silently failed to
# update anything from it. In normal usage this whole function is actually
# unreachable (install.sh's generated ~/.local/bin/xeon wrapper intercepts
# "update" itself, in bash, before ever calling into xeon.py — see that
# script), but it's still the real behavior for anyone invoking
# `python3 xeon.py update` directly, so it needs to point at a real repo:
# the actual Rubidium compiler lives in the "Rubidium" repo, not "xeon".
CORE_REPO_NAME  = "Rubidium"
CORE_RAW_BASE   = f"https://raw.githubusercontent.com/{PKG_REPO_OWNER}/{CORE_REPO_NAME}/{PKG_REPO_BRANCH}"
# Everything compiler.py/debug.py need to actually run stand-alone from
# ~/.xeon — they import lexer/parser/rub_ast/codegen from their own
# directory, so fetching only the first two (the old behavior here) left
# ~/.xeon unable to run either one at all.
RUBIDIUM_TOOLCHAIN_FILES = ("compiler.py", "debug.py", "lexer.py", "parser.py", "rub_ast.py", "codegen.py")

# xeon.py's own CLI script lives in a SEPARATE repo from the compiler
# (mirrors XEON_URL vs REPO_URL in install.sh) — not CORE_REPO_NAME/
# CORE_RAW_BASE above, which is the Rubidium compiler's repo.
XEON_CLI_REPO_NAME = "Xeon-Rubidium"
XEON_CLI_RAW_BASE  = f"https://raw.githubusercontent.com/{PKG_REPO_OWNER}/{XEON_CLI_REPO_NAME}/{PKG_REPO_BRANCH}"

# Vire's own repo — same owner/branch convention as the core Rubidium repo
# above, just a different name.
VIRE_REPO_NAME = "Rubidium-Vire"
VIRE_RAW_BASE  = f"https://raw.githubusercontent.com/{PKG_REPO_OWNER}/{VIRE_REPO_NAME}/{PKG_REPO_BRANCH}"
# Same reasoning as RUBIDIUM_TOOLCHAIN_FILES above — Vire's compiler.py
# needs its own lexer/parser/rub_ast/codegen sitting alongside it too.
VIRE_TOOLCHAIN_FILES = ("compiler.py", "debug.py", "lexer.py", "parser.py", "rub_ast.py", "codegen.py")

PKG_LIST_PATH  = XEON_DIR / "pkg-list"
PACKAGES_DIR   = XEON_DIR / "packages"
PKG_LIST_STALE_SECONDS = 24 * 60 * 60  # re-fetch if local pkg-list is older than this
TOKEN_PATH = XEON_DIR / "token"  # GitHub personal access token, set via 'xeon auth <token>'


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _require_src():
    if not os.path.exists("src"):
        print("✖ No src/ directory found. Run 'xeon init' first.")
        sys.exit(1)

    main_file = "src/main.rub"

    if not os.path.exists(main_file):
        print(f"✖ Entry point '{main_file}' not found.")
        sys.exit(1)

    return main_file


def _require_compiler():
    if not COMPILER_SCRIPT.exists():
        print(f"✖ Compiler not found at {COMPILER_SCRIPT}")
        print("  Please ensure Rubidium is installed in ~/.xeon")
        sys.exit(1)


def _require_vire_compiler():
    if not VIRE_COMPILER_SCRIPT.exists():
        print(f"✖ Vire compiler not found at {VIRE_COMPILER_SCRIPT}")
        print(f"  Please ensure Vire is installed in {VIRE_DIR}")
        sys.exit(1)


def _shared_lib_ext():
    if os.name == "nt":
        return ".dll"
    if sys.platform == "darwin":
        return ".dylib"
    return ".so"


def _compile_vire_files(build_dir):
    """Find every .vire source under src/ and compile each one straight
    into build/ at the same relative path (mirrored to a shared-lib
    extension) — a .vire file's only output IS a wrapper .so, so this both
    "compiles them" and "copies over the produced .so" in one step: the
    compiler writes directly to where the .rub compile step below expects
    an FFI("...") target to already be. Runs BEFORE the src/ .so/.dll/
    .dylib bundling loop and BEFORE the main Rubidium compile, so by the
    time the real program is built, every wrapper it might FFI-load is
    already sitting in build/ next to it.
    """
    vire_files = []
    for root, _, files in os.walk("src"):
        for fname in files:
            if fname.endswith(".vire"):
                vire_files.append(Path(root) / fname)

    if not vire_files:
        return 0

    _require_vire_compiler()
    so_ext = _shared_lib_ext()

    for vire_path in vire_files:
        rel_path = vire_path.relative_to("src")
        out_path = build_dir / rel_path.with_suffix(so_ext)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Compiling Vire wrapper {rel_path} → build/{rel_path.with_suffix(so_ext)}...")
        sys.stdout.flush()   # see the flush() note in run_debugger() — same reason

        # Vire has no entry point of its own (see the EXECUTION MODEL
        # section of its syntax reference) — every .vire build is a
        # shared library, so -s isn't optional here the way it is for -s
        # on the Rubidium side.
        cmd = [sys.executable, str(VIRE_COMPILER_SCRIPT), "-s", str(vire_path), str(out_path)]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"✖ Vire build failed for {rel_path}.")
            sys.exit(1)

    print(f"  {len(vire_files)} Vire wrapper(s) compiled")
    return len(vire_files)


_FFI_CALL_RE = re.compile(r'FFI\(\s*"([^"]+)"\s*\)')


def _collect_ffi_lib_paths():
    """Scan every .rub/.vire source file under src/ for FFI("path") calls
    with a literal string path, returning the set of distinct relative
    paths actually referenced anywhere in the project (both languages —
    a .rub can FFI-load a .vire-compiled wrapper, and a .vire can FFI-load
    a real C library, and either can reference either). A plain regex
    scan rather than a real parse: FFI("...") is a simple, fixed literal
    pattern, and this only needs to find candidate strings, not fully
    understand the source — the real compiler still catches anything a
    loose regex match gets wrong when it actually builds."""
    paths = set()
    for root, _, files in os.walk("src"):
        for fname in files:
            if fname.endswith((".rub", ".vire")):
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(errors="replace")
                except OSError:
                    continue
                for m in _FFI_CALL_RE.finditer(text):
                    paths.add(m.group(1))
    return paths


def _bundle_ffi_libs(build_dir):
    """Copy only the .so/.dll/.dylib files an FFI("path") call somewhere in
    src/ (.rub or .vire) ACTUALLY references — at that exact path, any
    depth of subfolders — instead of blindly copying every shared library
    sitting anywhere under src/ regardless of whether anything uses it.
    Looks for the real file at src/<path> (the established convention: a
    lib referenced as FFI("lib/foo.so") lives at src/lib/foo.so during
    development) and copies it to build/<path>, preserving that same
    structure so the relative path still resolves once the compiled
    binary later runs with build/ (or its own directory — see ffi_load's
    exe-relative fallback) reachable the same way.
    """
    ffi_paths = _collect_ffi_lib_paths()
    bundled = 0
    missing = []
    for rel in sorted(ffi_paths):
        if not rel.endswith((".so", ".dll", ".dylib")):
            continue  # not a bundle-able file target (a bare/versioned
                       # library name resolved at runtime some other way)
        src_path = Path("src") / rel
        if not src_path.exists():
            # A .vire-produced wrapper (e.g. FFI("wrapper.so") backed by
            # src/wrapper.vire) has nothing to copy here — _compile_vire_
            # files already placed the REAL build/wrapper.so; this path
            # just never had a matching file under src/ to begin with.
            vire_source = src_path.with_suffix(".vire")
            if not vire_source.exists():
                missing.append(rel)
            continue
        dst_path = build_dir / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        print(f"  bundled FFI lib → build/{rel}")
        bundled += 1

    if bundled:
        print(f"  {bundled} FFI library file(s) bundled")
    if missing:
        print(f"  Note: FFI path(s) referenced in code but not found under src/: {', '.join(missing)}")
    return bundled


def run_debugger(main_file):
    if not DEBUGGER_SCRIPT.exists():
        print("⚠ Debugger not found. Skipping debug checks.")
        return

    # BUG: debug.py doesn't just analyze — it actually INTERPRETS the
    # program (every print() in the source runs for real, and for a game
    # that means it opens windows / runs full frames / reads input) before
    # the compiler even starts. With no visual boundary around that block,
    # its output was indistinguishable from the real compiled run that
    # follows later — for a game especially, seeing gameplay text scroll by
    # with no indication it isn't the real run is actively misleading.
    # Bracket it clearly so it's obvious where the debugger's own simulated
    # execution starts and ends.
    banner = "═" * 60
    print(f"\n{banner}")
    print("🔍 DEBUGGER — this executes your program's code once to check")
    print("   for errors; anything it prints below is from THAT run, not")
    print("   from the real compiled program.")
    print(banner)
    # BUG (compounds the one above): subprocess.run() lets the child write
    # DIRECTLY to the inherited stdout fd, bypassing Python's own buffering
    # for this process entirely. When xeon's stdout isn't a terminal (piped,
    # redirected to a file, or — how this was actually found — captured by
    # any wrapper/CI), our print() calls above sit in a buffer while the
    # child's output goes straight through, so the banner meant to appear
    # BEFORE the debugger's output showed up AFTER it instead. Flushing
    # before handing off (and after getting control back) makes the
    # boundary correct regardless of what stdout is connected to.
    sys.stdout.flush()

    res = subprocess.run(
        [sys.executable, str(DEBUGGER_SCRIPT), main_file]
    )

    sys.stdout.flush()
    print(banner)
    print("🔍 END DEBUGGER OUTPUT")
    print(f"{banner}\n")
    sys.stdout.flush()

    if res.returncode != 0:
        print("✖ Debugger found issues.")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────

def init_project():
    if os.path.exists("src"):
        print("✖ Project already initialized (src/ exists).")
        return

    os.makedirs("src")

    with open("src/main.rub", "w") as f:
        f.write(
            'fn main() {\n'
            '    print("I\'m working fine!")\n'
            '    print("Ready to start coding?")\n'
            '}\n'
        )

    print("✔ Initialized new Rubidium project in ./src")


def check_project():
    main_file = _require_src()

    if not DEBUGGER_SCRIPT.exists():
        print(f"✖ Debugger not found at {DEBUGGER_SCRIPT}")
        sys.exit(1)

    # BUGFIX (RIG brain project): debug.py's argparse only accepts a single
    # positional <file.rub> (+ --strict) — there's no "check" subcommand on
    # that side. Passing "check" here as an extra positional made every
    # `xeon check` fail outright with "unrecognized arguments", regardless
    # of the project being checked.
    res = subprocess.run(
        [sys.executable, str(DEBUGGER_SCRIPT), main_file]
    )

    sys.exit(res.returncode)


def build_project(no_debug=False, shared=False, native=None):
    main_file = _require_src()
    _require_compiler()

    if not no_debug:
        run_debugger(main_file)

    build_dir = Path("build")

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.mkdir(parents=True)

    _compile_vire_files(build_dir)

    # syntax: FFI — only the libraries an FFI("path") call somewhere in
    # src/ actually references get bundled (see _bundle_ffi_libs), not
    # every .so/.dll/.dylib sitting anywhere under src/ regardless of use.
    _bundle_ffi_libs(build_dir)

    project_name = Path.cwd().name

    out_name = build_dir / project_name

    if shared:
        if os.name == "nt":
            out_name = out_name.with_suffix(".dll")
        elif sys.platform == "darwin":
            out_name = out_name.with_suffix(".dylib")
        else:
            out_name = out_name.with_suffix(".so")
    elif os.name == "nt":
        out_name = out_name.with_suffix(".exe")

    kind = "shared library" if shared else "executable"
    print(f"Compiling {project_name} ({kind})...")
    sys.stdout.flush()   # see the flush() note in run_debugger() — same bug,
                          # same fix: without this, "Compiling..." could show
                          # up AFTER the compiler subprocess's own output.

    cmd = [sys.executable, str(COMPILER_SCRIPT)]
    if shared:
        cmd.append("-s")
    if native:
        cmd += ["--native", native]
    cmd += [main_file, str(out_name)]

    res = subprocess.run(cmd)

    if res.returncode != 0:
        print("✖ Build failed.")
        sys.exit(1)

    print("✔ Build complete")

    return str(out_name)


def run_project(no_debug=False, shared=False, native=None):
    if shared:
        print("✖ 'run' doesn't apply to a shared library build (-s) — there's no entry point to execute.")
        print("  Use 'xeon build -s' and load the resulting library via FFI instead.")
        sys.exit(1)

    out_name = build_project(no_debug=no_debug, native=native)

    banner = "═" * 60
    print(f"\n{banner}")
    print(f"▶ RUNNING {out_name} — this is the real compiled program.")
    print(banner)
    sys.stdout.flush()   # see the matching flush() note in run_debugger()

    run_cmd = (
        [f"./{out_name}"]
        if os.name != "nt"
        else [out_name]
    )

    try:
        subprocess.run(run_cmd)
    except KeyboardInterrupt:
        print("\nProgram terminated.")
    finally:
        sys.stdout.flush()
        print(banner)


def xeon_update():
    """Updates the Xeon core toolchain files and attempts to update the CLI script itself."""
    print("🔄 Updating Xeon toolchain and CLI...")
    XEON_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Update core backend scripts (compiler.py/debug.py AND their own
    # lexer/parser/rub_ast/codegen dependencies — see RUBIDIUM_TOOLCHAIN_FILES)
    for script_name in RUBIDIUM_TOOLCHAIN_FILES:
        url = f"{CORE_RAW_BASE}/{script_name}"
        dest_path = XEON_DIR / script_name
        print(f"  Fetching latest {script_name}...")
        try:
            _http_download(url, dest_path)
            print(f"  ✔ Updated {script_name}")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"  ✖ Failed to update {script_name}: {e}")

    # 2. Update the Vire toolchain, into its own subfolder (see VIRE_DIR).
    VIRE_DIR.mkdir(parents=True, exist_ok=True)
    for script_name in VIRE_TOOLCHAIN_FILES:
        url = f"{VIRE_RAW_BASE}/{script_name}"
        dest_path = VIRE_DIR / script_name
        print(f"  Fetching latest vire/{script_name}...")
        try:
            _http_download(url, dest_path)
            print(f"  ✔ Updated vire/{script_name}")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"  ✖ Failed to update vire/{script_name}: {e}")

    # 3. Attempt to update the running CLI executable script itself — its
    # own repo (Xeon-Rubidium), not CORE_RAW_BASE (the compiler's repo).
    current_script = Path(sys.argv[0]).resolve()
    script_url = f"{XEON_CLI_RAW_BASE}/xeon.py"
    print("  Fetching latest xeon CLI script...")
    try:
        data = _http_get_bytes(script_url)
        try:
            current_script.write_bytes(data)
            print("  ✔ Updated xeon CLI script itself!")
        except OSError:
            fallback_path = XEON_DIR / "xeon.py"
            fallback_path.write_bytes(data)
            print(f"  ⚠ Could not overwrite {current_script} directly. Latest CLI saved to {fallback_path}")
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"  ✖ Failed to fetch latest xeon CLI script: {e}")

    print("✔ Xeon update execution finished.")


# ─────────────────────────────────────────────────────────────
# Package manager (xeon pkg) — HTTP helpers
# ─────────────────────────────────────────────────────────────

def _load_token():
    if TOKEN_PATH.exists():
        tok = TOKEN_PATH.read_text().strip()
        return tok or None
    return None


def _warn_if_no_token():
    if _load_token() is None:
        print("⚠ No GitHub token set (60 req/hour limit, shared per IP). "
              "Run 'xeon auth <token>' to raise it to 5000/hour. "
              "Run 'xeon pkg help' for details.")


def _http_get_bytes(url):
    headers = {"User-Agent": "xeon-pkg-manager"}
    token = _load_token()
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def _http_get_text(url):
    return _http_get_bytes(url).decode("utf-8")


def _http_get_json(url):
    return json.loads(_http_get_text(url))


def _http_download(url, dest_path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _http_get_bytes(url)
    with open(dest_path, "wb") as f:
        f.write(data)


# ─────────────────────────────────────────────────────────────
# Package manager — pkg-list parsing & version comparison
# ─────────────────────────────────────────────────────────────

def _parse_pkg_list(text):
    """'name|major.minor.patch' per line -> {name: version_str}"""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            continue
        name, version = line.split("|", 1)
        result[name.strip()] = version.strip()
    return result


def _parse_version(version_str):
    parts = version_str.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"invalid version '{version_str}' (expected major.minor.patch)")
    return tuple(int(p) for p in parts)


def _version_is_newer(remote_str, local_str):
    try:
        return _parse_version(remote_str) > _parse_version(local_str)
    except ValueError:
        return False


def _pkg_list_is_stale():
    """Missing entirely, or older than PKG_LIST_STALE_SECONDS."""
    if not PKG_LIST_PATH.exists():
        return True
    age = time.time() - PKG_LIST_PATH.stat().st_mtime
    return age > PKG_LIST_STALE_SECONDS


def _load_local_pkg_list():
    if not PKG_LIST_PATH.exists():
        return {}
    return _parse_pkg_list(PKG_LIST_PATH.read_text())


# ─────────────────────────────────────────────────────────────
# Package manager — commands
# ─────────────────────────────────────────────────────────────

def pkg_fetch(quiet=False):
    if not quiet:
        print("Fetching latest pkg-list...")
    url = f"{PKG_RAW_BASE}/pkg-list"
    try:
        text = _http_get_text(url)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"✖ Failed to fetch pkg-list: {e}")
        sys.exit(1)

    XEON_DIR.mkdir(parents=True, exist_ok=True)
    PKG_LIST_PATH.write_text(text)

    if not quiet:
        count = len(_parse_pkg_list(text))
        print(f"✔ pkg-list updated ({count} package(s) available)")


def _ensure_pkg_list_fresh():
    """Auto-fetch behaviour shared by pull/upgrade: fetch if missing or stale."""
    if _pkg_list_is_stale():
        reason = "missing" if not PKG_LIST_PATH.exists() else "stale (>24h old)"
        print(f"pkg-list is {reason} — fetching automatically...")
        pkg_fetch(quiet=True)
        print("✔ pkg-list updated")


def _download_package_files(pkg_name, dest_dir):
    def _walk(repo_path, local_dir):
        api_url = f"{PKG_API_BASE}/{repo_path}?ref={PKG_REPO_BRANCH}"
        entries = _http_get_json(api_url)
        # BUG: the GitHub contents API returns a JSON OBJECT, not a list, on
        # every error response (rate limit exceeded, path not found, etc) —
        # e.g. {"message": "API rate limit exceeded ..."}. This iterated it
        # unconditionally as if it were always the list of directory
        # entries; iterating a dict yields its string KEYS, so entry["type"]
        # then raised "TypeError: string indices must be integers" — a
        # confusing crash with a Python traceback instead of the real,
        # actionable error (rate limit, wrong package name, etc).
        if isinstance(entries, dict):
            msg = entries.get("message", "unexpected response from GitHub API")
            raise RuntimeError(f"GitHub API error for '{repo_path}': {msg}")
        for entry in entries:
            if entry["type"] == "file":
                _http_download(entry["download_url"], local_dir / entry["name"])
            elif entry["type"] == "dir":
                _walk(f"{repo_path}/{entry['name']}", local_dir / entry["name"])

    # BUG: this used to rmtree(dest_dir) BEFORE downloading the replacement —
    # so a rate limit or dropped connection partway through 'xeon pkg
    # upgrade' deleted the currently-installed, working package and then
    # failed, leaving NOTHING installed (not even the old version). Download
    # into a fresh temp directory first, and only swap it into place once
    # every file has downloaded successfully; a failure now leaves the
    # existing install untouched.
    tmp_dir = dest_dir.parent / f".{dest_dir.name}.tmp-{os.getpid()}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    try:
        _walk(pkg_name, tmp_dir)
    except BaseException:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        raise
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    tmp_dir.rename(dest_dir)


def pkg_pull(pkg_name):
    if not pkg_name:
        print("✖ Usage: xeon pkg pull <package_name>")
        sys.exit(1)

    _ensure_pkg_list_fresh()

    remote_list = _load_local_pkg_list()
    if pkg_name not in remote_list:
        print(f"✖ Package '{pkg_name}' not found in pkg-list.")
        print("  Run 'xeon pkg fetch' to refresh the index, or check the package name.")
        sys.exit(1)

    print(f"Pulling '{pkg_name}' ({remote_list[pkg_name]})...")
    dest_dir = PACKAGES_DIR / pkg_name
    try:
        _download_package_files(pkg_name, dest_dir)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
        print(f"✖ Failed to download package '{pkg_name}': {e}")
        sys.exit(1)

    for required in ("pkg.rub", "pkg.info", "pkg.ver"):
        if not (dest_dir / required).exists():
            print(f"⚠ Warning: installed package is missing '{required}'")

    ver_path = dest_dir / "pkg.ver"
    if ver_path.exists():
        installed_ver = ver_path.read_text().strip()
        if installed_ver != remote_list[pkg_name]:
            print(f"⚠ Warning: pkg.ver ({installed_ver}) doesn't match pkg-list ({remote_list[pkg_name]})")

    print(f"✔ Installed '{pkg_name}' → {dest_dir}")


def pkg_purge(pkg_name):
    if not pkg_name:
        print("✖ Usage: xeon pkg purge <package_name>")
        sys.exit(1)

    dest_dir = PACKAGES_DIR / pkg_name
    if not dest_dir.exists():
        print(f"✖ Package '{pkg_name}' is not installed.")
        sys.exit(1)

    shutil.rmtree(dest_dir)
    print(f"✔ Removed '{pkg_name}'")


def pkg_upgrade(pkg_name=None):
    _ensure_pkg_list_fresh()
    remote_list = _load_local_pkg_list()

    if pkg_name:
        pkg_dir = PACKAGES_DIR / pkg_name
        if not pkg_dir.exists():
            print(f"✖ Package '{pkg_name}' is not installed.")
            sys.exit(1)
        targets = [pkg_dir]
    else:
        if not PACKAGES_DIR.exists() or not any(PACKAGES_DIR.iterdir()):
            print("No packages installed.")
            return
        targets = sorted(PACKAGES_DIR.iterdir())

    upgraded, unchanged, missing = 0, 0, 0

    for pkg_dir in targets:
        if not pkg_dir.is_dir():
            continue
        name = pkg_dir.name
        ver_path = pkg_dir / "pkg.ver"
        local_ver = ver_path.read_text().strip() if ver_path.exists() else None

        if name not in remote_list:
            print(f"  {name}: ⚠ not found in pkg-list (skipped)")
            missing += 1
            continue

        remote_ver = remote_list[name]

        if local_ver is None or _version_is_newer(remote_ver, local_ver):
            print(f"  {name}: {local_ver or '?'} → {remote_ver} (upgrading)")
            try:
                _download_package_files(name, pkg_dir)
                upgraded += 1
            except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
                print(f"    ✖ Failed to upgrade '{name}': {e}")
        else:
            print(f"  {name}: {local_ver} (up to date)")
            unchanged += 1

    print(f"\n✔ Upgrade complete — {upgraded} upgraded, {unchanged} up to date, {missing} skipped")


def pkg_list_all():
    """Lists all packages available in the fetched registry index."""
    _ensure_pkg_list_fresh()
    remote_list = _load_local_pkg_list()
    
    if not remote_list:
        print("No packages found in index. Try running 'xeon pkg fetch'.")
        return

    print("Available Packages (Registry Index):")
    for name, version in sorted(remote_list.items()):
        print(f"  {name} ({version})")


def pkg_list_installed():
    """Lists all locally installed packages inside ~/.xeon/packages/."""
    if not PACKAGES_DIR.exists() or not any(PACKAGES_DIR.iterdir()):
        print("No packages installed.")
        return

    print("Installed Packages:")
    for pkg_dir in sorted(PACKAGES_DIR.iterdir()):
        if not pkg_dir.is_dir():
            continue
        pkg_name = pkg_dir.name
        ver_path = pkg_dir / "pkg.ver"
        local_ver = ver_path.read_text().strip() if ver_path.exists() else "unknown version"
        print(f"  {pkg_name} ({local_ver})")


PKG_HELP = """\
Rubidium Package Manager (xeon pkg)

Commands:
  xeon pkg help              Show this help
  xeon pkg fetch              Download the latest package index (pkg-list)
  xeon pkg list-all          List all packages available in the remote index
  xeon pkg installed         List all currently installed packages
  xeon pkg pull <name>         Install a package (auto-fetches the index
                                first if missing or older than 24h)
  xeon pkg purge <name>        Remove an installed package
  xeon pkg upgrade [name]      Upgrade a specific package, or every installed
                                package if no name is specified

How it works:
  Packages are installed to ~/.xeon/packages/<name>/. Once installed, use
  them from Rubidium source with:

      xeon <package_name>
      print(<package_name>.some_value)

  This works like `import`, but resolves against an installed package
  instead of a relative file path, and supports aliasing:

      xeon <package_name> as <alias>

  Package repository: https://github.com/{owner}/{repo}

  Note: unauthenticated requests are limited to 60/hour per IP. Run
  'xeon auth <token>' to raise this to 5000/hour.
""".format(owner=PKG_REPO_OWNER, repo=PKG_REPO_NAME)


AUTH_HELP = """\
Usage: xeon auth <token>      Set your GitHub token
       xeon auth               Show current auth status
       xeon auth clear         Remove the stored token

A GitHub token raises the API rate limit used by 'xeon pkg' from
60 requests/hour (shared per IP, unauthenticated) to 5000/hour.

Create one at: https://github.com/settings/tokens
(a classic token with 'public_repo' read access is enough — xeon-pkgs is public)
"""


def handle_auth(args):
    if not args:
        token = _load_token()
        if token:
            masked = token[:4] + "…" + token[-4:] if len(token) > 8 else "****"
            print(f"✔ GitHub token is set ({masked})")
        else:
            print("No GitHub token set.")
            print(AUTH_HELP)
        return

    if args[0] in ("help", "-h", "--help"):
        print(AUTH_HELP)
        return

    if args[0] == "clear":
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
            print("✔ Token removed")
        else:
            print("No token was set.")
        return

    token = args[0]
    XEON_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token.strip())
    try:
        TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
    print("✔ GitHub token saved — 'xeon pkg' will now use it automatically")


def handle_pkg(args):
    if not args:
        print(PKG_HELP)
        sys.exit(1)

    subcmd = args[0]
    rest = args[1:]

    if subcmd == "help":
        print(PKG_HELP)
    elif subcmd == "fetch":
        _warn_if_no_token()
        pkg_fetch()
    elif subcmd == "list-all":
        pkg_list_all()
    elif subcmd == "installed":
        pkg_list_installed()
    elif subcmd == "pull":
        _warn_if_no_token()
        pkg_pull(rest[0] if rest else None)
    elif subcmd == "purge":
        pkg_purge(rest[0] if rest else None)
    elif subcmd == "upgrade":
        _warn_if_no_token()
        pkg_upgrade(rest[0] if rest else None)
    else:
        print(f"Unknown pkg command: {subcmd}\n")
        print(PKG_HELP)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

USAGE = """\
Usage: xeon <command> [options]

Commands:
  init          Create a new Rubidium project in ./src
  check         Run the static analyzer only
  build         Analyze, debug-check, then compile
  run           Build and run the project
  update        Update the Xeon core components and CLI execution script
  pkg           Manage packages (run 'xeon pkg help' for details)
  auth          Set a GitHub token to raise 'xeon pkg' rate limits
                (run 'xeon auth' with no args for details)

Options:
  --no-debug    Skip debugger checks during build/run
  -s            Compile as a shared library (.so/.dll/.dylib) with no
                entry point — exported fn's are callable via FFI from
                another language. Only valid with 'build' (not 'run').
  --native <mode>
                current   Tune for this exact machine's CPU (-march=native).
                          Fastest, but won't run on other machines.
                amd64     Generic 64-bit x86 (Intel or AMD) — no per-CPU
                          tuning, just works on any machine of that family.
                amd32     Generic 32-bit x86 (Intel or AMD), same idea.
                arm64     Generic 64-bit ARM (aarch64).
                arm32     Generic 32-bit ARM (armhf).
"""

NATIVE_CHOICES = ("current", "amd64", "amd32", "arm32", "arm64")


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    args = sys.argv[1:]

    if args[0] == "pkg":
        handle_pkg(args[1:])
        return

    if args[0] == "auth":
        handle_auth(args[1:])
        return

    no_debug = "--no-debug" in args
    shared   = "-s" in args

    native = None
    if "--native" in args:
        idx = args.index("--native")
        if idx + 1 >= len(args) or args[idx + 1] not in NATIVE_CHOICES:
            print(f"✖ --native requires one of: {', '.join(NATIVE_CHOICES)}")
            sys.exit(1)
        native = args[idx + 1]
        del args[idx:idx + 2]

    args = [
        arg
        for arg in args
        if arg not in ("--no-debug", "-s")
    ]

    if not args:
        print(USAGE)
        sys.exit(1)

    cmd = args[0]

    if cmd == "init":
        init_project()

    elif cmd == "check":
        check_project()

    elif cmd == "build":
        build_project(no_debug=no_debug, shared=shared, native=native)

    elif cmd == "run":
        run_project(no_debug=no_debug, shared=shared, native=native)

    elif cmd == "update":
        xeon_update()

    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
