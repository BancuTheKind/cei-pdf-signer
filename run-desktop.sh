#!/bin/bash
# Run the desktop app in development mode

cd "$(dirname "$0")"
source venv/bin/activate
python main.py
