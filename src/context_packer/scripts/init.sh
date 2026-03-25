#!/usr/bin/env bash
# ctx-packer-init — AI Agent Configuration Installer
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/core.sh"
source "$SCRIPT_DIR/lib/install.sh"
source "$SCRIPT_DIR/lib/index.sh"
source "$SCRIPT_DIR/agents/_registry.sh"

TARGET_PATH="$(pwd)"
SELECTED_AGENTS=()
SKIP_INDEX=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --path)
      TARGET_PATH="$2"
      shift 2
      ;;
    --agents)
      IFS=',' read -ra SELECTED_AGENTS <<< "$2"
      shift 2
      ;;
    --skip-index)
      SKIP_INDEX=true
      shift
      ;;
    --force)
      CTX_FORCE=true
      shift
      ;;
    --list-agents)
      list_agents
      exit 0
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

if [[ ${#SELECTED_AGENTS[@]} -eq 0 ]]; then
  mapfile -t SELECTED_AGENTS < <(get_default_agents)
elif [[ "${SELECTED_AGENTS[0]}" == "all" ]]; then
  mapfile -t SELECTED_AGENTS < <(get_agent_ids)
fi

for agent_id in "${SELECTED_AGENTS[@]}"; do
  if ! is_valid_agent "$agent_id"; then
    log_error "Unknown agent: '$agent_id'. Run --list-agents for available agents."
    exit 1
  fi
done

export CTX_TARGET="$TARGET_PATH"
export CTX_FORCE="${CTX_FORCE:-false}"

log_header "ctx-packer init"
log_ok "Target: $TARGET_PATH"
log_ok "Agents: ${SELECTED_AGENTS[*]}"

check_git
install_ctx_packer

for agent_id in "${SELECTED_AGENTS[@]}"; do
  source "$SCRIPT_DIR/agents/${agent_id}.sh"
done

for agent_id in "${SELECTED_AGENTS[@]}"; do
  log_section "$(get_agent_display "$agent_id")"
  "install_${agent_id}"
done

if [[ "$SKIP_INDEX" == false ]]; then
  run_index "$TARGET_PATH"
fi

log_success "Done! Configured: ${SELECTED_AGENTS[*]}"
