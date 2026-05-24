#!/bin/bash
set -e

# Prevent running as root, which would install to /root instead of the user's home
if [ "$EUID" -eq 0 ]; then
  echo "[!] Please run this script as a normal user, not with sudo."
  exit 1
fi

cd "$(dirname "$0")"

XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"

echo "[1/5] Checking system..."
for cmd in python3 curl unzip; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[!] Required command '$cmd' is not installed."
        exit 1
    fi
done

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)'; then
    echo "[!] Python 3.13+ required. Please update your Python."
    exit 1
fi

TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "[2/5] Fetching source..."
if ! curl -L -f -s "$REPO_URL" -o rubidium.zip; then
    echo "[!] Download failed. Check connection."
    rm -rf "$TMP_DIR"
    exit 1
fi

echo "[3/5] Extracting..."
unzip -q -o rubidium.zip
rm -rf Rubidium 
for dir in *Rubidium*; do 
    [ -d "$dir" ] && [ "$dir" != "Rubidium" ] && mv "$dir" Rubidium
done

echo "[4/5] Copying files..."
mkdir -p "$XEON_DIR" "$BIN_DIR"

# FIX: Using '.' instead of '*' ensures hidden files/configs are also copied
cp -rf Rubidium/. "$XEON_DIR/"

cd "$HOME"
rm -rf "$TMP_DIR"

echo "[5/5] Creating wrapper..."
cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
set -e

if [ "$1" == "update" ]; then
    echo "Updating Xeon and Rubidium..."
    UPDATE_TMP=$(mktemp -d)
    cd "$UPDATE_TMP"
    
    if curl -L -f -s "https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip" -o rubidium.zip; then
        unzip -q -o rubidium.zip
        rm -rf Rubidium
        for dir in *Rubidium*; do 
            [ -d "$dir" ] && [ "$dir" != "Rubidium" ] && mv "$dir" Rubidium
        done
        
        mkdir -p "$HOME/.xeon"
        # FIX: Ensure hidden files update correctly
        cp -rf Rubidium/. "$HOME/.xeon/"
        
        echo "Update complete!"
    else
        echo "Update failed: Could not download repository."
    fi
    
    cd "$HOME"
    rm -rf "$UPDATE_TMP"
    exit 0
fi

# Standard Execution
python3 "$HOME/.xeon/xeon.py" "$@"
EOF

chmod +x "$BIN_DIR/xeon"

# FIX: Add to ALL detected profile files rather than just the last one found
for profile in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile"; do
    if [ -f "$profile" ] && ! grep -q "$BIN_DIR" "$profile"; then
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$profile"
        echo "✔ Added $BIN_DIR to $profile"
    fi
done

echo ""
echo "========================================================"
echo "Installation complete!"
echo "Run 'source ~/.bashrc' (or restart your terminal) to apply changes."
echo "Run 'xeon' to start or 'xeon update' to update."
echo "========================================================"
