#!/usr/bin/env python3
"""
Example script demonstrating how to call ws-ctx-engine MCP tools programmatically.

This script shows how to:
1. Initialize the MCP server
2. List available tools
3. Call individual tools with parameters
4. Process tool responses
"""

import json
import sys
from pathlib import Path

# Add the src directory to the path so we can import ws_ctx_engine
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ws_ctx_engine.mcp.server import MCPStdioServer


def main():
    # Initialize the MCP server with your workspace
    workspace = Path(__file__).parent.resolve()
    print(f"🚀 Initializing MCP server for workspace: {workspace}")
    
    server = MCPStdioServer(workspace=str(workspace))
    
    # 1. List all available tools
    print("\n📋 Listing available tools...")
    tools_response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    })
    
    if tools_response:
        tools = tools_response.get("result", {}).get("tools", [])
        print(f"\n✅ Found {len(tools)} available tools:")
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. **{tool['name']}**")
            print(f"   Description: {tool['description']}")
            if 'inputSchema' in tool:
                required = tool['inputSchema'].get('required', [])
                properties = tool['inputSchema'].get('properties', {})
                if properties:
                    print(f"   Parameters:")
                    for param_name, param_schema in properties.items():
                        param_type = param_schema.get('type', 'any')
                        param_desc = param_schema.get('description', '')
                        is_required = " (required)" if param_name in required else " (optional)"
                        print(f"     - {param_name}: {param_type}{is_required} - {param_desc}")
    
    # 2. Example: Call get_index_status tool
    print("\n\n🔍 Calling get_index_status tool...")
    status_response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_index_status",
            "arguments": {}
        }
    })
    
    if status_response:
        result = status_response.get("result", {})
        structured_content = result.get("structuredContent", {})
        print("\n✅ Index Status:")
        print(json.dumps(structured_content, indent=2))
    
    # 3. Example: Call search_codebase tool
    print("\n\n🔎 Searching codebase for 'authentication'...")
    search_response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_codebase",
            "arguments": {
                "query": "authentication",
                "limit": 5
            }
        }
    })
    
    if search_response:
        result = search_response.get("result", {})
        structured_content = result.get("structuredContent", {})
        print("\n✅ Search Results:")
        
        if "results" in structured_content:
            results = structured_content["results"]
            for i, item in enumerate(results[:5], 1):
                path = item.get("path", "N/A")
                score = item.get("score", 0)
                print(f"\n{i}. {path}")
                print(f"   Score: {score:.4f}")
        
        if "index_health" in structured_content:
            print(f"\n📊 Index Health:")
            health = structured_content["index_health"]
            for key, value in health.items():
                print(f"   {key}: {value}")
    
    # 4. Example: Call graph_search tool
    print("\n\n📊 Analyzing symbols in server.py...")
    graph_response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "graph_search",
            "arguments": {
                "file_id": "src/ws_ctx_engine/mcp/server.py"
            }
        }
    })
    
    if graph_response:
        result = graph_response.get("result", {})
        structured_content = result.get("structuredContent", {})
        print("\n✅ Symbols found in server.py:")
        
        symbols = structured_content.get("symbols", [])
        for i, symbol in enumerate(symbols, 1):
            symbol_name = symbol.get("name", "N/A")
            symbol_kind = symbol.get("kind", "N/A")
            range_info = symbol.get("range", {})
            start_line = range_info.get("start", {}).get("line", "?")
            end_line = range_info.get("end", {}).get("line", "?")
            print(f"\n{i}. {symbol_name} ({symbol_kind})")
            print(f"   Lines: {start_line}-{end_line}")
    
    # 5. Example: Call find_callers tool
    print("\n\n🔗 Finding callers of 'run_mcp_server'...")
    callers_response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "find_callers",
            "arguments": {
                "fn_name": "run_mcp_server"
            }
        }
    })
    
    if callers_response:
        result = callers_response.get("result", {})
        structured_content = result.get("structuredContent", {})
        print("\n✅ Callers of 'run_mcp_server':")
        
        callers = structured_content.get("callers", [])
        if callers:
            for i, caller in enumerate(callers, 1):
                file_path = caller.get("file", "N/A")
                fn_name = caller.get("function", "N/A")
                line = caller.get("line", "?")
                print(f"\n{i}. {fn_name}() in {file_path}:{line}")
        else:
            print("   No callers found")
    
    print("\n\n✨ Example completed!")
    print("\n💡 Available tools you can try:")
    print("   - search_codebase: Semantic search across your codebase")
    print("   - get_file_context: Get file content with dependencies")
    print("   - get_domain_map: View architecture domains")
    print("   - pack_context: Pack context files for LLM consumption")
    print("   - find_callers: Find function callers")
    print("   - impact_analysis: Analyze impact of file changes")
    print("   - graph_search: List symbols in a file")
    print("   - call_chain: Trace call paths between functions")
    print("   - session_clear: Clear session caches")


if __name__ == "__main__":
    main()
