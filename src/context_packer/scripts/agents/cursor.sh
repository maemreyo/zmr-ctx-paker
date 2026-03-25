#!/usr/bin/env bash
# Cursor adapter

install_cursor() {
  local rules_dir="$CTX_TARGET/.cursor/rules"
  local rules_file="$rules_dir/ctx-packer.mdc"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "cursor/ctx-packer.mdc.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file (use --force to overwrite)"
  fi
}
