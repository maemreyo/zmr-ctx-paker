#!/usr/bin/env bash
# Run wsctx index with timeout and error handling

run_index() {
  local target="$1"
  local timeout_seconds="${CTX_INDEX_TIMEOUT:-300}"

  log_section "Building initial index"
  _ensure_ws_ctx_engine_in_path

  if [[ ! -d "$target" ]]; then
    log_error "Target directory does not exist: $target"
    return 1
  fi

  log_ok "Running: wsctx index $target"
  log_ok "Timeout: ${timeout_seconds}s (set CTX_INDEX_TIMEOUT to override)"

  local exit_code=0
  if timeout "$timeout_seconds" wsctx index "$target"; then
    log_ok "Index built successfully"
  else
    exit_code=$?
    if [[ $exit_code -eq 124 ]]; then
      log_warn "Index timed out after ${timeout_seconds}s"
    else
      log_warn "Index exited with code $exit_code. Check output above."
    fi
  fi
}
