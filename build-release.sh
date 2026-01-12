#!/bin/bash
# Script pentru crearea release-ului GitHub
# Compileaza aplicatia si creeaza un ZIP pentru distribuire

set -e

cd "$(dirname "$0")"

# Obtine versiunea din tag-ul git (sau foloseste "dev" daca nu exista tag)
VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "dev")

echo "=== CEI PDF Signer - Release Build ==="
echo "Versiune: $VERSION"
echo ""

# Ruleaza build-ul normal
./build.sh

# Creeaza directorul pentru release
RELEASE_DIR="release"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Numele fisierului ZIP
ZIP_NAME="CEI-PDF-Signer-${VERSION}-macOS.zip"

echo ""
echo "Creez arhiva pentru release..."

# Creeaza ZIP-ul cu aplicatia
cd dist
zip -r -y "../$RELEASE_DIR/$ZIP_NAME" "CEI PDF Signer.app"
cd ..

# Calculeaza SHA256
echo ""
echo "Calculez SHA256..."
SHA256=$(shasum -a 256 "$RELEASE_DIR/$ZIP_NAME" | cut -d' ' -f1)

# Creeaza fisier cu checksums
echo "$SHA256  $ZIP_NAME" > "$RELEASE_DIR/SHA256SUMS.txt"

echo ""
echo "=== Release Build Complet ==="
echo ""
echo "Fisiere create in folderul '$RELEASE_DIR/':"
echo "  - $ZIP_NAME"
echo "  - SHA256SUMS.txt"
echo ""
echo "SHA256: $SHA256"
echo ""
echo "Pentru a publica pe GitHub:"
echo "  1. git push origin main --tags"
echo "  2. Mergi la https://github.com/USERNAME/cei-web-signer/releases"
echo "  3. Click 'Draft a new release'"
echo "  4. Selecteaza tag-ul $VERSION"
echo "  5. Incarca fisierul $ZIP_NAME"
echo ""
