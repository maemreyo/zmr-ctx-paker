#!/bin/bash
set -e

echo "============================================"
echo "  Context Packer Release & Publish Script"
echo "============================================"
echo

# Check for PyPI token
if [ -z "$PYPI_TOKEN" ]; then
    echo "Error: PYPI_TOKEN environment variable not set"
    echo "Set it with: export PYPI_TOKEN='your-token-here'"
    echo
    echo "Or add to ~/.pypirc:"
    echo "[pypi]"
    echo "username = __token__"
    echo "password = <your-token>"
    exit 1
fi

# Check git status
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is not clean. Please commit or stash changes first."
    exit 1
fi

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//g' | sed 's/"//g')
echo "Current version: $CURRENT_VERSION"
echo

# Ask for version bump type
echo "Select version bump type:"
echo "1) Patch (0.0.X) - default"
echo "2) Minor (0.X.0)"
echo "3) Major (X.0.0)"
read -p "Selection [1-3]: " BUMP_TYPE

IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

if [ "$BUMP_TYPE" = "3" ]; then
    NEW_VERSION="$((MAJOR + 1)).0.0"
elif [ "$BUMP_TYPE" = "2" ]; then
    NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
else
    NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
fi

echo "Bumping version: $CURRENT_VERSION → $NEW_VERSION"

# Portable sed for macOS/Linux
if sed --version 2>/dev/null | grep -q GNU; then
    sed -i "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
else
    sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi

# Gather git commits since last tag for changelog
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [ -n "$LAST_TAG" ]; then
    COMMITS=$(git log ${LAST_TAG}..HEAD --oneline --no-merges | sed 's/^/- /')
else
    COMMITS=$(git log --oneline --no-merges | sed 's/^/- /')
fi

# Generate changelog entry
DATE=$(date +"%Y-%m-%d")
CHANGELOG_ENTRY="## [$NEW_VERSION] - $DATE

### Changes
${COMMITS}
"

# Update CHANGELOG with new version
echo
echo "Updating CHANGELOG.md..."

if grep -q "## \[$NEW_VERSION\]" CHANGELOG.md; then
    echo "Version $NEW_VERSION already in CHANGELOG, skipping..."
else
    echo "$CHANGELOG_ENTRY" > /tmp/changelog_entry.txt
    
    # Allow user to edit changelog
    echo "Opening changelog entry in your default editor..."
    ${EDITOR:-vi} /tmp/changelog_entry.txt

    # Insert at top of CHANGELOG (after the header line)
    HEAD=$(head -1 CHANGELOG.md)
    TAIL=$(tail -n +2 CHANGELOG.md)
    echo "$HEAD" > /tmp/new_changelog.md
    echo "" >> /tmp/new_changelog.md
    cat /tmp/changelog_entry.txt >> /tmp/new_changelog.md
    echo "" >> /tmp/new_changelog.md
    echo "$TAIL" >> /tmp/new_changelog.md
    mv /tmp/new_changelog.md CHANGELOG.md

    rm /tmp/changelog_entry.txt
    echo "CHANGELOG updated!"
fi

# Build package
echo
echo "============================================"
echo "  Building package..."
echo "============================================"
rm -rf dist/ build/ *.egg-info/
python3.11 -m build

# Commit changes and create tag
echo
echo "============================================"
echo "  Committing and Tagging..."
echo "============================================"
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo
echo "Pushing commits and tags to remote..."
git push origin HEAD
git push origin "v$NEW_VERSION"

# Upload to PyPI
echo
echo "============================================"
echo "  Uploading to PyPI..."
echo "============================================"
python3.11 -m twine upload dist/* --username __token__ --password "$PYPI_TOKEN"

# GitHub Release
echo
echo "============================================"
echo "  Creating GitHub Release..."
echo "============================================"
if command -v gh &> /dev/null; then
    # Extract just the latest changelog section for the release notes
    awk -v ver="## \\[$NEW_VERSION\\]" '
        $0 ~ ver {flag=1; print; next}
        /^## \[/ && flag {exit}
        flag {print}
    ' CHANGELOG.md > /tmp/release_notes.md
    
    echo "Creating release using gh cli..."
    gh release create "v$NEW_VERSION" -F /tmp/release_notes.md -t "Release v$NEW_VERSION"
    rm /tmp/release_notes.md
    echo "✅ GitHub Release created!"
else
    echo "⚠️ 'gh' CLI not found. Please create the GitHub release manually:"
    echo "https://github.com/zamery/zmr-ctx-paker/releases/new?tag=v$NEW_VERSION"
fi

echo
echo "============================================"
echo "  ✅ Release complete! (v$NEW_VERSION)"
echo "============================================"
