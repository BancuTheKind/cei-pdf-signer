#!/bin/bash
# Create macOS .icns icon from SVG

set -e
cd "$(dirname "$0")"

# Check if we have the tools we need
if ! command -v sips &> /dev/null; then
    echo "sips not found (should be available on macOS)"
    exit 1
fi

# Create iconset directory
ICONSET="icon.iconset"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"

# First convert SVG to a large PNG using Python
python3 << 'PYTHON'
import subprocess
import os

# Try using cairosvg if available, otherwise use a simple HTML approach
try:
    import cairosvg
    cairosvg.svg2png(url='icon.svg', write_to='icon_1024.png', output_width=1024, output_height=1024)
except ImportError:
    # Fall back to using sips with a pre-rendered PNG or qlmanage
    import sys
    print("cairosvg not available, trying qlmanage...", file=sys.stderr)
    os.system('qlmanage -t -s 1024 -o . icon.svg 2>/dev/null || true')
    if os.path.exists('icon.svg.png'):
        os.rename('icon.svg.png', 'icon_1024.png')
    else:
        # Create a simple placeholder PNG
        print("Could not convert SVG. Please install cairosvg: pip install cairosvg", file=sys.stderr)
        sys.exit(1)
PYTHON

if [ ! -f "icon_1024.png" ]; then
    echo "Failed to create PNG from SVG"
    echo "Install cairosvg: pip install cairosvg"
    exit 1
fi

# Generate all required sizes
sips -z 16 16     icon_1024.png --out "$ICONSET/icon_16x16.png"
sips -z 32 32     icon_1024.png --out "$ICONSET/icon_16x16@2x.png"
sips -z 32 32     icon_1024.png --out "$ICONSET/icon_32x32.png"
sips -z 64 64     icon_1024.png --out "$ICONSET/icon_32x32@2x.png"
sips -z 128 128   icon_1024.png --out "$ICONSET/icon_128x128.png"
sips -z 256 256   icon_1024.png --out "$ICONSET/icon_128x128@2x.png"
sips -z 256 256   icon_1024.png --out "$ICONSET/icon_256x256.png"
sips -z 512 512   icon_1024.png --out "$ICONSET/icon_256x256@2x.png"
sips -z 512 512   icon_1024.png --out "$ICONSET/icon_512x512.png"
sips -z 1024 1024 icon_1024.png --out "$ICONSET/icon_512x512@2x.png"

# Create the icns file
iconutil -c icns "$ICONSET" -o icon.icns

# Cleanup
rm -rf "$ICONSET"
rm -f icon_1024.png

echo "Created icon.icns successfully!"
