#!/bin/bash
set -e
cd "$(dirname "$0")"

XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

echo "[1/5] Checking system..."
# Version Check
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if (( $(echo "$PY_VER < 3.13" | bc -l) )); then
    echo "[!] Python 3.13+ required. Please update your Python."
    exit 1
fi

# 2. Download
echo "[2/5] Fetching source..."
if ! curl -L -f -s "$REPO_URL" -o rubidium.zip; then
    echo "[!] Download failed. Check connection."
    exit 1
fi

echo "[3/5] Extracting..."
# -o ensures it overwrites existing extracted files without prompting
unzip -q -o rubidium.zip
for dir in *Rubidium*; do [ -d "$dir" ] && [ "$dir" != "Rubidium" ] && mv "$dir" Rubidium; done

# 3. Installation
echo "[4/5] Copying files (overwriting existing)..."
mkdir -p "$XEON_DIR/Rubidium" "$BIN_DIR"
cp -rf Rubidium/* "$XEON_DIR/Rubidium/"
[ -f "xeon.py" ] && cp -f xeon.py "$XEON_DIR/"
[ -f "debug.py" ] && cp -f debug.py "$XEON_DIR/"

# 4. Wrapper
cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
# UPDATE COMMAND LOGIC
if [ "$1" == "update" ]; then
    echo "Updating Xeon and Rubidium..."
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    curl -L -s "https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip" -o rubidium.zip
    unzip -q -o rubidium.zip
    for dir in *Rubidium*; do [ -d "$dir" ] && [ "$dir" != "Rubidium" ] && mv "$dir" Rubidium; done
    
    # Overwrite without deleting
    mkdir -p "$HOME/.xeon"
    cp -rf Rubidium/* "$HOME/.xeon"
    [ -f "xeon.py" ] && cp -f xeon.py "$HOME/.xeon/"
    [ -f "debug.py" ] && cp -f debug.py "$HOME/.xeon/"
    
    cd "$HOME"
    rm -rf "$TMP_DIR"
    echo "Update complete!"
    exit 0
fi

# Standard Execution
python3 "$HOME/.xeon/xeon.py" "$@"
EOF
chmod +x "$BIN_DIR/xeon"

# 5. Path Configuration
PROFILE_FILE=""
[ -f "$HOME/.bashrc" ] && PROFILE_FILE="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && PROFILE_FILE="$HOME/.zshrc"

if [ -n "$PROFILE_FILE" ] && ! grep -q "$BIN_DIR" "$PROFILE_FILE"; then
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$PROFILE_FILE"
    echo "✔ Added to PATH. Please restart terminal."
fi

echo "Installation complete!"
