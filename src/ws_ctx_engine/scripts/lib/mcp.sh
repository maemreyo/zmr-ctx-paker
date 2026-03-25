#!/usr/bin/env bash
# MCP configuration bootstrap helpers for wsctx-init

emit_mcp_config() {
  local config_dir="$CTX_TARGET/.ws-ctx-engine"
  local config_file="$config_dir/mcp_config.json"

  if _should_write "$config_file"; then
    mkdir -p "$config_dir"
    _render_template "mcp/mcp_config.json.tpl" > "$config_file"
    log_ok "Created $config_file"
  else
    log_skip "$config_file (use --force to overwrite)"
  fi
}
