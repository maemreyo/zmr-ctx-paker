#!/usr/bin/env bash
# GitHub Copilot adapter

install_copilot() {
  local copilot_dir="$CTX_TARGET/.github"
  local copilot_file="$copilot_dir/copilot-instructions.md"

  if [[ -f "$copilot_file" ]]; then
    if grep -q "ws-ctx-engine" "$copilot_file" 2>/dev/null; then
      if [[ "${CTX_FORCE:-false}" == "true" ]]; then
        _remove_section "$copilot_file" "ws-ctx-engine"
        _render_template "copilot/copilot-instructions.md.tpl" >> "$copilot_file"
        log_ok "Replaced ws-ctx-engine in $copilot_file (--force)"
      else
        log_skip "$copilot_file (ws-ctx-engine already present)"
      fi
    else
      echo "" >> "$copilot_file"
      _render_template "copilot/copilot-instructions.md.tpl" >> "$copilot_file"
      log_ok "Appended ws-ctx-engine to $copilot_file"
    fi
  else
    mkdir -p "$copilot_dir"
    _render_template "copilot/copilot-instructions.md.tpl" > "$copilot_file"
    log_ok "Created $copilot_file"
  fi
}
