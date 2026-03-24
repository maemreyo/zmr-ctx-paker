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

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//g' | sed 's/"//g')
echo "Current version: $CURRENT_VERSION"
echo

# Parse version parts
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR=${VERSION_PARTS[0]}
MINOR=${VERSION_PARTS[1]}
PATCH=${VERSION_PARTS[2]}

# Auto increment patch version
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"

echo "Bumping version: $CURRENT_VERSION → $NEW_VERSION"
sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Update CHANGELOG with new version
echo
echo "Updating CHANGELOG.md..."
DATE=$(date +"%Y-%m-%d")
CHANGELOG_HEADER="## [$NEW_VERSION] - $DATE"

# Check if version already exists in CHANGELOG
if grep -q "## \[$NEW_VERSION\]" CHANGELOG.md; then
    echo "Version $NEW_VERSION already in CHANGELOG, skipping..."
else
    # Create new entry
    cat > /tmp/changelog_entry.txt << 'ENTRY'
## [VERSION] - DATE

### Added
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py

ENTRY

    # Replace placeholder with actual version and date
    sed -i '' "s/VERSION/$NEW_VERSION/g" /tmp/changelog_entry.txt
    sed -i '' "s/DATE/$DATE/g" /tmp/changelog_entry.txt

    # Insert at top of CHANGELOG (after the header line)
    HEAD=$(head -1 CHANGELOG.md)
    TAIL=$(tail -n +2 CHANGELOG.md)
    echo "$HEAD" > /tmp/new_changelog.md
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

# Upload to PyPI
echo
echo "============================================"
echo "  Uploading to PyPI..."
echo "============================================"
python3.11 -m twine upload dist/* --username __token__ --password "$PYPI_TOKEN"

echo
echo "============================================"
echo "  ✅ Release complete!"
echo "============================================"
echo
echo "Don't forget to:"
echo "1. Push changes: git push && git push --tags"
echo "2. Create GitHub release"
