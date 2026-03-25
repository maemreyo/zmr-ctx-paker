#!/usr/bin/env bash
# TRAE adapter

install_trae() {
  local rules_file="$CTX_TARGET/.rules"

  if [[ -f "$rules_file" ]]; then
    if grep -q "ctx-packer" "$rules_file" 2>/dev/null; then
      log_skip "$rules_file (ctx-packer already present)"
    else
      echo "" >> "$rules_file"
      _render_template "trae/.rules.tpl" >> "$rules_file"
      log_ok "Appended ctx-packer section to $rules_file"
    fi
  else
    _render_template "trae/.rules.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  fi
}
