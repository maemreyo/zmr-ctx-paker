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
  
  export CTX_PACKER_VERSION
  export CTX_DATE
  export CTX_TARGET_NAME

  envsubst '
    ${CTX_DATE}
    ${CTX_PACKER_VERSION}
    ${CTX_TARGET_NAME}
    ${CTX_CMD_INDEX}
    ${CTX_CMD_QUERY}
    ${CTX_CMD_PACK}
    ${CTX_CMD_STATUS}
    ${CTX_CMD_VACUUM}
    ${CTX_CMD_REINDEX_DOMAIN}
    ${CTX_CMD_FULL_ZIP}
    ${CTX_CMD_FULL_XML}
  ' < "$tpl"
}

_remove_section() {
  local file="$1"
  local marker="${2:-ctx-packer}"
  [[ -f "$file" ]] || return 0
  
  local tmp
  tmp="$(mktemp)"
  awk -v marker="^# ${marker}" '
    /^# / && found { found=0 }
    $0 ~ marker { found=1 }
    !found { print }
  ' "$file" > "$tmp" && mv "$tmp" "$file"
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
  --agents <list>   Comma-separated agent IDs, or 'all'
  --skip-index      Skip running ctx-packer index after setup
  --force           Overwrite existing config files
  --list-agents     Show all supported agents
  -h, --help        Show this help
  -v, --version     Show version

Examples:
  ctx-packer-init
  ctx-packer-init --agents claude,cursor,agents_md
  ctx-packer-init --agents all --force
  ctx-packer-init --path ~/my-project --skip-index

EOF
}

show_version() {
  _ensure_ctx_packer_in_path
  if command -v ctx-packer &> /dev/null; then
    local version
    version=$(ctx-packer --version 2>/dev/null || echo "ctx-packer version: unknown")
    echo "$version"
  else
    echo "ctx-packer-init (ctx-packer not installed yet)"
  fi
}

check_git() {
  if [[ ! -d "$CTX_TARGET/.git" ]]; then
    log_warn "Not a git repository. Configuration will still work."
  fi
}

_has_gum() { command -v gum &>/dev/null; }

_ensure_gum() {
  _has_gum && return 0

  log_warn "gum (interactive UI) not found."

  if _has_gum_installer; then
    if gum confirm "Install gum for interactive agent selection?"; then
      _install_gum && return 0
    fi
  else
    log_warn "Cannot auto-install gum. Using defaults."
  fi
  return 1
}

_has_gum_installer() {
  command -v brew &>/dev/null || command -v apt-get &>/dev/null || \
  command -v pacman &>/dev/null || command -v nix-env &>/dev/null
}

_install_gum() {
  if command -v brew &>/dev/null; then
    brew install gum
  elif command -v apt-get &>/dev/null; then
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://repo.charm.sh/apt/gpg.key \
      | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
    echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" \
      | sudo tee /etc/apt/sources.list.d/charm.list
    sudo apt update && sudo apt install -y gum
  elif command -v pacman &>/dev/null; then
    sudo pacman -S --noconfirm gum
  fi
}

_is_interactive() {
  [[ -t 0 ]] && [[ -t 1 ]]
}

_ensure_ctx_packer_in_path() {
  local user_bin
  user_bin="$(python3 -m site --user-base 2>/dev/null)/bin"
  if [[ -d "$user_bin" ]]; then
    export PATH="$user_bin:$PATH"
  fi
}
