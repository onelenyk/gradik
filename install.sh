#!/bin/bash

set -e

INSTALL_DIR="$HOME/gradik"
REPO_URL="https://github.com/onelenyk/gradik.git"

echo "🚀 Installing Gradik..."
echo "📂 Install location: $INSTALL_DIR"
echo ""

# Check if directory exists
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory $INSTALL_DIR already exists."
    read -p "Remove and reinstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "❌ Installation cancelled"
        exit 1
    fi
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Clone repo
echo "📥 Cloning repository..."
git clone "$REPO_URL" "$INSTALL_DIR"

# Install dependencies
cd "$INSTALL_DIR"
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt -q

echo ""
echo "✅ Installation complete!"
echo ""
echo "To start Gradik:"
echo "  cd $INSTALL_DIR"
echo "  ./run.sh"
echo ""
echo "Or install globally with pip:"
echo "  pip install -e $INSTALL_DIR"
echo "  gradik start"
