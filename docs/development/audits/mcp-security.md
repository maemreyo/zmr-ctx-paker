# ws-ctx-engine MCP Security Audit (Tooling Layer)

_Date:_ 2026-03-25

## Scope

Audit of the four exposed MCP tools:

- `search_codebase`
- `get_file_context`
- `get_domain_map`
- `get_index_status`

## Controls Verified

1. **Read-only registry enforcement**
   - Unknown or write-style tool names are rejected with `TOOL_NOT_FOUND`.

2. **Workspace scope isolation + traversal protection**
   - Relative path resolution is anchored to configured workspace root.
   - Absolute/out-of-workspace paths and traversal attempts are denied (`ACCESS_DENIED`).
   - Symlink escape is blocked.

3. **Secret handling in file context**
   - Secret scan runs before file content return.
   - Secret-bearing files return `content: null` + `secrets_detected`.
   - Scan cache persisted at `.ws-ctx-engine/secret_scan_cache.json`.

4. **RADE data-boundary wrapping**
   - Safe file content is wrapped with start/end delimiters.
   - Delimiter token is session-derived and not exposed as a dedicated payload field.

5. **Rate limiting**
   - Per-tool configurable token-bucket limiter is enforced.
   - Exceeded requests return `RATE_LIMIT_EXCEEDED` with `retry_after_seconds`.

## Evidence (tests)

- `tests/unit/test_mcp_tools.py`
- `tests/property/test_mcp_security_properties.py`
- `tests/integration/test_mcp_integration.py`
- `tests/unit/test_mcp_rate_limiter.py`

## Residual Risk Notes

- Security behavior depends on correct workspace binding at startup.
- If index metadata is absent/stale, quality degrades but security boundaries remain active.

## Conclusion

Current MCP implementation satisfies core security requirements for read-only, workspace-bound operation with path-escape prevention, secret-aware file responses, RADE wrapping, and throttling controls.
