#!/usr/bin/env python3
"""
Practical example: Actually calling MCP tools and displaying results.

This script demonstrates real tool execution with the current workspace.
"""

import sys
from pathlib import Path

# Use the installed package
from ws_ctx_engine.mcp.server import MCPStdioServer


def main():
    workspace = Path.cwd()
    print(f"🚀 Workspace: {workspace}\n")
    
    # Initialize server
    server = MCPStdioServer(workspace=str(workspace))
    
    # Example 1: List all available tools
    print("="*60)
    print("📋 EXAMPLE 1: List Available Tools")
    print("="*60)
    
    response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    })
    
    if response and "result" in response:
        tools = response["result"].get("tools", [])
        print(f"\n✅ Found {len(tools)} tools:\n")
        for i, tool in enumerate(tools, 1):
            print(f"{i:2}. {tool['name']}")
            print(f"    {tool['description'][:80]}...")
    
    # Example 2: Get index status (quick check)
    print("\n\n" + "="*60)
    print("📊 EXAMPLE 2: Check Index Status")
    print("="*60)
    
    response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_index_status",
            "arguments": {}
        }
    })
    
    if response:
        result = response.get("result", {}).get("structuredContent", {})
        if "error" in result:
            print(f"\n⚠️  {result['error']}: {result['message']}")
            print("\n💡 To fix this, run: ws-ctx-engine index .")
        else:
            print(f"\n✅ Index is healthy!")
            print(f"   Files indexed: {result.get('file_count', 'N/A')}")
            print(f"   Last updated: {result.get('last_updated', 'N/A')}")
    
    # Example 3: Search for something specific
    print("\n\n" + "="*60)
    print("🔍 EXAMPLE 3: Search Codebase")
    print("="*60)
    
    response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_codebase",
            "arguments": {
                "query": "MCP server implementation",
                "limit": 5
            }
        }
    })
    
    if response:
        result = response.get("result", {}).get("structuredContent", {})
        results = result.get("results", [])
        
        if results:
            print(f"\n✅ Found {len(results)} relevant files:\n")
            for i, item in enumerate(results[:5], 1):
                path = item.get("path", "N/A")
                score = item.get("score", 0)
                print(f"{i}. {path}")
                print(f"   Score: {score:.4f}")
        else:
            print("\n⚠️  No results found (index may need to be built)")
    
    # Example 4: Analyze a specific file
    print("\n\n" + "="*60)
    print("🔬 EXAMPLE 4: Graph Search - List Symbols in File")
    print("="*60)
    
    response = server._handle_request({
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
    
    if response:
        result = response.get("result", {}).get("structuredContent", {})
        symbols = result.get("symbols", [])
        
        if symbols:
            print(f"\n✅ Found {len(symbols)} symbols in server.py:\n")
            for i, symbol in enumerate(symbols[:10], 1):
                name = symbol.get("name", "N/A")
                kind = symbol.get("kind", "N/A")
                range_info = symbol.get("range", {})
                start_line = range_info.get("start", {}).get("line", "?")
                print(f"{i}. {name} ({kind}) - line {start_line}")
        else:
            print("\n⚠️  No symbols found (graph may not be built)")
    
    # Example 5: Find callers
    print("\n\n" + "="*60)
    print("🔗 EXAMPLE 5: Find Callers of a Function")
    print("="*60)
    
    response = server._handle_request({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "find_callers",
            "arguments": {
                "fn_name": "call_tool"
            }
        }
    })
    
    if response:
        result = response.get("result", {}).get("structuredContent", {})
        callers = result.get("callers", [])
        
        if callers:
            print(f"\n✅ Found {len(callers)} callers of 'call_tool':\n")
            for i, caller in enumerate(callers[:5], 1):
                file_path = caller.get("file", "N/A")
                fn_name = caller.get("function", "N/A")
                line = caller.get("line", "?")
                print(f"{i}. {fn_name}() in {file_path}:{line}")
        else:
            print("\n⚠️  No callers found")
    
    # Summary
    print("\n\n" + "="*60)
    print("✨ SUMMARY")
    print("="*60)
    print("\nYou've seen examples of:")
    print("  ✓ Listing available tools")
    print("  ✓ Checking index health")
    print("  ✓ Searching the codebase semantically")
    print("  ✓ Discovering symbols in files")
    print("  ✓ Finding function callers")
    print("\n💡 For more examples, see:")
    print("   - examples/json_rpc_examples.py (JSON structures)")
    print("   - examples/MCP_TOOL_EXAMPLES.md (documentation)")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
