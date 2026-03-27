# MCP Tool Calling Guide - Quick Start

This guide shows you how to call tools within the ws-ctx-engine MCP server, with working examples using Python 3.13.5.

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
# Using uv (recommended)
uv run python3.13 examples/mcp_tool_example.py

# Or install the package first
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Step 2: Run Examples

Three progressively detailed examples are provided:

1. **JSON Structure Examples** - See exact JSON formats
   ```bash
   uv run python3.13 examples/json_rpc_examples.py
   ```

2. **Practical Tool Calls** - Real tool execution with results
   ```bash
   uv run python3.13 examples/practical_tool_calls.py
   ```

3. **Full Demo** - Complete walkthrough
   ```bash
   uv run python3.13 examples/mcp_tool_example.py
   ```

## 📚 Available Tools (12 Total)

| # | Tool Name | Purpose |
|---|-----------|---------|
| 1 | `search_codebase` | Semantic search across your codebase |
| 2 | `get_file_context` | Get file content with dependencies |
| 3 | `get_domain_map` | View architecture domain mapping |
| 4 | `get_index_status` | Check index health and freshness |
| 5 | `index_status` | Alias for get_index_status |
| 6 | `pack_context` | Package context for LLMs (XML/JSON/YAML/MD/ZIP) |
| 7 | `session_clear` | Clear session deduplication caches |
| 8 | `find_callers` | Find all callers of a function |
| 9 | `impact_analysis` | Analyze impact of file changes |
| 10 | `graph_search` | List symbols in a file |
| 11 | `call_chain` | Trace call paths between functions |
| 12 | `get_status` | Comprehensive server status |

## 🔧 How to Call Tools

### Method 1: Python API (Recommended for Development)

```python
from ws_ctx_engine.mcp.server import MCPStdioServer

# Initialize server
server = MCPStdioServer(workspace="/path/to/your/project")

# Call a tool
response = server._handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "search_codebase",
        "arguments": {
            "query": "authentication logic",
            "limit": 10
        }
    }
})

# Process response
result = response["result"]["structuredContent"]
print(result)
```

### Method 2: JSON-RPC over STDIO (Production Use)

Send JSON lines to the MCP server's stdin:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_codebase","arguments":{"query":"auth","limit":5}}}' | \
python -m ws_ctx_engine.mcp.server --workspace /path/to/project
```

### Method 3: Via MCP Client (IDE Integration)

Configure your IDE (Qoder, Windsurf, Cursor) to use ws-ctx-engine as an MCP server, then use tools directly from the IDE.

## 📋 Example JSON-RPC Requests

### List All Tools
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

### Search Codebase
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_codebase",
    "arguments": {
      "query": "MCP server implementation",
      "limit": 10
    }
  }
}
```

### Get File Context
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_file_context",
    "arguments": {
      "path": "src/ws_ctx_engine/mcp/server.py",
      "include_dependencies": true,
      "include_dependents": true
    }
  }
}
```

### Check Index Status
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "get_index_status",
    "arguments": {}
  }
}
```

## 🎯 Common Use Cases

### 1. Finding Where a Function is Used
```python
response = server._handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "find_callers",
        "arguments": {"fn_name": "authenticate"}
    }
})
```

### 2. Understanding Impact Before Refactoring
```python
response = server._handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "impact_analysis",
        "arguments": {"file_path": "src/auth.py"}
    }
})
```

### 3. Discovering API Endpoints
```python
response = server._handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "search_codebase",
        "arguments": {
            "query": "REST API endpoint route handler",
            "limit": 20
        }
    }
})
```

### 4. Preparing Context for LLM
```python
response = server._handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "pack_context",
        "arguments": {
            "query": "user authentication flow",
            "format": "xml",
            "token_budget": 50000
        }
    }
})
```

## ⚠️ Important Notes

1. **Index Required**: Most tools require indexes to be built first
   ```bash
   ws-ctx-engine index .
   ```

2. **Workspace Boundaries**: Tools only access files within the workspace directory

3. **Rate Limiting**: Tools may have rate limits configured in `.ws-ctx-engine.yaml`

4. **Python Version**: Examples tested with Python 3.13.5

## 📖 Additional Resources

- **Full Documentation**: [`examples/MCP_TOOL_EXAMPLES.md`](MCP_TOOL_EXAMPLES.md)
- **JSON Examples**: [`examples/json_rpc_examples.py`](json_rpc_examples.py)
- **Practical Examples**: [`examples/practical_tool_calls.py`](practical_tool_calls.py)
- **Full Demo**: [`examples/mcp_tool_example.py`](mcp_tool_example.py)
- **MCP Server Guide**: [`docs/integrations/mcp-server.md`](../docs/integrations/mcp-server.md)
- **Qoder Setup**: [`docs/mcp/setup-guide/qoder/`](../docs/mcp/setup-guide/qoder/)

## 🆘 Troubleshooting

### "INDEX_NOT_FOUND" Error
```bash
# Build the indexes
ws-ctx-engine index .
```

### "No module named 'faiss'" Warning
```bash
# Install optional dependencies
pip install ws-ctx-engine[all]
```

### "GraphStore init failed" Warning
```bash
# Install graph database support
pip install pycozo
```

### Import Errors
Make sure you're using the virtual environment:
```bash
source .venv/bin/activate
# or use uv
uv run python3.13 your_script.py
```

## ✨ Next Steps

1. Try the examples in order
2. Build indexes for your own project
3. Integrate with your IDE via MCP
4. Explore advanced features like `call_chain` and `impact_analysis`

Happy coding! 🚀
