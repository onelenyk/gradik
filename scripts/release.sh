#!/bin/bash
# Automated build and release to GitHub

set -e
cd "$(dirname "$0")/.."

VERSION=${1:-}

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 1.0.0"
    exit 1
fi

echo "🚀 Preparing Gradik v$VERSION for release..."
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not found"
    echo ""
    echo "Install it with:"
    echo "  brew install gh"
    echo "  # or"
    echo "  https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo ""
    echo "Run: gh auth login"
    exit 1
fi

# Ensure working directory is clean
if [[ -n $(git status -s) ]]; then
    echo "⚠️  Working directory has uncommitted changes:"
    git status -s
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

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

# Get binary size
SIZE=$(du -h dist/gradik | cut -f1)
echo "   Size: $SIZE"

# Create git tag
TAG="v$VERSION"
echo ""
echo "🏷️  Creating git tag: $TAG"
git tag -a "$TAG" -m "Release $VERSION" || {
    echo "⚠️  Tag already exists. Delete it? (y/N)"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$TAG"
        git push origin :refs/tags/"$TAG" 2>/dev/null || true
        git tag -a "$TAG" -m "Release $VERSION"
    else
        exit 1
    fi
}

# Push tag
echo "📤 Pushing tag to GitHub..."
git push origin "$TAG"

# Create release notes
RELEASE_NOTES="Release notes for v$VERSION

## Installation

\`\`\`bash
curl -fsSL https://raw.githubusercontent.com/onelenyk/gradik/master/install.sh | bash
\`\`\`

## What's New
- Binary size: $SIZE
- Built on: $(date +%Y-%m-%d)

## Features
- 📊 Monitor Gradle & Kotlin daemons
- 🎯 Track Android Studio & Emulators
- 💻 Monitor IDEs (VS Code, Cursor, etc.)
- 🌓 Dark/Light mode
- 🚨 Resource alerts
- ⚡ Process management (kill daemons)
"

# Create GitHub release and upload binary
echo ""
echo "📦 Creating GitHub release..."
gh release create "$TAG" \
    --title "Gradik v$VERSION" \
    --notes "$RELEASE_NOTES" \
    dist/gradik

echo ""
echo "✅ Release complete!"
echo ""
echo "🌐 View release: https://github.com/onelenyk/gradik/releases/tag/$TAG"
echo ""
echo "🎯 Users can now install with:"
echo "   curl -fsSL https://raw.githubusercontent.com/onelenyk/gradik/master/install.sh | bash"
