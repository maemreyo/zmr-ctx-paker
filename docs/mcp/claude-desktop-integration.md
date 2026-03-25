# ctx-packer MCP + Claude Desktop

## Prerequisites

- `ctx-packer` is installed and available in `PATH`
- Repository has been indexed at least once

```bash
ctx-packer index .
```

## Start MCP server

From your repository root:

```bash
ctx-packer mcp --workspace .
```

## Configure Claude Desktop

Add a server entry to Claude Desktop MCP config:

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

Use an absolute workspace path to guarantee scope isolation.

## Available tools

- `search_codebase`
- `get_file_context`
- `get_domain_map`
- `get_index_status`

All tools are read-only and workspace-bound.
