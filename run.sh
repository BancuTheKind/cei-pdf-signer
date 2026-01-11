#!/bin/bash
# CEI Web PDF Signer - Launcher Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    echo "Install it with: brew install python3"
    exit 1
fi

# Check/create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.deps_installed" ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/.deps_installed
fi

# Run the web server
echo ""
echo "=============================================="
echo "  CEI Web PDF Signer"
echo "=============================================="
echo ""
echo "  Open your browser and go to:"
echo "  http://localhost:5000"
echo ""
echo "  Press Ctrl+C to stop the server"
echo "=============================================="
echo ""

python3 app.py
