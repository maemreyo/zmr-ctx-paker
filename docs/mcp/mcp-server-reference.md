# ws-ctx-engine MCP Server Reference

## Entry points

- CLI: `ws-ctx-engine mcp --workspace <path>`
- Module: `python -m ws_ctx_engine.mcp_server`

## Workspace binding

The server is bound to one workspace root. All file requests are resolved under that root and blocked if they escape it.

## Security model

- Read-only tool registry (no write/exec tools)
- Path traversal guard
- RADE content delimiters for safe file payload boundaries
- Secret scanning with cache (`.ws-ctx-engine/secret_scan_cache.json`)
- Per-tool rate limiting

## Tool reference

### `search_codebase`

**Input**

- `query` (string, required)
- `limit` (int, optional, default `10`, range `1..50`)
- `domain_filter` (string, optional)

**Output**

- `results`: ranked file list
- `index_health`: freshness/status block

### `get_file_context`

**Input**

- `path` (string, required)
- `include_dependencies` (bool, optional, default `true`)
- `include_dependents` (bool, optional, default `true`)

**Output**

- file metadata (`path`, `language`, `line_count`)
- wrapped file `content` when safe
- `dependencies`, `dependents`
- `secrets_detected`, `sanitized`
- `index_health`

If secrets are detected, `content` is omitted and a safe error message is returned.

### `get_domain_map`

**Input**: empty object

**Output**

- `domains` (top architecture domains)
- `graph_stats`
- `index_health`

### `get_index_status`

**Input**: empty object

**Output**

- `index_health`
- `recommendation`
- `workspace`

## Errors

Common error codes:

- `TOOL_NOT_FOUND`
- `INVALID_ARGUMENT`
- `INDEX_NOT_FOUND`
- `FILE_NOT_FOUND`
- `FILE_READ_FAILED`
- `RATE_LIMIT_EXCEEDED`
- `SEARCH_FAILED`

## Configuration

Default config path: `.ws-ctx-engine/mcp_config.json`

Supported fields:

- `workspace` (optional)
- `cache_ttl_seconds` (positive integer)
- `rate_limits` per tool (positive integers)
