#!/usr/bin/env bash
# Claude Code adapter

install_claude() {
  local skill_dir="$CTX_TARGET/.claude/skills/ctx-packer"
  local skill_file="$skill_dir/SKILL.md"
  local claude_md="$CTX_TARGET/.claude/CLAUDE.md"

  if _should_write "$skill_file"; then
    mkdir -p "$skill_dir"
    _render_template "claude/SKILL.md.tpl" > "$skill_file"
    log_ok "Created $skill_file"
  else
    log_skip "$skill_file (use --force to overwrite)"
  fi

  if [[ -f "$claude_md" ]]; then
    if grep -q "ctx-packer" "$claude_md" 2>/dev/null; then
      log_skip "$claude_md (ctx-packer section already present)"
    else
      echo "" >> "$claude_md"
      _render_template "claude/CLAUDE_append.md.tpl" >> "$claude_md"
      log_ok "Updated $claude_md (appended ctx-packer section)"
    fi
  else
    mkdir -p "$(dirname "$claude_md")"
    _render_template "claude/CLAUDE_append.md.tpl" > "$claude_md"
    log_ok "Created $claude_md"
  fi
}
