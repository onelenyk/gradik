#!/bin/bash

set -e

INSTALL_DIR="$HOME/.gradik-repo"
REPO_URL="https://github.com/onelenyk/gradik.git"

echo "🚀 Installing Gradik..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip"
    exit 1
fi

# Remove old install if exists
if [ -d "$INSTALL_DIR" ]; then
    echo "🧹 Cleaning old installation..."
    rm -rf "$INSTALL_DIR"
fi

# Clone repo to temp location
echo "📥 Cloning repository..."
git clone -q "$REPO_URL" "$INSTALL_DIR"

# Install globally with pip
echo "📦 Installing Gradik globally..."
pip3 install -e "$INSTALL_DIR" -q

echo ""
echo "✅ Installation complete!"
echo ""
echo "🎯 Usage:"
echo "  gradik start    # Start dashboard"
echo "  gradik stop     # Stop dashboard"
echo "  gradik status   # Check status"
echo ""
echo "Dashboard will open at: http://localhost:5050"
