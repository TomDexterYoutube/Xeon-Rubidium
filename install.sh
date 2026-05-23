#!/bin/bash
set -e

echo "Installing Xeon and Rubidium..."

XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"

# Create the target directories
mkdir -p "$XEON_DIR"
mkdir -p "$BIN_DIR"

# Copy the compiler files and the build tool to the home directory
cp -r rubidium/* "$XEON_DIR/"
cp xeon.py "$XEON_DIR/"

# Create the executable wrapper
cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
python3 "$HOME/.xeon/xeon.py" "$@"
EOF

# Make the wrapper executable
chmod +x "$BIN_DIR/xeon"

echo "✔ Installation complete!"
echo "Make sure $BIN_DIR is in your PATH (it usually is by default)."
echo "You can now run 'xeon init' in any directory."
echo ""
echo "To update the compiler later, just drop the new .py files into $XEON_DIR"
