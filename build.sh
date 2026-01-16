#!/bin/bash
# Build standalone Gradik binary

set -e
cd "$(dirname "$0")"

echo "🔨 Building Gradik..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

# Install build dependencies
echo "📦 Installing build dependencies..."
pip3 install pyinstaller flask psutil -q

# Build standalone binary
echo "⚙️  Creating standalone binary..."
pyinstaller --onefile \
    --name gradik \
    --add-data "gradik:gradik" \
    --hidden-import flask \
    --hidden-import psutil \
    --clean \
    --noconfirm \
    app.py

# Clean up
rm -rf build gradik.spec

echo ""
echo "✅ Build complete!"
echo "   Binary: dist/gradik"
echo ""
echo "   Run with: ./dist/gradik"
echo "   Or copy to PATH: sudo cp dist/gradik /usr/local/bin/"
