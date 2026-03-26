# ws-ctx-engine MCP + Claude Desktop

## Prerequisites

- `ws-ctx-engine` is installed and available in `PATH`
- Repository has been indexed at least once

```bash
ws-ctx-engine index .
```

## Start MCP server

From your repository root:

```bash
ws-ctx-engine mcp --workspace .
```

## Configure Claude Desktop

Add a server entry to Claude Desktop MCP config:

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

Use an absolute workspace path to guarantee scope isolation.

## Available tools

- `search_codebase`
- `get_file_context`
- `get_domain_map`
- `get_index_status`

All tools are read-only and workspace-bound.
