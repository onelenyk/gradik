#!/bin/bash

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

# Install deps if needed
if ! python3 -c "import flask, psutil" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt -q
fi

# Start with optional port argument
# Usage: ./run.sh [port]
# Port is saved to ~/.gradik/config.json and persisted
python3 app.py "$@"
