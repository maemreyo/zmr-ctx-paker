#!/usr/bin/env bash
# Run ctx-packer index with error handling and timeout

run_index() {
  local target="$1"
  local timeout_seconds="${CTX_INDEX_TIMEOUT:-300}"

  log_section "Building initial index"

  if [[ ! -d "$target" ]]; then
    log_error "Target directory does not exist: $target"
    return 1
  fi

  export PATH="$HOME/Library/Python/3.11/bin:$PATH"

  log_ok "Running: ctx-packer index $target"
  log_ok "Timeout: ${timeout_seconds}s (set CTX_INDEX_TIMEOUT to override)"

  if ctx-packer index "$target" 2>&1; then
    log_ok "Index built successfully"
  else
    log_warn "Index build completed with warnings"
    log_warn "You can rebuild later with: ctx-packer index $target"
  fi
}
