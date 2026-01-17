#!/bin/bash
# Create a release tag - GitHub Actions will handle the rest

set -e

VERSION=${1:-}

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 1.0.0"
    exit 1
fi

TAG="v$VERSION"

echo "🚀 Creating release v$VERSION"
echo ""

# Check for uncommitted changes
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

# Create and push tag
echo "🏷️  Creating tag: $TAG"
if git tag -a "$TAG" -m "Release v$VERSION"; then
    echo "✅ Tag created locally"
else
    echo "❌ Tag already exists locally"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$TAG"
        git push origin :refs/tags/"$TAG" 2>/dev/null || true
        git tag -a "$TAG" -m "Release v$VERSION"
    else
        exit 1
    fi
fi

echo ""
echo "📤 Pushing tag to GitHub..."
git push origin "$TAG"

echo ""
echo "✅ Tag pushed!"
echo ""
echo "🤖 GitHub Actions will now:"
echo "   1. Build the binary on macOS"
echo "   2. Test it"
echo "   3. Create GitHub Release"
echo "   4. Upload the binary"
echo ""
echo "🌐 Watch progress: https://github.com/onelenyk/gradik/actions"
echo "📦 Release: https://github.com/onelenyk/gradik/releases/tag/$TAG"
echo ""
echo "⏱️  Takes ~5 minutes. Check the Actions tab!"
