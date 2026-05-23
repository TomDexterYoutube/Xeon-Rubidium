import sys
import os
import subprocess
from pathlib import Path
import glob

# Resolve the ~/.xeon directory
XEON_DIR = Path.home() / ".xeon"
COMPILER_SCRIPT = XEON_DIR / "compiler.py"

def init_project():
    if os.path.exists("src"):
        print("✖ Project already initialized (src/ exists).")
        return
    
    os.makedirs("src")
    with open("src/main.rub", "w") as f:
        f.write('use thread\n\nfn main() {\n    print("Hello, Rubidium!")\n}\n')
        
    print("✔ Initialized new Rubidium project in ./src")

def build_project():
    if not os.path.exists("src"):
        print("✖ No src/ directory found. Run 'xeon init' first.")
        sys.exit(1)
        
    if not COMPILER_SCRIPT.exists():
        print(f"✖ Compiler not found at {COMPILER_SCRIPT}.")
        print("Please ensure Rubidium is installed in ~/.xeon")
        sys.exit(1)
        
    os.makedirs("build", exist_ok=True)
    
    # Grab all .rub files in the src directory for multi-file compilation
    src_files = glob.glob("src/*.rub")
    if not src_files:
        print("✖ No .rub files found in src/")
        sys.exit(1)
        
    # The executable name defaults to the name of the project folder
    project_name = Path(os.getcwd()).name
    out_name = f"build/{project_name}"
    if os.name == "nt":
        out_name += ".exe"
        
    print(f"Compiling {project_name}...")
    
    cmd = [sys.executable, str(COMPILER_SCRIPT)] + src_files + [out_name]
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
