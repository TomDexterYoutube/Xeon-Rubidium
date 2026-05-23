#!/bin/bash
set -e
cd "$(dirname "$0")"

XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

echo "[1/6] Checking system..."
# Version Check
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if (( $(echo "$PY_VER < 3.13" | bc -l) )); then
    echo "[!] Python 3.13+ required. Please update your Python."
    exit 1
fi

# 2. Cleanup
echo "[2/6] Cleaning up stale files..."
rm -rf "$XEON_DIR/Rubidium"
rm -f "$XEON_DIR/xeon.py" "$XEON_DIR/debug.py"

# 3. Download & Verify
echo "[3/6] Fetching source..."
if ! curl -L -f "$REPO_URL" -o rubidium.zip; then
    echo "[!] Download failed. Check connection."
    exit 1
fi

# Size check ( > 5KB)
if [ $(wc -c <"rubidium.zip") -lt 5000 ]; then
    echo "[!] Download corrupt."
    rm rubidium.zip
    exit 1
fi

echo "[4/6] Extracting..."
unzip -q rubidium.zip
rm rubidium.zip
for dir in *Rubidium*; do [ -d "$dir" ] && [ "$dir" != "Rubidium" ] && mv "$dir" Rubidium; done

# 4. Installation
echo "[5/6] Copying files..."
mkdir -p "$XEON_DIR" "$BIN_DIR"
cp -r Rubidium "$XEON_DIR/"
[ -f "xeon.py" ] && cp xeon.py "$XEON_DIR/"
[ -f "debug.py" ] && cp debug.py "$XEON_DIR/"

# 5. Wrapper
cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
python3 "$HOME/.xeon/xeon.py" "$@"
EOF
chmod +x "$BIN_DIR/xeon"

# 6. Path Configuration
PROFILE_FILE=""
[ -f "$HOME/.bashrc" ] && PROFILE_FILE="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && PROFILE_FILE="$HOME/.zshrc"

if [ -n "$PROFILE_FILE" ] && ! grep -q "$BIN_DIR" "$PROFILE_FILE"; then
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$PROFILE_FILE"
    echo "✔ Added to PATH. Please restart terminal."
fi

echo "Installation complete!"
