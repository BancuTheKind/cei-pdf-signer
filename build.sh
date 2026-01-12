#!/bin/bash
# Script pentru compilarea aplicatiei CEI PDF Signer
# Creeaza aplicatia nativa macOS folosind PyInstaller

set -e

cd "$(dirname "$0")"

echo "=== CEI PDF Signer - Build Script ==="
echo ""

# Verifica daca exista environment virtual
if [ ! -d "venv" ]; then
    echo "Creez environment virtual..."
    python3 -m venv venv
fi

# Activeaza environment-ul virtual
source venv/bin/activate

# Instaleaza dependentele daca e nevoie
if [ ! -f "venv/.deps_installed" ]; then
    echo "Instalez dependentele..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/.deps_installed
fi

# Instaleaza PyInstaller daca nu exista
if ! command -v pyinstaller &> /dev/null; then
    echo "Instalez PyInstaller..."
    pip install pyinstaller
fi

# Curata build-urile anterioare
echo "Curata build-urile anterioare..."
rm -rf build dist

# Compileaza aplicatia
echo "Compilez aplicatia..."
pyinstaller CEIPDFSigner.spec

# Create symlink in /Applications pointing to the built app
ln -sf "$(pwd)/dist/CEI PDF Signer.app" "/Applications/CEI PDF Signer.app"

echo ""
echo "=== Build Complet ==="
echo ""
echo "Aplicatia se afla in: dist/CEI PDF Signer.app"
echo ""
echo "Pentru a rula:     open 'dist/CEI PDF Signer.app'"
echo "Symlink creat in:  /Applications/CEI PDF Signer.app"
echo ""
