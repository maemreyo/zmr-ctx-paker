# ctx-packer MCP + Windsurf

## Quick setup

1. Build index once:

```bash
ctx-packer index .
```

2. Register MCP server in Windsurf with this command:

```bash
ctx-packer mcp --workspace /absolute/path/to/repo
```

## Example MCP server block

```json
{
  "mcpServers": {
    "ctx-packer": {
      "command": "ctx-packer",
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
