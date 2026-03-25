# ctx-packer MCP + Cursor

## 1) Prepare workspace

```bash
ctx-packer index .
```

## 2) Run MCP server command

Cursor should launch this command for the workspace:

```bash
ctx-packer mcp --workspace /absolute/path/to/repo
```

## 3) Cursor MCP configuration

In Cursor MCP settings (or `.cursor/mcp.json`), register:

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

## Notes

- Keep one MCP server per workspace for strict path isolation.
- Re-run `ctx-packer index .` after large code changes to improve relevance.
