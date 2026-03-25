#!/usr/bin/env bash
# Cursor adapter

install_cursor() {
  local rules_dir="$CTX_TARGET/.cursor/rules"
  local rules_file="$rules_dir/ctx-packer.mdc"
  local legacy_rules_file="$CTX_TARGET/.cursorrules"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "cursor/ctx-packer.mdc.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file (use --force to overwrite)"
  fi

  if _should_write "$legacy_rules_file"; then
    _render_template "cursor/.cursorrules.tpl" > "$legacy_rules_file"
    log_ok "Created $legacy_rules_file"
  else
    log_skip "$legacy_rules_file (use --force to overwrite)"
  fi
}
