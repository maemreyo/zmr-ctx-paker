# mcp Command

Run ws-ctx-engine as an MCP (Model Context Protocol) stdio server.

## Usage

```bash
ws-ctx-engine mcp [OPTIONS]
```

## Options

| Option         | Short | Description                       |
| -------------- | ----- | --------------------------------- |
| `--workspace`  | `-w`  | Workspace root path               |
| `--mcp-config` |       | Path to MCP config JSON           |
| `--rate-limit` |       | Override rate limit as TOOL=LIMIT |

## Description

The `mcp` command starts ws-ctx-engine as an MCP server, enabling AI agents to interact with your codebase through standardized tool calls. This is the primary integration method for AI-powered IDEs and assistants.

## What is MCP?

**Model Context Protocol (MCP)** is a standard protocol that allows AI models to interact with external tools and services. It provides:

- **Standardized interface**: Common tool definition format
- **Tool discovery**: Automatic capability advertisement
- **Rate limiting**: Built-in request throttling
- **Error handling**: Structured error responses

## Examples

### Basic Server Start

```bash
# Start with current directory as workspace
ws-ctx-engine mcp --workspace .

# Start with specific workspace
ws-ctx-engine mcp -w /path/to/repo
```

### With Custom Configuration

```bash
# Use custom MCP config
ws-ctx-engine mcp -w /path/to/repo --mcp-config mcp-settings.json
```

### With Rate Limiting

```bash
# Set rate limit for search_codebase tool
ws-ctx-engine mcp -w . --rate-limit search_codebase=60

# Multiple rate limits
ws-ctx-engine mcp -w . --rate-limit search_codebase=60 --rate-limit query_codebase=30
```

## Available MCP Tools

When running as an MCP server, ws-ctx-engine exposes these tools:

### Search Tools

**`search_codebase`**
- Semantic code search
- Returns ranked file paths
- Parameters: `query`, `limit`, `domain_filter`

**`get_file_context`**  
- Retrieve full file content with dependencies
- Parameters: `file_path`, `include_dependencies`

### Graph Tools

**`get_symbol_info`**
- Get symbol definitions and references
- Parameters: `symbol_name`, `file_path`

**`trace_call_chain`**
- Trace execution path between functions
- Parameters: `from_fn`, `to_fn`

### Context Tools

**`pack_context`**
- Generate LLM-ready context packages
- Parameters: `query`, `format`, `budget`, `mode`

**`get_domain_map`**
- Retrieve domain keyword mappings
- Parameters: None

### Admin Tools

**`get_index_status`**
- Check index health and statistics
- Parameters: None

**`rebuild_index`**
- Trigger index rebuild
- Parameters: `incremental`

## Integration Examples

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ws-ctx-engine": {
      "command": "ws-ctx-engine",
      "args": ["mcp", "-w", "/path/to/your/project"],
      "env": {}
    }
  }
}
```

### Cursor IDE

Add to Cursor settings:

```json
{
  "mcp": {
    "servers": {
      "ws-ctx-engine": {
        "command": "ws-ctx-engine",
        "args": ["mcp", "-w", "${workspaceFolder}"]
      }
    }
  }
}
```

### Windsurf

Windsurf auto-detects ws-ctx-engine when installed in project.

## Rate Limiting

Prevent API abuse with rate limits:

```bash
# Allow 60 requests per minute to search
ws-ctx-engine mcp -w . --rate-limit search_codebase=60

# Different limits per tool
ws-ctx-engine mcp \
  -w . \
  --rate-limit search_codebase=120 \
  --rate-limit pack_context=30 \
  --rate-limit get_symbol_info=200
```

**Default Limits:**
- Search operations: 60/min
- Pack operations: 30/min
- Graph operations: 200/min
- Status operations: Unlimited

## MCP Config File

Create a JSON config file for advanced settings:

```json
{
  "server_name": "ws-ctx-engine",
  "version": "1.0.0",
  "tools": {
    "search_codebase": {
      "description": "Search codebase semantically",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "limit": {"type": "number", "default": 10}
        }
      }
    }
  },
  "rate_limits": {
    "search_codebase": 60,
    "pack_context": 30
  }
}
```

Usage:
```bash
ws-ctx-engine mcp -w . --mcp-config mcp-settings.json
```

## Output Modes

### Human Mode (Default)
Verbose output with status messages:

```
Starting MCP server...
Workspace: /path/to/repo
Available tools: search_codebase, pack_context, ...
Listening for requests...
```

### Quiet Mode
Minimal output for production:

```bash
ws-ctx-engine mcp -w . --quiet
```

## Troubleshooting

**"Workspace not found"**
- Verify workspace path exists
- Use absolute paths

**"Port already in use"**
- MCP uses stdio, not network ports
- Check no other process using same workspace

**"Tool not available"**
- Ensure indexes are built
- Check tool name spelling

**"Rate limit exceeded"**
- Increase limit with `--rate-limit`
- Or reduce request frequency

## Best Practices

### Development

```bash
# Start server in background
ws-ctx-engine mcp -w . &

# Test connection
ws-ctx-engine status .
```

### Production

```bash
# Start with systemd or supervisor
[Service]
ExecStart=/usr/bin/ws-ctx-engine mcp -w /var/www/project --quiet
Restart=always
```

### Docker

```dockerfile
CMD ["ws-ctx-engine", "mcp", "-w", "/app"]
```

## Security Considerations

### Access Control
- MCP server runs locally (stdio)
- No network exposure by default
- File access limited to workspace

### Sensitive Data
- Enable secret scanning in config
- Review tool outputs
- Monitor rate limits

### Resource Usage
- Set appropriate rate limits
- Monitor memory usage
- Configure token budgets

## Related Commands

- [`status`](status.md) - Check index status before starting server
- [`index`](index.md) - Build indexes needed for server
- [`query`](query.md) - CLI equivalent of pack_context tool

## Related Documentation

- [MCP Server Guide](../../integrations/mcp-server.md) - Complete setup guide
- [Claude Desktop Integration](../../integrations/claude-desktop.md) - Claude setup
- [Cursor Integration](../../integrations/cursor.md) - Cursor IDE setup
- [Agent Workflows](../../integrations/agent-workflows.md) - Agent patterns
