#!/usr/bin/env bash
# TRAE adapter

install_trae() {
  local rules_file="$CTX_TARGET/.rules"

  if [[ -f "$rules_file" ]]; then
    if grep -q "ws-ctx-engine" "$rules_file" 2>/dev/null; then
      if [[ "${CTX_FORCE:-false}" == "true" ]]; then
        _remove_section "$rules_file" "ws-ctx-engine"
        _render_template "trae/.rules.tpl" >> "$rules_file"
        log_ok "Replaced ws-ctx-engine section in $rules_file (--force)"
      else
        log_skip "$rules_file (ws-ctx-engine already present)"
      fi
    else
      echo "" >> "$rules_file"
      _render_template "trae/.rules.tpl" >> "$rules_file"
      log_ok "Appended ws-ctx-engine section to $rules_file"
    fi
  else
    _render_template "trae/.rules.tpl" > "$rules_file"
    log_ok "Created $rules_file"
  fi
}
