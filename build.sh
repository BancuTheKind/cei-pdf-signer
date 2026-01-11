#!/bin/bash
# Build script for CEI PDF Signer desktop app

set -e

cd "$(dirname "$0")"

echo "=== CEI PDF Signer Build Script ==="
echo ""

# Activate virtual environment
source venv/bin/activate

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Building application..."
python setup.py py2app

echo ""
echo "=== Build Complete ==="
echo "App location: dist/CEI PDF Signer.app"
echo ""
echo "To run: open 'dist/CEI PDF Signer.app'"
echo "To install: cp -r 'dist/CEI PDF Signer.app' /Applications/"
