#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# AGENT REGISTRY — source of truth for all supported agents
# Format: "id:display_name:description:default_enabled"
# ──────────────────────────────────────────────────────────

AGENT_REGISTRY=(
  "agents_md:AGENTS.md (Universal):Open standard, works with Codex/Copilot/Jules/Amp/RooCode:true"
  "claude:Claude Code:Anthropic's terminal-based agentic coding tool:true"
  "cursor:Cursor:.cursor/rules/*.mdc format for Cursor IDE:true"
  "windsurf:Windsurf:Cascade rules in .windsurf/rules/:true"
  "trae:TRAE:.rules file for ByteDance TRAE IDE:false"
  "codex:OpenAI Codex:.agents/skills/ format for Codex CLI:false"
  "copilot:GitHub Copilot:.github/copilot-instructions.md:false"
)

get_agent_ids() {
  for entry in "${AGENT_REGISTRY[@]}"; do
    echo "${entry%%:*}"
  done
}

get_default_agents() {
  for e in "${AGENT_REGISTRY[@]}"; do
    if [[ "$e" == *":true" ]]; then
      echo "${e%%:*}"
    fi
  done
}

is_valid_agent() {
  local id="$1"
  for entry in "${AGENT_REGISTRY[@]}"; do
    [[ "${entry%%:*}" == "$id" ]] && return 0
  done
  return 1
}

get_agent_display() {
  local id="$1"
  for e in "${AGENT_REGISTRY[@]}"; do
    if [[ "$e" =~ ^${id}: ]]; then
      IFS=: read -r _ name _ <<< "$e"
      echo "$name"
      return
    fi
  done
  echo "$id"
}

get_agent_desc() {
  local id="$1"
  for e in "${AGENT_REGISTRY[@]}"; do
    if [[ "$e" =~ ^${id}: ]]; then
      IFS=: read -r _ _ desc _ <<< "$e"
      echo "$desc"
      return
    fi
  done
}
