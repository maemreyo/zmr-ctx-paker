# MCP Setup Guide for Qoder

## Quick Start

This guide helps you configure the Model Context Protocol (MCP) server for Qoder IDE.

## Prerequisites

Make sure `ws-ctx-engine` is installed:

```bash
pip install -e .
# or
uv pip install -e .
```

Verify installation:
```bash
wsctx --version
```

## Configuration Steps

### Step 1: Initialize the Engine (First Time Only)

Before using MCP, initialize the workspace:

```bash
cd /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker
wsctx init
```

This will:
- Create `.ws-ctx-engine/` directory with configuration
- Build code index and embeddings
- Set up domain mappings

### Step 2: Configure Qoder MCP

**Option A: Copy from project template**

Copy the content from `docs/mcp/setup-guide/qoder/mcp.json.example` to Qoder's MCP config location:

Source: `docs/mcp/setup-guide/qoder/mcp.json.example`
Destination: `/Users/trung.ngo/Library/Application Support/Qoder/SharedClientCache/mcp.json`

**Option B: Manual configuration**

Edit `/Users/trung.ngo/Library/Application Support/Qoder/SharedClientCache/mcp.json`:

```json
{
  "mcpServers": {
    "ws-ctx-engine": {
      "command": "wsctx",
      "args": ["mcp", "--workspace", "/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker"]
    }
  }
}
```

**Option C: Use wsctx-init helper**

```bash
wsctx-init mcp --target /Users/trung.ngo/Library/Application\ Support/Qoder/SharedClientCache
```

### Step 3: Restart Qoder

After configuring, restart Qoder IDE to load the MCP server.

## Available MCP Tools

Once configured, you'll have access to these tools:

### 1. `search_codebase`
Search the codebase semantically.

**Parameters:**
- `query` (string, required): Search query
- `limit` (int, optional, default 10): Max results (1-50)
- `domain_filter` (string, optional): Filter by domain

**Example:**
```
search_codebase(query="authentication logic", limit=5)
```

### 2. `get_file_context`
Get file content with dependency context.

**Parameters:**
- `path` (string, required): File path relative to workspace
- `include_dependencies` (bool, optional, default true): Include dependencies
- `include_dependents` (bool, optional, default true): Include dependents

**Example:**
```
get_file_context(path="src/ws_ctx_engine/mcp/server.py")
```

### 3. `get_domain_map`
Get architecture domain information.

**Parameters:** None

### 4. `get_index_status`
Check index health and status.

**Parameters:** None

## Security Features

The MCP server includes:
- ✅ Path traversal protection
- ✅ Read-only access (no write/exec tools)
- ✅ Secret scanning with caching
- ✅ Per-tool rate limiting
- ✅ Content delimiters for safe boundaries

### Default Rate Limits

- `search_codebase`: 60 requests/minute
- `get_file_context`: 120 requests/minute
- `get_domain_map`: 10 requests/minute
- `get_index_status`: 10 requests/minute

## Customization

### Change Workspace

Edit the `--workspace` argument in `mcp.json`:

```json
{
  "mcpServers": {
    "ws-ctx-engine": {
      "command": "wsctx",
      "args": ["mcp", "--workspace", "/path/to/your/project"]
    }
  }
}
```

### Adjust Rate Limits

Create/edit `.ws-ctx-engine/mcp_config.json`:

```json
{
  "workspace": "/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker",
  "rate_limits": {
    "search_codebase": 60,
    "get_file_context": 120,
    "get_domain_map": 10,
    "get_index_status": 10
  },
  "cache_ttl_seconds": 30
}
```

## Troubleshooting

### MCP Server Not Loading

1. Check if `wsctx` command is available:
   ```bash
   which wsctx
   ```

2. Verify MCP config syntax:
   ```bash
   python -m json.tool /Users/trung.ngo/Library/Application\ Support/Qoder/SharedClientCache/mcp.json
   ```

3. Check Qoder logs for MCP errors

### Index Not Found Errors

Run initialization:
```bash
wsctx init --force
```

### Permission Issues

Ensure Qoder has access to the workspace directory:
```bash
ls -la /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker
```

## Testing the Setup

After configuration, test the MCP server:

```bash
# Run comprehensive tests
python scripts/mcp/mcp_comprehensive_test.py

# Or simple smoke test
wsctx mcp --workspace /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker
```

## Performance Tips

1. **Pre-warming**: The server pre-loads models in background (~200ms)
2. **Caching**: Results cached for 30 seconds by default
3. **ONNX Backend**: Uses optimized ONNX runtime when available
4. **Batch Operations**: Group related queries together

## Additional Resources

- [MCP Server Documentation](docs/integrations/mcp-server.md)
- [MCP Protocol Implementation](docs/reference/mcp-protocol.md)
- [Performance Optimization Guide](docs/performance/MCP_PERFORMANCE_OPTIMIZATION.md)
- [CLI Reference](docs/cli-reference.md#mcp-server)

## Example Usage in Qoder

Once configured, you can use natural language queries:

**Example 1: Find authentication code**
> "Search for authentication logic in the codebase"

**Example 2: Get file with context**
> "Show me the MCP server implementation with its dependencies"

**Example 3: Check index status**
> "Is the codebase index up to date?"

**Example 4: Explore architecture**
> "What are the main architectural domains?"

---

**Last Updated:** March 27, 2026
**Version:** ws-ctx-engine 0.1.10
