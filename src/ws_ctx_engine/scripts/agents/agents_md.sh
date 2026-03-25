#!/usr/bin/env bash
# AGENTS.md — Universal open standard

install_agents_md() {
  local agents_file="$CTX_TARGET/AGENTS.md"

  if [[ -f "$agents_file" ]]; then
    if grep -q "ws-ctx-engine" "$agents_file" 2>/dev/null; then
      if [[ "${CTX_FORCE:-false}" == "true" ]]; then
        _remove_section "$agents_file" "ws-ctx-engine — Code Packaging"
        _render_template "agents_md/AGENTS.md.tpl" >> "$agents_file"
        log_ok "Replaced ws-ctx-engine section in $agents_file (--force)"
      else
        log_skip "$agents_file (ws-ctx-engine already present)"
      fi
    else
      echo "" >> "$agents_file"
      _render_template "agents_md/AGENTS.md.tpl" >> "$agents_file"
      log_ok "Appended ws-ctx-engine to $agents_file"
    fi
  else
    _render_template "agents_md/AGENTS.md.tpl" > "$agents_file"
    log_ok "Created $agents_file"
  fi
}
