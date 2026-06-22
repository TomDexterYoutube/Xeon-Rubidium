import sys
import os
import subprocess
import shutil
from pathlib import Path


# Resolve the ~/.xeon directory
XEON_DIR = Path.home() / ".xeon"

COMPILER_SCRIPT = XEON_DIR / "compiler.py"
DEBUGGER_SCRIPT = XEON_DIR / "debug.py"


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


def build_project(no_debug=False):
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

    if os.name == "nt":
        out_name = out_name.with_suffix(".exe")

    print(f"Compiling {project_name}...")

    res = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            main_file,
            str(out_name),
        ]
    )

    if res.returncode != 0:
        print("✖ Build failed.")
        sys.exit(1)

    print("✔ Build complete")

    return str(out_name)


def run_project(no_debug=False):
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
# Entry Point
# ─────────────────────────────────────────────────────────────

USAGE = """\
Usage: xeon <command> [options]

Commands:
  init          Create a new Rubidium project in ./src
  check         Run the static analyzer only
  build         Analyze, debug-check, then compile
  run           Build and run the project

Options:
  --no-debug    Skip debugger checks during build/run
"""


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    args = sys.argv[1:]

    no_debug = "--no-debug" in args

    args = [
        arg
        for arg in args
        if arg != "--no-debug"
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
        build_project(no_debug=no_debug)

    elif cmd == "run":
        run_project(no_debug=no_debug)

    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
