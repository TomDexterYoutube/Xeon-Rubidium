#!/bin/bash
set -e

echo "Checking system dependencies..."

# Detect OS and install Clang/Python if missing
if ! command -v clang &> /dev/null || ! command -v python3 &> /dev/null; then
    echo "Required dependencies (Clang or Python3) are missing."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Attempting to install via apt..."
        sudo apt update
        sudo apt install -y python3 clang build-essential
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Attempting to install via Xcode Command Line Tools..."
        xcode-select --install
        echo "Please complete the macOS prompt, then re-run this script."
        exit 1
    else
        echo "Manual installation required for your OS."
        exit 1
    fi
else
    echo "Dependencies are already installed."
fi

echo "Installing Xeon and Rubidium..."

XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"

# Create the target directories
mkdir -p "$XEON_DIR"
mkdir -p "$BIN_DIR"

# Copy the compiler files and the build tool to the home directory
cp -r Rubidium*/* "$XEON_DIR/"
cp xeon.py "$XEON_DIR/"

# Create the executable wrapper
cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
python3 "$HOME/.xeon/xeon.py" "$@"
EOF

# Make the wrapper executable
chmod +x "$BIN_DIR/xeon"

echo "Installation complete."
echo "Make sure $BIN_DIR is in your PATH."
echo "You can now run 'xeon init' in any directory."
echo "To update the compiler later, place the new .py files into $XEON_DIR"
