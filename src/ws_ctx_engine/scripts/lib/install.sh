#!/usr/bin/env bash
# Install ws-ctx-engine via pip or pipx

install_ws_ctx_engine() {
  log_section "Installing ws-ctx-engine"
  _ensure_ws_ctx_engine_in_path

  if command -v wsctx &> /dev/null; then
    local current_version
    current_version=$(wsctx --version 2>/dev/null | head -1 || echo "unknown")
    log_ok "ws-ctx-engine already installed: $current_version"

    if [[ "${CTX_FORCE:-false}" == "true" ]]; then
      log_section "Reinstalling ws-ctx-engine (--force)"
      _do_install
    else
      return 0
    fi
  else
    _do_install
  fi
}

_do_install() {
  if command -v pipx &> /dev/null; then
    log_ok "Installing via pipx..."
    pipx install --force "ws-ctx-engine[all]" 2>/dev/null || pipx install --force ws-ctx-engine
  elif command -v pip3 &> /dev/null; then
    log_ok "Installing via pip3..."
    pip3 install --user --upgrade "ws-ctx-engine[all]" 2>/dev/null || pip3 install --user --upgrade ws-ctx-engine
  elif command -v pip &> /dev/null; then
    log_ok "Installing via pip..."
    pip install --user --upgrade "ws-ctx-engine[all]" 2>/dev/null || pip install --user --upgrade ws-ctx-engine
  else
    log_error "pip not found. Please install pip first:"
    log_error "  curl https://bootstrap.pypa.io/get-pip.py | python3"
    exit 1
  fi

  _ensure_ws_ctx_engine_in_path
  if command -v wsctx &> /dev/null; then
    local new_version
    new_version=$(wsctx --version 2>/dev/null | head -1 || echo "installed")
    log_ok "ws-ctx-engine installed: $new_version"
  else
    log_error "Installation failed. Please install manually:"
    log_error "  pip install ws-ctx-engine"
    exit 1
  fi
}
