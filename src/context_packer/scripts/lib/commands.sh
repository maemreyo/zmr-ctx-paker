#!/usr/bin/env bash
# lib/commands.sh — Canonical command strings, sourced from CLI output
# Đây là single source of truth cho tất cả templates.

_discover_commands() {
  _ensure_ctx_packer_in_path

  if command -v ctx-packer &>/dev/null; then
    local help_output
    help_output="$(ctx-packer --help 2>&1)"

    CMD_INDEX="index"
    CMD_QUERY="query"
    CMD_PACK="pack"
    CMD_STATUS="status"
    CMD_VACUUM="vacuum"
    CMD_REINDEX_DOMAIN="reindex-domain"

    for cmd in "$CMD_INDEX" "$CMD_QUERY" "$CMD_PACK" "$CMD_STATUS" "$CMD_VACUUM"; do
      if ! grep -q "^  $cmd\b" <<< "$help_output" 2>/dev/null; then
        log_warn "Command 'ctx-packer $cmd' not found in --help output."
        log_warn "Template may be outdated. Please update lib/commands.sh."
      fi
    done
  fi

  export CTX_CMD_INDEX="ctx-packer ${CMD_INDEX:=index} ."
  export CTX_CMD_QUERY='ctx-packer '"${CMD_QUERY:=query}"' "<query>"'
  export CTX_CMD_PACK='ctx-packer '"${CMD_PACK:=pack}"' . --query "<topic>"'
  export CTX_CMD_STATUS="ctx-packer ${CMD_STATUS:=status} ."
  export CTX_CMD_VACUUM="ctx-packer ${CMD_VACUUM:=vacuum}"
  export CTX_CMD_REINDEX_DOMAIN="ctx-packer ${CMD_REINDEX_DOMAIN:=reindex-domain} ."
  export CTX_CMD_FULL_ZIP='ctx-packer '"${CMD_PACK:=pack}"' . --query "<topic>" --format zip'
  export CTX_CMD_FULL_XML='ctx-packer '"${CMD_PACK:=pack}"' . --query "<topic>" --format xml'
}
