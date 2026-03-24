#!/bin/bash
# ZMR-KOE Test Suite for Context-Packer
# This script runs 10 different test queries against the zmr-koe repository
# and saves the output to examples/zmr-koe/output/

set -e

REPO_ROOT=$(pwd)
SOURCE_DIR="examples/zmr-koe/source"
OUTPUT_BASE="examples/zmr-koe/output"
CONFIG="/tmp/zmr_koe_test_config.yaml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create config
cat > "$CONFIG" << 'EOF'
token_budget: 30000
include_patterns:
  - "**/*.ts"
  - "**/*.js"
  - "**/*.rs"
  - "**/*.svelte"
  - "**/*.md"
exclude_patterns:
  - "**/node_modules/**"
  - "**/target/**"
  - "**/.git/**"
  - "**/dist/**"
  - "**/build/**"
EOF

# Ensure index is fresh
echo -e "${BLUE}Building fresh index for zmr-koe...${NC}"
python3 -m context_packer.cli index "$SOURCE_DIR" --config "$CONFIG"
echo -e "${GREEN}✓ Index built${NC}"

# List of 10 test cases (ID, Query)
declare -A test_cases=(
    ["1_audio_system"]="How does the audio playback system work? Show me the sink and output stream management in audio.rs"
    ["2_model_onboarding"]="What is the logic for downloading and verifying TTS models (onnx and bin files) in onboarding.rs?"
    ["3_shortcuts"]="How are global shortcuts like Alt+Space and Alt+P handled and registered in the app in main.rs?"
    ["4_text_preprocessing"]="Show me the text preprocessing and regex cleaning logic for captured text before synthesis in capture.rs."
    ["5_sidecar_lifecycle"]="How does the sidecar process (koko) lifecycle management work in sidecar.rs?"
    ["6_pause_logic"]="What is the gapless playback implementation and inter-sentence pause (ms) logic in audio.rs and commands.rs?"
    ["7_config_persistence"]="How are user settings and pronunciation dictionaries persisted and synced in config.rs?"
    ["8_tauri_bridge"]="Show me the Tauri command handlers that bridge the frontend Svelte store to the backend Rust state in commands.rs."
    ["9_accessibility_capture"]="How is text captured from other applications using accessibility APIs or clipboard fallbacks in capture.rs?"
    ["10_build_process"]="What is the build process for the application and how are sidecar binaries managed in build.rs and tauri.conf.json?"
)

# Run each test
for id in "1_audio_system" "2_model_onboarding" "3_shortcuts" "4_text_preprocessing" "5_sidecar_lifecycle" "6_pause_logic" "7_config_persistence" "8_tauri_bridge" "9_accessibility_capture" "10_build_process"; do
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
