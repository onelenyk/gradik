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
python3 -m pip install --user "$INSTALL_DIR" -q 2>&1 | grep -v "WARNING:" || true

echo ""
echo "✅ Installation complete!"
echo ""

# Check if gradik is in PATH
if ! command -v gradik &> /dev/null; then
    # Find where gradik was installed
    GRADIK_PATH=$(python3 -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='posix_user'))" 2>/dev/null)
    
    if [ -n "$GRADIK_PATH" ] && [ -f "$GRADIK_PATH/gradik" ]; then
        echo "⚠️  Adding $GRADIK_PATH to PATH..."
        echo ""
        
        # Detect shell and add to PATH
        if [ -n "$ZSH_VERSION" ]; then
            SHELL_RC="$HOME/.zshrc"
        elif [ -n "$BASH_VERSION" ]; then
            SHELL_RC="$HOME/.bashrc"
        else
            SHELL_RC="$HOME/.profile"
        fi
        
        # Add to shell config if not already there
        if ! grep -q "Python.*bin" "$SHELL_RC" 2>/dev/null; then
            echo "" >> "$SHELL_RC"
            echo "# Added by Gradik installer" >> "$SHELL_RC"
            echo "export PATH=\"$GRADIK_PATH:\$PATH\"" >> "$SHELL_RC"
            echo "✅ Added to $SHELL_RC"
            echo ""
            echo "Run this now: export PATH=\"$GRADIK_PATH:\$PATH\""
            echo "Or restart your terminal"
        fi
    fi
fi

echo ""
echo "🎯 Usage:"
echo "  gradik start    # Start dashboard"
echo "  gradik stop     # Stop dashboard"
echo "  gradik status   # Check status"
echo ""
echo "Dashboard will open at: http://localhost:5050"
