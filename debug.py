import sys
import re

def check_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    errors = []
    
    for i, line in enumerate(lines, 1):
        # 1. Check for missing 'mut' keyword on reassignment
        if re.search(r'^\s*([a-zA-Z_]\w*)\s*=\s*.*', line):
            var_name = re.search(r'^\s*([a-zA-Z_]\w*)', line).group(1)
            # Simple heuristic: look if it was declared without mut
            errors.append(f"Line {i}: Error[E001]: Variable '{var_name}' is not mutable.\n"
                          f"  -> Suggestion: Change to 'let mut {var_name} = ...'")
        
        # 2. Check for potential division by zero
        if "/ 0" in line:
            errors.append(f"Line {i}: Warning[W001]: Division by zero detected.\n"
                          f"  -> Suggestion: Wrap in a 'try/on_error' block.")

    if errors:
        for err in errors:
            print(err)
        return False
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if not check_file(sys.argv[1]):
            sys.exit(1)
    sys.exit(0)
