#!/bin/bash
# Manual release instructions (no gh CLI needed)

set -e
cd "$(dirname "$0")/.."

VERSION=${1:-}

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release-manual.sh <version>"
    echo "Example: ./scripts/release-manual.sh 1.0.0"
    exit 1
fi

echo "🚀 Preparing Gradik v$VERSION for manual release..."
echo ""

# Clean previous builds
echo "🧹 Cleaning previous builds..."
make clean

# Build binary
echo ""
echo "🔨 Building binary..."
./scripts/build.sh

# Verify binary works
echo ""
echo "🧪 Testing binary..."
if ! ./dist/gradik --help > /dev/null 2>&1; then
    echo "❌ Binary test failed!"
    exit 1
fi
echo "✅ Binary works!"

# Get binary info
SIZE=$(du -h dist/gradik | cut -f1)
CHECKSUM=$(shasum -a 256 dist/gradik | cut -d' ' -f1)

echo ""
echo "📦 Release ready!"
echo ""
echo "   Binary: dist/gradik"
echo "   Size: $SIZE"
echo "   SHA256: $CHECKSUM"
echo ""

# Create tag
TAG="v$VERSION"
echo "🏷️  Creating git tag: $TAG"
git tag -a "$TAG" -m "Release $VERSION" 2>/dev/null || {
    echo "⚠️  Tag $TAG already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$TAG"
        git push origin :refs/tags/"$TAG" 2>/dev/null || true
        git tag -a "$TAG" -m "Release $VERSION"
    else
        echo "Skipping tag creation"
    fi
}

echo ""
echo "📤 Pushing tag..."
git push origin "$TAG" 2>/dev/null || echo "⚠️  Failed to push tag (maybe already exists)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 MANUAL STEPS - Follow these:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open: https://github.com/onelenyk/gradik/releases/new"
echo ""
echo "2. Fill in:"
echo "   Tag: $TAG"
echo "   Title: Gradik v$VERSION"
echo ""
echo "3. Release notes (copy this):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat << EOF

## Installation

\`\`\`bash
curl -fsSL https://raw.githubusercontent.com/onelenyk/gradik/master/install.sh | bash
\`\`\`

## Binary Info
- **Size:** $SIZE
- **SHA256:** \`$CHECKSUM\`
- **Built:** $(date +"%Y-%m-%d %H:%M %Z")
- **Platform:** macOS ARM64 (Apple Silicon)

## Features
- 📊 Monitor Gradle & Kotlin daemons
- 🎯 Track Android Studio & Emulators  
- 💻 Monitor IDEs (VS Code, Cursor, Windsurf, etc.)
- 🌓 Dark/Light mode toggle
- 🚨 Smart alerts (stuck/idle processes)
- ⚡ Kill processes directly from dashboard
- 🔧 Configurable port (persistent)

## Usage
\`\`\`bash
gradik start          # Start in background
gradik stop           # Stop service
gradik status         # Check status
gradik start -p 8080  # Custom port
\`\`\`

EOF
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "4. Upload binary: dist/gradik"
echo ""
echo "5. Click 'Publish release'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📂 Binary location: $(pwd)/dist/gradik"
echo ""

# Offer to open browser
if command -v open &> /dev/null; then
    read -p "Open GitHub releases page now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open "https://github.com/onelenyk/gradik/releases/new?tag=$TAG&title=Gradik%20v$VERSION"
    fi
fi
