#!/usr/bin/env bash
# OpenAI Codex adapter

install_codex() {
  local skill_dir="$CTX_TARGET/.agents/skills/ctx-packer"
  local skill_file="$skill_dir/SKILL.md"

  if _should_write "$skill_file"; then
    mkdir -p "$skill_dir"
    _render_template "codex/SKILL.md.tpl" > "$skill_file"
    log_ok "Created $skill_file"
  else
    log_skip "$skill_file (use --force to overwrite)"
  fi
}
