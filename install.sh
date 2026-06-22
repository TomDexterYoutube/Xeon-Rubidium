#!/bin/bash
set -e

# Prevent running as root
if [ "$EUID" -eq 0 ]; then
    echo "[!] Please run this script as a normal user, not with sudo."
    exit 1
fi

cd "$(dirname "$0")"

XEON_DIR="$HOME/.xeon"
BIN_DIR="$HOME/.local/bin"

XEON_URL="https://raw.githubusercontent.com/TomDexterYoutube/Xeon-Rubidium/main/xeon.py"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"


mkdir -p "$XEON_DIR" "$BIN_DIR"


echo "[1/5] Checking system..."

for cmd in python3 curl unzip; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[!] Required command '$cmd' is not installed."
        exit 1
    fi
done


echo "[2/5] Installing xeon.py..."

cp xeon.py "$XEON_DIR/xeon.py"


TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"


echo "[3/5] Downloading Rubidium source..."

if ! curl -L -f -s "$REPO_URL" -o rubidium.zip; then
    echo "[!] Download failed."
    rm -rf "$TMP_DIR"
    exit 1
fi


echo "[4/5] Extracting files..."

unzip -q -o rubidium.zip


rm -rf Rubidium

for dir in *Rubidium*; do
    if [ -d "$dir" ]; then
        mv "$dir" Rubidium
    fi
done


echo "[5/5] Copying files..."

cp -rf Rubidium/. "$XEON_DIR/"


cd "$HOME"
rm -rf "$TMP_DIR"


echo "Creating xeon command..."


cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
set -e

XEON_DIR="$HOME/.xeon"

XEON_URL="https://raw.githubusercontent.com/TomDexterYoutube/Xeon-Rubidium/main/xeon.py"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"


if [ "$1" == "update" ]; then

    echo "Updating Rubidium..."

    UPDATE_TMP=$(mktemp -d)
    cd "$UPDATE_TMP"


    echo "Updating xeon.py..."

    if curl -L -f -s "$XEON_URL" -o xeon.py; then
        mv xeon.py "$XEON_DIR/xeon.py"
    else
        echo "[!] Failed to update xeon.py"
        rm -rf "$UPDATE_TMP"
        exit 1
    fi


    echo "Updating language files..."

    if curl -L -f -s "$REPO_URL" -o rubidium.zip; then

        unzip -q -o rubidium.zip


        rm -rf Rubidium

        for dir in *Rubidium*; do
            if [ -d "$dir" ]; then
                mv "$dir" Rubidium
            fi
        done


        cp -rf Rubidium/. "$XEON_DIR/"


        echo "Update complete!"

    else

        echo "[!] Failed to download Rubidium."

    fi


    cd "$HOME"
    rm -rf "$UPDATE_TMP"

    exit 0
fi



python3 "$XEON_DIR/xeon.py" "$@"

EOF


chmod +x "$BIN_DIR/xeon"



echo "Adding PATH..."


for profile in \
"$HOME/.bashrc" \
"$HOME/.zshrc" \
"$HOME/.bash_profile"

do

    if [ -f "$profile" ] && ! grep -q "$BIN_DIR" "$profile"; then

        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$profile"

        echo "✔ Added $BIN_DIR to $profile"

    fi

done



echo ""
echo "========================================================"
echo "Installation complete!"
echo ""
echo "Restart terminal or run:"
echo "source ~/.bashrc"
echo ""
echo "Run:"
echo "xeon"
echo ""
echo "Update later with:"
echo "xeon update"
echo "========================================================"
