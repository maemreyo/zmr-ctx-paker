#!/usr/bin/env bash
# lib/selector.sh — Agent selection: gum-first, fallback to defaults

_agent_label() {
  local id="$1"
  local name desc default
  for e in "${AGENT_REGISTRY[@]}"; do
    [[ "$e" =~ ^${id}: ]] || continue
    IFS=: read -r _ name desc default <<< "$e"
    local marker=""
    [[ "$default" == "true" ]] && marker="(default)"
    printf "%-14s %-20s %s" "$id" "$name" "$marker"
    return
  done
}

select_agents_interactive() {
  local all_ids
  mapfile -t all_ids < <(get_agent_ids)

  local labels=()
  for id in "${all_ids[@]}"; do
    labels+=("$(_agent_label "$id")")
  done

  local selected
  selected=$(
    printf '%s\n' "${labels[@]}" | \
    gum choose \
      --no-limit \
      --header "Select AI agents to configure (space to toggle, enter to confirm):" \
      --selected="$(get_default_agents | xargs | tr ' ' ',')" \
      --cursor-prefix "○ " \
      --selected-prefix "● " \
      --unselected-prefix "  "
  )

  local result=()
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local id
    id=$(awk '{print $1}' <<< "$line")
    result+=("$id")
  done <<< "$selected"

  printf '%s\n' "${result[@]}"
}

select_agents_defaults() {
  get_default_agents
}

resolve_agents() {
  local -n _out=$1

  if [[ ${#SELECTED_AGENTS[@]} -gt 0 ]]; then
    if [[ "${SELECTED_AGENTS[0]}" == "all" ]]; then
      mapfile -t _out < <(get_agent_ids)
    else
      _out=("${SELECTED_AGENTS[@]}")
    fi
    return
  fi

  if ! _is_interactive; then
    log_warn "Non-interactive mode detected. Using defaults (or --agents flag)."
    mapfile -t _out < <(select_agents_defaults)
    return
  fi

  if _ensure_gum 2>/dev/null; then
    mapfile -t _out < <(select_agents_interactive)
    if [[ ${#_out[@]} -eq 0 ]]; then
      log_warn "No agents selected. Using defaults."
      mapfile -t _out < <(select_agents_defaults)
    fi
  else
    log_warn "Running with default agents. Pass --agents to customize."
    mapfile -t _out < <(select_agents_defaults)
  fi
}
