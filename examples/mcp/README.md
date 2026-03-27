# MCP Tool Calling Examples for ws-ctx-engine

This guide demonstrates how to call MCP tools within the ws-ctx-engine server.

## Available Tools

The ws-ctx-engine MCP server provides **12 powerful tools**:

### 1. **search_codebase** - Semantic Search
Search your codebase using natural language queries.

```json
{
  "name": "search_codebase",
  "arguments": {
    "query": "authentication logic",
    "limit": 10,
    "domain_filter": "security"
  }
}
```

**Parameters:**
- `query` (required): Your search query
- `limit` (optional, default: 10): Number of results (1-50)
- `domain_filter` (optional): Filter by domain keyword

---

### 2. **get_file_context** - File with Dependencies
Get file content along with its dependencies and dependents.

```json
{
  "name": "get_file_context",
  "arguments": {
    "path": "src/ws_ctx_engine/mcp/server.py",
    "include_dependencies": true,
    "include_dependents": true
  }
}
```

**Parameters:**
- `path` (required): File path relative to workspace
- `include_dependencies` (optional, default: true): Include files this depends on
- `include_dependents` (optional, default: true): Include files that depend on this

---

### 3. **get_domain_map** - Architecture Domains
View the architecture domain mapping of your codebase.

```json
{
  "name": "get_domain_map",
  "arguments": {}
}
```

---

### 4. **get_index_status** / **index_status** - Index Health
Check if your indexes are up-to-date.

```json
{
  "name": "get_index_status",
  "arguments": {}
}
```

---

### 5. **pack_context** - Context Packaging
Package relevant files into various formats (XML, JSON, YAML, Markdown, ZIP).

```json
{
  "name": "pack_context",
  "arguments": {
    "query": "MCP server implementation",
    "format": "xml",
    "token_budget": 50000,
    "agent_phase": "edit"
  }
}
```

**Parameters:**
- `query` (required): What context you need
- `format` (optional, default: xml): Output format (xml/json/yaml/md/zip)
- `token_budget` (optional): Maximum tokens (≥1000)
- `agent_phase` (optional): Phase weighting (discovery/edit/test)

---

### 6. **session_clear** - Cache Management
Clear session deduplication caches.

```json
{
  "name": "session_clear",
  "arguments": {
    "session_id": "my-session-123"
  }
}
```

**Parameters:**
- `session_id` (optional): Specific session to clear (omit to clear all)

---

### 7. **find_callers** - Call Graph Analysis
Find all functions that call a specific function.

```json
{
  "name": "find_callers",
  "arguments": {
    "fn_name": "authenticate"
  }
}
```

**Parameters:**
- `fn_name` (required): Function name to find callers for

---

### 8. **impact_analysis** - Change Impact
Analyze what files would be affected by changing a file.

```json
{
  "name": "impact_analysis",
  "arguments": {
    "file_path": "src/ws_ctx_engine/mcp/tools.py"
  }
}
```

**Parameters:**
- `file_path` (required): File to analyze impact for

---

### 9. **graph_search** - Symbol Discovery
List all symbols (functions, classes, constants) in a file.

```json
{
  "name": "graph_search",
  "arguments": {
    "file_id": "src/ws_ctx_engine/mcp/server.py"
  }
}
```

**Parameters:**
- `file_id` (required): File to analyze

---

### 10. **call_chain** - Call Path Tracing
Trace the call path between two functions.

```json
{
  "name": "call_chain",
  "arguments": {
    "from_fn": "main",
    "to_fn": "authenticate",
    "max_depth": 5
  }
}
```

**Parameters:**
- `from_fn` (required): Starting function
- `to_fn` (required): Target function
- `max_depth` (optional, default: 5): Maximum BFS hops (1-10)

---

### 11. **get_status** - Server Status
Get comprehensive server status including index health and graph statistics.

```json
{
  "name": "get_status",
  "arguments": {}
}
```

---

## Complete Example Script

See [`examples/mcp_tool_example.py`](examples/mcp_tool_example.py) for a full working example.

## Running the Example

```bash
# Using uv (recommended)
uv run python3.13 examples/mcp_tool_example.py

# Or activate virtual environment first
source .venv/bin/activate
python examples/mcp_tool_example.py
```

## JSON-RPC Format

All tool calls use the JSON-RPC 2.0 format:

### Request Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_codebase",
    "arguments": {
      "query": "your query here"
    }
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"results\": [...]}"
      }
    ],
    "structuredContent": {
      "results": [...],
      "index_health": {...}
    }
  }
}
```

## Usage Tips

1. **Start with `get_index_status`** - Always check if your indexes are healthy before searching
2. **Use semantic queries** - Be descriptive in your search queries
3. **Combine tools** - Use `search_codebase` to find files, then `get_file_context` for details
4. **Leverage impact analysis** - Before refactoring, use `impact_analysis` to understand dependencies
5. **Cache wisely** - Use `session_clear` when you want fresh results

## More Information

- [MCP Integration Guide](docs/integrations/mcp-server.md)
- [Qoder Setup Guide](docs/mcp/setup-guide/qoder/)
- [Performance Optimization](docs/performance/MCP_PERFORMANCE_OPTIMIZATION.md)
