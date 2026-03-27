#!/usr/bin/env python3
"""
Minimal example showing MCP tool call JSON formats.

This demonstrates the exact JSON structure for calling ws-ctx-engine MCP tools.
"""

# Example 1: List all available tools
LIST_TOOLS_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}

# Expected response:
# {
#     "jsonrpc": "2.0",
#     "id": 1,
#     "result": {
#         "tools": [
#             {"name": "search_codebase", "description": "...", "inputSchema": {...}},
#             ...
#         ]
#     }
# }


# Example 2: Search codebase semantically
SEARCH_CODEBASE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "search_codebase",
        "arguments": {
            "query": "authentication middleware",
            "limit": 10
        }
    }
}

# Expected response structure:
# {
#     "jsonrpc": "2.0",
#     "id": 2,
#     "result": {
#         "content": [{"type": "text", "text": "..."}],
#         "structuredContent": {
#             "results": [
#                 {"path": "src/auth.py", "score": 0.95},
#                 ...
#             ],
#             "index_health": {...}
#         }
#     }
# }


# Example 3: Get file context with dependencies
GET_FILE_CONTEXT_REQUEST = {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "get_file_context",
        "arguments": {
            "path": "src/ws_ctx_engine/mcp/server.py",
            "include_dependencies": True,
            "include_dependents": False
        }
    }
}


# Example 4: Check index status
GET_INDEX_STATUS_REQUEST = {
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
        "name": "get_index_status",
        "arguments": {}
    }
}


# Example 5: Find callers of a function
FIND_CALLERS_REQUEST = {
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
        "name": "find_callers",
        "arguments": {
            "fn_name": "run_mcp_server"
        }
    }
}


# Example 6: Analyze impact of file changes
IMPACT_ANALYSIS_REQUEST = {
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
        "name": "impact_analysis",
        "arguments": {
            "file_path": "src/ws_ctx_engine/mcp/tools.py"
        }
    }
}


# Example 7: List symbols in a file
GRAPH_SEARCH_REQUEST = {
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
        "name": "graph_search",
        "arguments": {
            "file_id": "src/ws_ctx_engine/mcp/server.py"
        }
    }
}


# Example 8: Pack context for LLM consumption
PACK_CONTEXT_REQUEST = {
    "jsonrpc": "2.0",
    "id": 8,
    "method": "tools/call",
    "params": {
        "name": "pack_context",
        "arguments": {
            "query": "MCP server implementation",
            "format": "xml",
            "token_budget": 50000,
            "agent_phase": "edit"
        }
    }
}


# Example 9: Trace call chain between functions
CALL_CHAIN_REQUEST = {
    "jsonrpc": "2.0",
    "id": 9,
    "method": "tools/call",
    "params": {
        "name": "call_chain",
        "arguments": {
            "from_fn": "main",
            "to_fn": "authenticate",
            "max_depth": 5
        }
    }
}


# Example 10: Clear session cache
SESSION_CLEAR_REQUEST = {
    "jsonrpc": "2.0",
    "id": 10,
    "method": "tools/call",
    "params": {
        "name": "session_clear",
        "arguments": {}
    }
}


def print_example(name, request):
    """Print a formatted example."""
    import json
    
    print(f"\n{'='*60}")
    print(f"Example: {name}")
    print('='*60)
    print(json.dumps(request, indent=2))


if __name__ == "__main__":
    print("\n📚 MCP Tool Call Examples")
    print("These are the exact JSON structures you'd send to the MCP server")
    
    print_example("List Available Tools", LIST_TOOLS_REQUEST)
    print_example("Search Codebase", SEARCH_CODEBASE_REQUEST)
    print_example("Get File Context", GET_FILE_CONTEXT_REQUEST)
    print_example("Check Index Status", GET_INDEX_STATUS_REQUEST)
    print_example("Find Function Callers", FIND_CALLERS_REQUEST)
    print_example("Analyze Change Impact", IMPACT_ANALYSIS_REQUEST)
    print_example("Discover File Symbols", GRAPH_SEARCH_REQUEST)
    print_example("Pack Context for LLM", PACK_CONTEXT_REQUEST)
    print_example("Trace Call Chain", CALL_CHAIN_REQUEST)
    print_example("Clear Session Cache", SESSION_CLEAR_REQUEST)
    
    print(f"\n{'='*60}")
    print("💡 Tip: Use these JSON structures when calling the MCP server")
    print("   via stdio, or use the Python example in mcp_tool_example.py")
    print('='*60 + '\n')
