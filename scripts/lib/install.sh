#!/usr/bin/env bash
# Install ctx-packer via pip or pipx

install_ctx_packer() {
  log_section "Installing ctx-packer"

  if command -v ctx-packer &> /dev/null; then
    local current_version
    current_version=$(ctx-packer --version 2>/dev/null | head -1 || echo "unknown")
    log_ok "ctx-packer already installed: $current_version"

    if [[ "${CTX_FORCE:-false}" == "true" ]]; then
      log_section "Reinstalling ctx-packer (--force)"
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
    pipx install --force "ctx-packer[all]" 2>/dev/null || pipx install --force ctx-packer
  elif command -v pip3 &> /dev/null; then
    log_ok "Installing via pip3..."
    pip3 install --user --upgrade "ctx-packer[all]" 2>/dev/null || pip3 install --user --upgrade ctx-packer
  elif command -v pip &> /dev/null; then
    log_ok "Installing via pip..."
    pip install --user --upgrade "ctx-packer[all]" 2>/dev/null || pip install --user --upgrade ctx-packer
  else
    log_error "pip not found. Please install pip first:"
    log_error "  curl https://bootstrap.pypa.io/get-pip.py | python3"
    exit 1
  fi

  export PATH="$HOME/Library/Python/3.11/bin:$PATH"
  if command -v ctx-packer &> /dev/null; then
    local new_version
    new_version=$(ctx-packer --version 2>/dev/null | head -1 || echo "installed")
    log_ok "ctx-packer installed: $new_version"
  else
    log_error "Installation failed. Please install manually:"
    log_error "  pip install ctx-packer"
    exit 1
  fi
}
