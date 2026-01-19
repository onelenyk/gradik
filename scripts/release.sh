#!/bin/bash
# Create a release tag - GitHub Actions will handle the rest
# Supports auto-versioning: patch, minor, major, or explicit version

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$PROJECT_ROOT/VERSION"

# Get current version
get_current_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE" | tr -d ' \n'
    else
        echo "0.0.0"
    fi
}

# Bump version
bump_version() {
    local current=$1
    local type=$2
    
    IFS='.' read -ra PARTS <<< "$current"
    local major=${PARTS[0]}
    local minor=${PARTS[1]}
    local patch=${PARTS[2]}
    
    case $type in
        patch)
            patch=$((patch + 1))
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        *)
            echo "$type"  # Return as-is if it's an explicit version
            return
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Update version in files
update_version_files() {
    local new_version=$1
    
    # Update VERSION file
    echo "$new_version" > "$VERSION_FILE"
    echo "✅ Updated VERSION file: $new_version"
    
    # Update pyproject.toml
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed
            sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" "$PROJECT_ROOT/pyproject.toml"
        else
            # Linux sed
            sed -i "s/^version = \".*\"/version = \"$new_version\"/" "$PROJECT_ROOT/pyproject.toml"
        fi
        echo "✅ Updated pyproject.toml"
    fi
}

VERSION_INPUT=${1:-}

if [ -z "$VERSION_INPUT" ]; then
    CURRENT=$(get_current_version)
    echo "📦 Current version: $CURRENT"
    echo ""
    echo "Usage: ./scripts/release.sh [patch|minor|major|<version>]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/release.sh patch    # Bump patch: $CURRENT -> $(bump_version "$CURRENT" patch)"
    echo "  ./scripts/release.sh minor    # Bump minor: $CURRENT -> $(bump_version "$CURRENT" minor)"
    echo "  ./scripts/release.sh major    # Bump major: $CURRENT -> $(bump_version "$CURRENT" major)"
    echo "  ./scripts/release.sh 1.2.3    # Use explicit version"
    exit 1
fi

# Determine new version
if [[ "$VERSION_INPUT" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Explicit version provided
    VERSION="$VERSION_INPUT"
else
    # Auto-bump
    CURRENT=$(get_current_version)
    VERSION=$(bump_version "$CURRENT" "$VERSION_INPUT")
    
    if [ "$VERSION" = "$VERSION_INPUT" ]; then
        echo "❌ Invalid version type: $VERSION_INPUT"
        echo "   Use: patch, minor, major, or explicit version (e.g., 1.2.3)"
        exit 1
    fi
    
    echo "📈 Auto-bumping: $CURRENT -> $VERSION ($VERSION_INPUT)"
fi

TAG="v$VERSION"

echo ""
echo "🚀 Creating release v$VERSION"
echo ""

# Update version files
update_version_files "$VERSION"

# Check for uncommitted changes (excluding VERSION and pyproject.toml)
if [[ -n $(git status -s | grep -v "VERSION\|pyproject.toml") ]]; then
    echo "⚠️  Working directory has uncommitted changes:"
    git status -s | grep -v "VERSION\|pyproject.toml"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Commit version changes
if [[ -n $(git status -s VERSION pyproject.toml) ]]; then
    echo "📝 Committing version changes..."
    git add VERSION pyproject.toml
    git commit -m "Bump version to $VERSION" || true
fi

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
