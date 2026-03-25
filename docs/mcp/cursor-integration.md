# ws-ctx-engine MCP + Cursor

## 1) Prepare workspace

```bash
ws-ctx-engine index .
```

## 2) Run MCP server command

Cursor should launch this command for the workspace:

```bash
ws-ctx-engine mcp --workspace /absolute/path/to/repo
```

## 3) Cursor MCP configuration

In Cursor MCP settings (or `.cursor/mcp.json`), register:

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

## Notes

- Keep one MCP server per workspace for strict path isolation.
- Re-run `ws-ctx-engine index .` after large code changes to improve relevance.
