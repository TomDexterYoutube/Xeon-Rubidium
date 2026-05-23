#!/bin/bash
set -e

# 1. Dependency Check
echo "Checking system dependencies..."
if ! command -v clang &> /dev/null || ! command -v python3 &> /dev/null; then
    echo "Required dependencies (Clang or Python3) are missing."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update && sudo apt install -y python3 clang build-essential
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        xcode-select --install
        echo "Please complete the macOS prompt, then re-run this script."
        exit 1
    fi
fi

# 2. Installation
echo "Installing Xeon and Rubidium..."
XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$XEON_DIR" "$BIN_DIR"
cp -r Rubidium*/* "$XEON_DIR/"
cp xeon.py "$XEON_DIR/"

# 3. Create Wrapper
cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
python3 "$HOME/.xeon/xeon.py" "$@"
EOF
chmod +x "$BIN_DIR/xeon"

# 4. Smart Path Configuration
PROFILE_FILE=""
if [ -f "$HOME/.bashrc" ]; then PROFILE_FILE="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then PROFILE_FILE="$HOME/.zshrc"
elif [ -f "$HOME/.profile" ]; then PROFILE_FILE="$HOME/.profile"; fi

if [ -n "$PROFILE_FILE" ]; then
    if ! grep -q "$BIN_DIR" "$PROFILE_FILE"; then
        echo -e "\n# Xeon PATH configuration\nexport PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$PROFILE_FILE"
        echo "✔ Added $BIN_DIR to $PROFILE_FILE"
    fi
    
    # 5. Automatically source the profile
    echo "✔ Applying configuration to current session..."
    source "$PROFILE_FILE"
else
    echo "⚠ Could not detect a shell profile. Please add $BIN_DIR to your PATH manually."
fi

echo "--------------------------------------------------------"
echo "Installation complete!, run 'source ~/.bashrc' to enable xeon!"

