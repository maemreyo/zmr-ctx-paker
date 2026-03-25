#!/usr/bin/env bash
# lib/commands.sh — Canonical command strings, sourced from CLI output
# Đây là single source of truth cho tất cả templates.

_discover_commands() {
  _ensure_ws_ctx_engine_in_path

  if command -v wsctx &>/dev/null; then
    local help_output
    help_output="$(ws-ctx-engine --help 2>&1)"

    CMD_INDEX="index"
    CMD_SEARCH="search"
    CMD_QUERY="query"
    CMD_PACK="pack"
    CMD_STATUS="status"
    CMD_VACUUM="vacuum"
    CMD_REINDEX_DOMAIN="reindex-domain"

    for cmd in "$CMD_INDEX" "$CMD_SEARCH" "$CMD_PACK" "$CMD_STATUS" "$CMD_VACUUM"; do
      if ! grep -q "^  $cmd\b" <<< "$help_output" 2>/dev/null; then
        log_warn "Command 'ws-ctx-engine $cmd' not found in --help output."
        log_warn "Template may be outdated. Please update lib/commands.sh."
      fi
    done
  fi

  export CTX_CMD_INDEX="ws-ctx-engine ${CMD_INDEX:=index} ."
  export CTX_CMD_SEARCH='ws-ctx-engine '"${CMD_SEARCH:=search}"' "<query>"'
  export CTX_CMD_PACK='ws-ctx-engine '"${CMD_PACK:=pack}"' . --query "<topic>"'
  export CTX_CMD_STATUS="ws-ctx-engine ${CMD_STATUS:=status} ."
  export CTX_CMD_VACUUM="ws-ctx-engine ${CMD_VACUUM:=vacuum}"
  export CTX_CMD_REINDEX_DOMAIN="ws-ctx-engine ${CMD_REINDEX_DOMAIN:=reindex-domain} ."
  export CTX_CMD_FULL_ZIP='ws-ctx-engine '"${CMD_PACK:=pack}"' . --query "<topic>" --format zip'
  export CTX_CMD_FULL_XML='ws-ctx-engine '"${CMD_PACK:=pack}"' . --query "<topic>" --format xml'
}
