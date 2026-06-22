import sys
import os
import subprocess
import shutil
from pathlib import Path

# Resolve the ~/.xeon directory
XEON_DIR        = Path.home() / ".xeon"
COMPILER_SCRIPT = XEON_DIR / "compiler.py"
DEBUGGER_SCRIPT = XEON_DIR / "debug.py"
ANALYZER_SCRIPT = XEON_DIR / "analyzer.py"


# ─── Helpers ──────────────────────────────────────────────────────────────────

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
        print(f"✖ Compiler not found at {COMPILER_SCRIPT}.")
        print("  Please ensure Rubidium is installed in ~/.xeon")
        sys.exit(1)


# ─── Commands ─────────────────────────────────────────────────────────────────

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


def check_project(strict: bool = False):
    """Run the static analyzer against src/main.rub."""
    main_file = _require_src()

    if not ANALYZER_SCRIPT.exists():
        print(f"✖ Analyzer not found at {ANALYZER_SCRIPT}.")
        print("  Please ensure analyzer.py is installed in ~/.xeon")
        sys.exit(1)

    cmd = [sys.executable, str(ANALYZER_SCRIPT), "check", main_file]
    if strict:
        cmd.append("--strict")

    res = subprocess.run(cmd)
    sys.exit(res.returncode)


def build_project(strict_check: bool = False):
    main_file = _require_src()
    _require_compiler()

    # ── Step 1: Static analysis ───────────────────────────────────────────────
    if ANALYZER_SCRIPT.exists():
        print("🔎 Running static analyzer...")
        cmd = [sys.executable, str(ANALYZER_SCRIPT), "check", main_file]
        if strict_check:
            cmd.append("--strict")
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("✖ Static analysis failed. Fix errors before building.")
            sys.exit(1)
    else:
        print("⚠  Analyzer not found — skipping static analysis.")

    # ── Step 2: Debugger ──────────────────────────────────────────────────────
    if DEBUGGER_SCRIPT.exists():
        print("🔍 Running Rubidium debugger...")
        res = subprocess.run([sys.executable, str(DEBUGGER_SCRIPT), main_file])
        if res.returncode != 0:
            print("✖ Debugger found issues. Fix them before compiling.")
            sys.exit(1)

    # ── Step 3: Clean build directory ────────────────────────────────────────
    os.makedirs("build", exist_ok=True)
    for fname in os.listdir("build"):
        fpath = os.path.join("build", fname)
        if os.path.isfile(fpath) or os.path.islink(fpath):
            os.remove(fpath)
        elif os.path.isdir(fpath):
            shutil.rmtree(fpath)

    # ── Step 4: Bundle FFI libraries ─────────────────────────────────────────
    bundled = 0
    for root, _dirs, files in os.walk("src"):
        for fname in files:
            if fname.endswith((".so", ".dll", ".dylib")):
                src_path = os.path.join(root, fname)
                rel      = os.path.relpath(src_path, "src")
                dst_path = os.path.join("build", rel)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"  bundled FFI lib → build/{rel}")
                bundled += 1
    if bundled:
        print(f"  {bundled} FFI library file(s) bundled")

    # ── Step 5: Compile ───────────────────────────────────────────────────────
    project_name = Path(os.getcwd()).name
    out_name = f"build/{project_name}"
    if os.name == "nt":
        out_name += ".exe"

    print(f"Compiling {project_name}...")
    res = subprocess.run(
        [sys.executable, str(COMPILER_SCRIPT), main_file, out_name]
    )

    if res.returncode != 0:
        print("✖ Build failed.")
        sys.exit(1)

    return out_name


def run_project(strict_check: bool = False):
    out_name = build_project(strict_check=strict_check)
    print(f"Running {out_name}...\n" + "─" * 30)
    run_cmd = [f"./{out_name}"] if os.name != "nt" else [out_name]
    try:
        subprocess.run(run_cmd)
    except KeyboardInterrupt:
        pass


# ─── Entry point ──────────────────────────────────────────────────────────────

USAGE = """\
Usage: xeon <command> [options]

Commands:
  init          Create a new Rubidium project in ./src
  check         Run the static analyzer only
  build         Analyze, debug-check, then compile
  run           Build and run the project

Options:
  --strict      Treat analyzer warnings as errors (check / build / run)
"""

def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    args   = sys.argv[1:]
    cmd    = args[0]
    strict = "--strict" in args

    if cmd == "init":
        init_project()
    elif cmd == "check":
        check_project(strict=strict)
    elif cmd == "build":
        build_project(strict_check=strict)
    elif cmd == "run":
        run_project(strict_check=strict)
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
