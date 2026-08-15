#!/bin/bash
set -e

# Prevent running as root
if [ "$EUID" -eq 0 ]; then
    echo "[!] Please run this script as a normal user, not with sudo."
    exit 1
fi

cd "$(dirname "$0")"

XEON_DIR="$HOME/.xeon"
VIRE_DIR="$XEON_DIR/vire"
BIN_DIR="$HOME/.local/bin"

XEON_URL="https://raw.githubusercontent.com/TomDexterYoutube/Xeon-Rubidium/main/xeon.py"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"
VIRE_REPO_URL="https://github.com/TomDexterYoutube/Rubidium-Vire/archive/refs/heads/main.zip"


mkdir -p "$XEON_DIR" "$VIRE_DIR" "$BIN_DIR"


echo "[1/6] Checking system..."

for cmd in python3 curl unzip; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[!] Required command '$cmd' is not installed."
        exit 1
    fi
done


echo "[2/6] Installing xeon.py..."

cp xeon.py "$XEON_DIR/xeon.py"


TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"


echo "[3/6] Downloading Rubidium source..."

if ! curl -L -f -s "$REPO_URL" -o rubidium.zip; then
    echo "[!] Download failed."
    rm -rf "$TMP_DIR"
    exit 1
fi


echo "[4/6] Extracting Rubidium..."

unzip -q -o rubidium.zip

rm -rf Rubidium

for dir in *Rubidium*; do
    if [ -d "$dir" ] && [[ "$dir" != *Vire* ]]; then
        mv "$dir" Rubidium
    fi
done

cp -rf Rubidium/. "$XEON_DIR/"


# Vire — the FFI compatibility layer's own toolchain (compiler.py/debug.py/
# lexer.py/parser.py/rub_ast.py/codegen.py). It lives in its own vire/
# subfolder rather than flattened into $XEON_DIR alongside Rubidium's
# identically-named files, which it would otherwise collide with.
echo "[5/6] Downloading and extracting Vire..."

if curl -L -f -s "$VIRE_REPO_URL" -o vire.zip; then
    unzip -q -o vire.zip

    rm -rf Vire

    for dir in *Vire*; do
        if [ -d "$dir" ]; then
            mv "$dir" Vire
        fi
    done

    cp -rf Vire/. "$VIRE_DIR/"
else
    echo "[!] Failed to download Vire — continuing without it (FFI wrapper builds won't work until 'xeon update' succeeds)."
fi


cd "$HOME"
rm -rf "$TMP_DIR"


echo "[6/6] Creating xeon command..."


cat << 'EOF' > "$BIN_DIR/xeon"
#!/bin/bash
set -e

XEON_DIR="$HOME/.xeon"
VIRE_DIR="$XEON_DIR/vire"

XEON_URL="https://raw.githubusercontent.com/TomDexterYoutube/Xeon-Rubidium/main/xeon.py"
REPO_URL="https://github.com/TomDexterYoutube/Rubidium/archive/refs/heads/main.zip"
VIRE_REPO_URL="https://github.com/TomDexterYoutube/Rubidium-Vire/archive/refs/heads/main.zip"


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
            if [ -d "$dir" ] && [[ "$dir" != *Vire* ]]; then
                mv "$dir" Rubidium
            fi
        done


        cp -rf Rubidium/. "$XEON_DIR/"


        echo "Rubidium update complete!"

    else

        echo "[!] Failed to download Rubidium."

    fi


    echo "Updating Vire..."

    mkdir -p "$VIRE_DIR"

    if curl -L -f -s "$VIRE_REPO_URL" -o vire.zip; then

        unzip -q -o vire.zip


        rm -rf Vire

        for dir in *Vire*; do
            if [ -d "$dir" ]; then
                mv "$dir" Vire
            fi
        done


        cp -rf Vire/. "$VIRE_DIR/"


        echo "Vire update complete!"

    else

        echo "[!] Failed to download Vire."

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
