#!/usr/bin/env bash
# AGENTS.md — Universal open standard

install_agents_md() {
  local agents_file="$CTX_TARGET/AGENTS.md"

  if [[ -f "$agents_file" ]]; then
    if grep -q "ctx-packer" "$agents_file" 2>/dev/null; then
      log_skip "$agents_file (ctx-packer already present)"
    else
      echo "" >> "$agents_file"
      _render_template "agents_md/AGENTS.md.tpl" >> "$agents_file"
      log_ok "Appended ctx-packer to $agents_file"
    fi
  else
    _render_template "agents_md/AGENTS.md.tpl" > "$agents_file"
    log_ok "Created $agents_file"
  fi
}
