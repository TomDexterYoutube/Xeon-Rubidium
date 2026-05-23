import sys
import os
import subprocess
from pathlib import Path

# Resolve the ~/.xeon directory
XEON_DIR = Path.home() / ".xeon"
COMPILER_SCRIPT = XEON_DIR / "compiler.py"
DEBUGGER_SCRIPT = XEON_DIR / "debug.py"

def init_project():
    if os.path.exists("src"):
        print("✖ Project already initialized (src/ exists).")
        return
    
    os.makedirs("src")
    with open("src/main.rub", "w") as f:
        f.write('fn main() {\n    print("Im, working fine!")\n    print("Ready to start coding?)\n}\n')
        
    print("✔ Initialized new Rubidium project in ./src")

def build_project():
    if not os.path.exists("src"):
        print("✖ No src/ directory found. Run 'xeon init' first.")
        sys.exit(1)
        
    # Enforce main.rub as the strict entry point (like Rust's main.rs)
    main_file = "src/main.rub"
    if not os.path.exists(main_file):
        print(f"✖ Entry point '{main_file}' not found.")
        sys.exit(1)
        
    if not COMPILER_SCRIPT.exists():
        print(f"✖ Compiler not found at {COMPILER_SCRIPT}.")
        print("Please ensure Rubidium is installed in ~/.xeon")
        sys.exit(1)

    if DEBUGGER_SCRIPT.exists():
        print("🔍 Running Rubidium debugger...")
        debug_cmd = [sys.executable, str(DEBUGGER_SCRIPT), main_file]
        res = subprocess.run(debug_cmd)
        if res.returncode != 0:
            print("✖ Debugger found issues. Fix them before compiling.")
            sys.exit(1)
    
    os.makedirs("build", exist_ok=True)
    
    # The executable name defaults to the name of the project folder
    project_name = Path(os.getcwd()).name
    out_name = f"build/{project_name}"
    if os.name == "nt":
        out_name += ".exe"
        
    print(f"Compiling {project_name}...")
    
    # Pass ONLY main.rub to the compiler.
    # The compiler will automatically trace and pull in other files via import/use.
    cmd = [sys.executable, str(COMPILER_SCRIPT), main_file, out_name]
    res = subprocess.run(cmd)
    
    if res.returncode != 0:
        print("✖ Build failed.")
        sys.exit(1)
        
    return out_name

def run_project():
    out_name = build_project()
    print(f"Running {out_name}...\n" + "─"*30)
    
    # Format execution command based on OS
    run_cmd = [f"./{out_name}"] if os.name != "nt" else [out_name]
    
    try:
        subprocess.run(run_cmd)
    except KeyboardInterrupt:
        pass

def main():
    if len(sys.argv) < 2:
        print("Usage: xeon <init|build|run>")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "init":
        init_project()
    elif cmd == "build":
        build_project()
    elif cmd == "run":
        run_project()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: xeon <init|build|run>")
        sys.exit(1)

if __name__ == "__main__":
    main()
