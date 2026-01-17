#!/bin/bash
# Quick start for development

cd "$(dirname "$0")/.."

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

# Start server in foreground
# Usage: ./run.sh [options]
# Examples:
#   ./run.sh               - Start in foreground on default port
#   ./run.sh -p 8080       - Start on port 8080
#   ./run.sh start         - Start in background

# If no arguments, default to foreground start
if [ $# -eq 0 ]; then
    python3 app.py start -f
else
    python3 app.py "$@"
fi
