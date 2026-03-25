#!/usr/bin/env bash
# GitHub Copilot adapter

install_copilot() {
  local copilot_dir="$CTX_TARGET/.github"
  local copilot_file="$copilot_dir/copilot-instructions.md"

  if [[ -f "$copilot_file" ]]; then
    if grep -q "ctx-packer" "$copilot_file" 2>/dev/null; then
      if [[ "${CTX_FORCE:-false}" == "true" ]]; then
        _remove_section "$copilot_file" "ctx-packer"
        _render_template "copilot/copilot-instructions.md.tpl" >> "$copilot_file"
        log_ok "Replaced ctx-packer in $copilot_file (--force)"
      else
        log_skip "$copilot_file (ctx-packer already present)"
      fi
    else
      echo "" >> "$copilot_file"
      _render_template "copilot/copilot-instructions.md.tpl" >> "$copilot_file"
      log_ok "Appended ctx-packer to $copilot_file"
    fi
  else
    mkdir -p "$copilot_dir"
    _render_template "copilot/copilot-instructions.md.tpl" > "$copilot_file"
    log_ok "Created $copilot_file"
  fi
}
