import sys
import os
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

# ─────────────────────────────────────────────────────────────
# Package manager (xeon pkg) config
# ─────────────────────────────────────────────────────────────

PKG_REPO_OWNER  = "TomDexterYoutube"
PKG_REPO_NAME   = "xeon-pkgs"
PKG_REPO_BRANCH = "main"
PKG_RAW_BASE = f"https://raw.githubusercontent.com/{PKG_REPO_OWNER}/{PKG_REPO_NAME}/{PKG_REPO_BRANCH}"
PKG_API_BASE = f"https://api.github.com/repos/{PKG_REPO_OWNER}/{PKG_REPO_NAME}/contents"

PKG_LIST_PATH  = XEON_DIR / "pkg-list"
PACKAGES_DIR   = XEON_DIR / "packages"
PKG_LIST_STALE_SECONDS = 24 * 60 * 60  # re-fetch if local pkg-list is older than this


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


def run_debugger(main_file):
    if not DEBUGGER_SCRIPT.exists():
        print("⚠ Debugger not found. Skipping debug checks.")
        return

    print("🔍 Running Rubidium debugger...")

    res = subprocess.run(
        [sys.executable, str(DEBUGGER_SCRIPT), main_file]
    )

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

    res = subprocess.run(
        [sys.executable, str(DEBUGGER_SCRIPT), "check", main_file]
    )

    sys.exit(res.returncode)


def build_project(no_debug=False, shared=False):
    main_file = _require_src()
    _require_compiler()

    if not no_debug:
        run_debugger(main_file)

    build_dir = Path("build")

    if build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.mkdir(parents=True)

    bundled = 0

    for root, _, files in os.walk("src"):
        for fname in files:
            if fname.endswith((".so", ".dll", ".dylib")):
                src_path = Path(root) / fname
                rel_path = src_path.relative_to("src")

                dst_path = build_dir / rel_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(src_path, dst_path)

                print(f"  bundled FFI lib → build/{rel_path}")
                bundled += 1

    if bundled:
        print(f"  {bundled} FFI library file(s) bundled")

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

    cmd = [sys.executable, str(COMPILER_SCRIPT)]
    if shared:
        cmd.append("-s")
    cmd += [main_file, str(out_name)]

    res = subprocess.run(cmd)

    if res.returncode != 0:
        print("✖ Build failed.")
        sys.exit(1)

    print("✔ Build complete")

    return str(out_name)


def run_project(no_debug=False, shared=False):
    if shared:
        print("✖ 'run' doesn't apply to a shared library build (-s) — there's no entry point to execute.")
        print("  Use 'xeon build -s' and load the resulting library via FFI instead.")
        sys.exit(1)

    out_name = build_project(no_debug=no_debug)

    print(f"\nRunning {out_name}...")
    print("─" * 30)

    run_cmd = (
        [f"./{out_name}"]
        if os.name != "nt"
        else [out_name]
    )

    try:
        subprocess.run(run_cmd)
    except KeyboardInterrupt:
        print("\nProgram terminated.")


# ─────────────────────────────────────────────────────────────
# Package manager (xeon pkg) — HTTP helpers
# ─────────────────────────────────────────────────────────────

def _http_get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "xeon-pkg-manager"})
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
    """Recursively download every file under <pkg_name>/ in the repo via the
    GitHub Contents API (needed since raw.githubusercontent.com can't list a
    directory, and packages may contain an unknown number of extra .rub files)."""
    def _walk(repo_path, local_dir):
        api_url = f"{PKG_API_BASE}/{repo_path}?ref={PKG_REPO_BRANCH}"
        entries = _http_get_json(api_url)
        for entry in entries:
            if entry["type"] == "file":
                _http_download(entry["download_url"], local_dir / entry["name"])
            elif entry["type"] == "dir":
                _walk(f"{repo_path}/{entry['name']}", local_dir / entry["name"])

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    _walk(pkg_name, dest_dir)


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
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
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


def pkg_upgrade():
    _ensure_pkg_list_fresh()
    remote_list = _load_local_pkg_list()

    if not PACKAGES_DIR.exists() or not any(PACKAGES_DIR.iterdir()):
        print("No packages installed.")
        return

    upgraded, unchanged, missing = 0, 0, 0

    for pkg_dir in sorted(PACKAGES_DIR.iterdir()):
        if not pkg_dir.is_dir():
            continue
        pkg_name = pkg_dir.name
        ver_path = pkg_dir / "pkg.ver"
        local_ver = ver_path.read_text().strip() if ver_path.exists() else None

        if pkg_name not in remote_list:
            print(f"  {pkg_name}: ⚠ not found in pkg-list (skipped)")
            missing += 1
            continue

        remote_ver = remote_list[pkg_name]

        if local_ver is None or _version_is_newer(remote_ver, local_ver):
            print(f"  {pkg_name}: {local_ver or '?'} → {remote_ver} (upgrading)")
            try:
                _download_package_files(pkg_name, pkg_dir)
                upgraded += 1
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                print(f"    ✖ Failed to upgrade '{pkg_name}': {e}")
        else:
            print(f"  {pkg_name}: {local_ver} (up to date)")
            unchanged += 1

    print(f"\n✔ Upgrade complete — {upgraded} upgraded, {unchanged} up to date, {missing} skipped")


PKG_HELP = """\
Rubidium Package Manager (xeon pkg)

Commands:
  xeon pkg help              Show this help
  xeon pkg fetch              Download the latest package index (pkg-list)
  xeon pkg pull <name>         Install a package (auto-fetches the index
                                first if missing or older than 24h)
  xeon pkg purge <name>        Remove an installed package
  xeon pkg upgrade             Upgrade every installed package to the
                                latest version listed in pkg-list

How it works:
  Packages are installed to ~/.xeon/packages/<name>/. Once installed, use
  them from Rubidium source with:

      xeon <package_name>
      print(<package_name>.some_value)

  This works like `import`, but resolves against an installed package
  instead of a relative file path, and supports aliasing:

      xeon <package_name> as <alias>

  Package repository: https://github.com/{owner}/{repo}
""".format(owner=PKG_REPO_OWNER, repo=PKG_REPO_NAME)


def handle_pkg(args):
    if not args:
        print(PKG_HELP)
        sys.exit(1)

    subcmd = args[0]
    rest = args[1:]

    if subcmd == "help":
        print(PKG_HELP)
    elif subcmd == "fetch":
        pkg_fetch()
    elif subcmd == "pull":
        pkg_pull(rest[0] if rest else None)
    elif subcmd == "purge":
        pkg_purge(rest[0] if rest else None)
    elif subcmd == "upgrade":
        pkg_upgrade()
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
  pkg           Manage packages (run 'xeon pkg help' for details)

Options:
  --no-debug    Skip debugger checks during build/run
  -s            Compile as a shared library (.so/.dll/.dylib) with no
                entry point — exported fn's are callable via FFI from
                another language. Only valid with 'build' (not 'run').
"""


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    args = sys.argv[1:]

    if args[0] == "pkg":
        handle_pkg(args[1:])
        return

    no_debug = "--no-debug" in args
    shared   = "-s" in args

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
        build_project(no_debug=no_debug, shared=shared)

    elif cmd == "run":
        run_project(no_debug=no_debug, shared=shared)

    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
