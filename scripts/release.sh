#!/bin/bash
# Build and prepare Gradik for GitHub Release

set -e
cd "$(dirname "$0")/.."

VERSION=${1:-"1.0.0"}

echo "📦 Building Gradik v$VERSION for release..."
echo ""

# Build binary
./scripts/build.sh

# Test binary
echo ""
echo "🧪 Testing binary..."
./dist/gradik --help > /dev/null && echo "✅ Binary works!"

# Get file size
SIZE=$(du -h dist/gradik | cut -f1)

echo ""
echo "✅ Release ready!"
echo ""
echo "Binary: dist/gradik ($SIZE)"
echo ""
echo "📤 Next steps:"
echo "1. Go to: https://github.com/onelenyk/gradik/releases/new"
echo "2. Tag version: v$VERSION"
echo "3. Release title: Gradik v$VERSION"
echo "4. Upload file: dist/gradik"
echo "5. Publish release"
echo ""
echo "Then the one-liner will work:"
echo "  curl -fsSL https://raw.githubusercontent.com/onelenyk/gradik/master/install.sh | bash"
