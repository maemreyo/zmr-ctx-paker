#!/usr/bin/env bash
# Shared utilities — logging, colors, skip logic, template rendering

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_header()  { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }
log_section() { echo -e "\n${CYAN}━━ $* ━━${NC}"; }
log_ok()      { echo -e "  ${GREEN}✓${NC} $*"; }
log_skip()    { echo -e "  ${YELLOW}○${NC} $*"; }
log_error()   { echo -e "  ${RED}✗${NC} $*" >&2; }
log_warn()    { echo -e "  ${YELLOW}!${NC} $*" >&2; }
log_success() { echo -e "\n${GREEN}${BOLD}✔ $*${NC}"; }

_should_write() {
  local file="$1"
  [[ ! -f "$file" ]] || [[ "${CTX_FORCE:-false}" == "true" ]]
}

_render_template() {
  local tpl="$SCRIPT_DIR/../templates/$1"
  if [[ ! -f "$tpl" ]]; then
    log_error "Template not found: $tpl"
    return 1
  fi
  CTX_PACKER_VERSION="$(ctx-packer --version 2>/dev/null | head -1 || echo 'latest')"
  CTX_DATE="$(date +%Y-%m-%d)"
  CTX_TARGET_NAME="$(basename "$CTX_TARGET")"
  envsubst < "$tpl"
}

list_agents() {
  echo -e "\n${BOLD}Available agents:${NC}"
  for entry in "${AGENT_REGISTRY[@]}"; do
    IFS=: read -r id name desc default <<< "$entry"
    local marker="○"
    [[ "$default" == "true" ]] && marker="${GREEN}●${NC}"
    printf "  %b %-12s ${CYAN}%-18s${NC} %s\n" "$marker" "$id" "$name" "$desc"
  done
  echo -e "\n  ${GREEN}●${NC} = enabled by default, ○ = opt-in"
}

show_help() {
  cat <<EOF

Usage: ctx-packer-init [options]

Options:
  --path <dir>       Target project path (default: current dir)
  --agents <list>    Comma-separated agent IDs, or 'all'
  --skip-index       Skip running ctx-packer index after setup
  --force            Overwrite existing config files
  --list-agents      Show all supported agents
  -h, --help         Show this help

Examples:
  ctx-packer-init
  ctx-packer-init --agents claude,cursor,agents_md
  ctx-packer-init --agents all --force
  ctx-packer-init --path ~/my-project --skip-index

EOF
}

check_git() {
  if [[ ! -d ".git" ]]; then
    log_warn "Not a git repository. Configuration will still work."
  fi
}
