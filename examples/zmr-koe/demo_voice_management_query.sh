#!/bin/bash
# Demo script: Query voice management logic from zmr-koe repository
# Run this from the repository root: bash examples/zmr-koe/demo_voice_management_query.sh

set -e

# Ensure we are in the repo root if possible, or paths will be relative to root
REPO_ROOT=$(pwd)
SOURCE_DIR="examples/zmr-koe/source"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Directory $SOURCE_DIR not found. Please run this script from the repository root."
    exit 1
fi

echo "================================================================================"
echo "DEMO: Context-Packer Query - Voice Management Logic"
echo "================================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Create config that includes all relevant languages
echo -e "${BLUE}Step 1: Creating config for all languages (TS, JS, Rust)${NC}"
cat > /tmp/voice_query_config.yaml << 'EOF'
token_budget: 50000
include_patterns:
  - "**/*.ts"
  - "**/*.js"
  - "**/*.rs"
exclude_patterns:
  - "**/node_modules/**"
  - "**/target/**"
  - "**/.git/**"
  - "**/dist/**"
  - "**/build/**"
EOF
echo -e "${GREEN}✓ Config created${NC}"
echo ""

# Step 2: Clean old index
echo -e "${BLUE}Step 2: Cleaning old index${NC}"
rm -rf "$SOURCE_DIR/.context-pack"
echo -e "${GREEN}✓ Old index removed${NC}"
echo ""

# Step 3: Build new index with all languages
echo -e "${BLUE}Step 3: Building index with all languages${NC}"
python3 -m context_packer.cli index "$SOURCE_DIR" --config /tmp/voice_query_config.yaml
echo -e "${GREEN}✓ Index built${NC}"
echo ""

# Step 4: Query voice management logic
echo -e "${BLUE}Step 4: Querying voice management logic${NC}"
echo -e "${YELLOW}Query: 'How does voice management work? Show me the logic for managing voices'${NC}"
echo ""
python3 -m context_packer.cli query \
  "How does voice management work? Show me the logic for managing voices" \
  --repo "$SOURCE_DIR" \
  --config /tmp/voice_query_config.yaml
echo ""

# Step 5: Extract and show results
echo -e "${BLUE}Step 5: Analyzing results${NC}"
echo ""

if [ -f output/context-pack.zip ]; then
  # Extract
  rm -rf /tmp/voice_query_result
  unzip -q output/context-pack.zip -d /tmp/voice_query_result

  # Show review context
  echo -e "${GREEN}=== REVIEW CONTEXT ===${NC}"
  cat /tmp/voice_query_result/REVIEW_CONTEXT.md
  echo ""

  # List files
  echo -e "${GREEN}=== FILES INCLUDED ===${NC}"
  find /tmp/voice_query_result/files -type f | while read file; do
    rel_path=$(echo "$file" | sed 's|/tmp/voice_query_result/files/||')
    size=$(wc -l < "$file")
    echo "  📄 $rel_path ($size lines)"
  done
  echo ""

  # Show file previews
  echo -e "${GREEN}=== FILE PREVIEWS ===${NC}"
  find /tmp/voice_query_result/files -type f | while read file; do
    rel_path=$(echo "$file" | sed 's|/tmp/voice_query_result/files/||')
    echo ""
    echo -e "${YELLOW}File: $rel_path${NC}"
    echo "---"
    head -30 "$file"
    lines=$(wc -l < "$file")
    if [ $lines -gt 30 ]; then
      echo "... ($(($lines - 30)) more lines)"
    fi
    echo ""
  done
else
  echo -e "${YELLOW}⚠ No output file generated${NC}"
fi

echo ""
echo "================================================================================"
echo -e "${GREEN}✓ Demo complete!${NC}"
echo "================================================================================"
echo ""
echo "Summary:"
echo "  - Index built with TypeScript, JavaScript, and Rust files"
echo "  - Query executed: voice management logic"
echo "  - Results saved to: output/context-pack.zip"
echo "  - Extracted to: /tmp/voice_query_result"
echo ""
