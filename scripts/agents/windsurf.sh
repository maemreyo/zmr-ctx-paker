#!/usr/bin/env bash
# Windsurf / Cascade adapter

install_windsurf() {
  local rules_dir="$CTX_TARGET/.windsurf/rules"
  local rules_file="$rules_dir/ctx-packer.md"

  if _should_write "$rules_file"; then
    mkdir -p "$rules_dir"
    _render_template "windsurf/ctx-packer.md.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  else
    log_skip "$rules_file (use --force to overwrite)"
  fi
}
