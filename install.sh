#!/bin/bash
# Gradik installer - downloads pre-built binary

set -e

INSTALL_DIR="/usr/local/bin"
BINARY_URL="https://github.com/onelenyk/gradik/releases/latest/download/gradik"
TEMP_FILE="/tmp/gradik-install-$$"

echo "🚀 Installing Gradik..."
echo ""

# Check permissions for /usr/local/bin
if [ ! -w "$INSTALL_DIR" ]; then
    echo "⚠️  Need sudo access to install to $INSTALL_DIR"
    USE_SUDO="sudo"
else
    USE_SUDO=""
fi

# Download binary
echo "📥 Downloading Gradik binary..."
if command -v curl &> /dev/null; then
    curl -fsSL "$BINARY_URL" -o "$TEMP_FILE"
elif command -v wget &> /dev/null; then
    wget -q "$BINARY_URL" -O "$TEMP_FILE"
else
    echo "❌ Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Make executable
chmod +x "$TEMP_FILE"

# Install to /usr/local/bin
echo "📦 Installing to $INSTALL_DIR..."
$USE_SUDO mv "$TEMP_FILE" "$INSTALL_DIR/gradik"

# Verify installation
if command -v gradik &> /dev/null; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "🎯 Usage:"
    echo "   gradik start    # Start dashboard"
    echo "   gradik stop     # Stop dashboard"
    echo "   gradik status   # Check status"
    echo ""
    echo "Dashboard will open at: http://localhost:5050"
else
    echo "❌ Installation failed. Binary installed but not in PATH."
    echo "   Try: /usr/local/bin/gradik"
    exit 1
fi
