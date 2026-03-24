#!/bin/bash
# Context-Packer Self-Test Suite
# This script runs test queries against the context-packer repository itself
# and saves the output to examples/context-packer-self/output/

set -e

REPO_ROOT=$(pwd)
SOURCE_DIR="$REPO_ROOT/src/context_packer"
OUTPUT_BASE="$REPO_ROOT/examples/context-packer-self/output"
CONFIG="/tmp/zmr_ctx_self_test_config.yaml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create config
cat > "$CONFIG" << 'EOF'
token_budget: 30000
include_patterns:
  - "**/*.py"
exclude_patterns:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "**/test_*.py"
  - "**/__init__.py"
EOF

mkdir -p "$OUTPUT_BASE"

# Ensure index is fresh
echo -e "${BLUE}Building fresh index for context-packer...${NC}"
python3 -m context_packer.cli index "$SOURCE_DIR" --config "$CONFIG"
echo -e "${GREEN}✓ Index built${NC}"

# List of 10 test cases (ID, Query)
declare -A test_cases=(
    ["1_chunking_flow"]="Show me the chunking logic flow from entry point to output in the chunker module"
    ["2_python_resolver"]="Show me how PythonResolver extracts function and class definitions"
    ["3_js_resolver"]="Show me how JavaScriptResolver handles JSX elements and exports"
    ["4_ts_resolver"]="Show me how TypeScriptResolver handles interfaces and type aliases"
    ["5_rust_resolver"]="Show me how RustResolver handles impl blocks and macro definitions"
    ["6_symbol_extraction"]="Show me how symbols_defined and symbols_referenced are collected"
    ["7_file_filtering"]="Show me how _should_include_file works with include/exclude patterns"
    ["8_fallback_regex"]="Show me when RegexChunker is used as fallback and how it parses"
    ["9_markdown_chunker"]="Show me how MarkdownChunker splits content by headings"
    ["10_tree_sitter_parse"]="Show me how TreeSitterChunker parses files and extracts definitions"
)

# Run each test
for id in "1_chunking_flow" "2_python_resolver" "3_js_resolver" "4_ts_resolver" "5_rust_resolver" "6_symbol_extraction" "7_file_filtering" "8_fallback_regex" "9_markdown_chunker" "10_tree_sitter_parse"; do
    query="${test_cases[$id]}"
    echo -e "\n${BLUE}Running Test Case: $id${NC}"
    echo -e "${YELLOW}Query: '$query'${NC}"

    test_output_dir="$OUTPUT_BASE/$id"
    mkdir -p "$test_output_dir"

    # Run query
    python3 -m context_packer.cli query "$query" --repo "$SOURCE_DIR" --config "$CONFIG"

    # Move and extract output
    if [ -f output/context-pack.zip ]; then
        mv output/context-pack.zip "$test_output_dir/context-pack.zip"
        unzip -q "$test_output_dir/context-pack.zip" -d "$test_output_dir/extracted"
        echo -e "${GREEN}✓ Output saved and extracted to $test_output_dir${NC}"

        # Log summary of files included
        if [ -f "$test_output_dir/extracted/REVIEW_CONTEXT.md" ]; then
            echo -e "${GREEN}=== TOP FILES INCLUDED ===${NC}"
            grep -E "^\| \`" "$test_output_dir/extracted/REVIEW_CONTEXT.md" | head -n 5
        fi
    else
        echo -e "${YELLOW}⚠ No output generated for $id${NC}"
    fi
done

echo -e "\n${GREEN}================================================================================${NC}"
echo -e "${GREEN}✓ All 10 test cases completed!${NC}"
echo -e "${GREEN}Results are located in: $OUTPUT_BASE${NC}"
echo -e "${GREEN}================================================================================${NC}"
