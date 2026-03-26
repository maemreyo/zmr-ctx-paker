# ws-ctx-engine MCP + Windsurf

## Quick setup

1. Build index once:

```bash
ws-ctx-engine index .
```

2. Register MCP server in Windsurf with this command:

```bash
ws-ctx-engine mcp --workspace /absolute/path/to/repo
```

## Example MCP server block

```json
{
  "mcpServers": {
    "ws-ctx-engine": {
      "command": "ws-ctx-engine",
      "args": ["mcp", "--workspace", "/absolute/path/to/repo"]
    }
  }
}
```

## Tooling exposed

- `search_codebase(query, limit?, domain_filter?)`
- `get_file_context(path, include_dependencies?, include_dependents?)`
- `get_domain_map()`
- `get_index_status()`

All operations are read-only.
