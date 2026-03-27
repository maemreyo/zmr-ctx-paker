#!/usr/bin/env python3
"""
MCP Tool Debug Logger - Detailed Input/Output Logging

This script logs every tool call with clear INPUT/OUTPUT formatting for investigation.
All requests and responses are saved to a log file for analysis.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ws_ctx_engine.mcp.server import MCPStdioServer


class ToolCallLogger:
    """Logs all MCP tool calls with detailed input/output."""
    
    def __init__(self, workspace: str, log_file: str = None):
        self.workspace = Path(workspace).resolve()
        self.server = MCPStdioServer(workspace=str(self.workspace))
        
        # Setup logging
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"mcp_tool_calls_{timestamp}.log"
        
        self.log_file = Path(log_file)
        self.call_count = 0
        
        # Initialize log file
        self._write_header()
    
    def _write_header(self):
        """Write log file header."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("="*100 + "\n")
            f.write("MCP TOOL CALL DEBUG LOG\n")
            f.write("="*100 + "\n")
            f.write(f"Workspace: {self.workspace}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write(f"Python Version: {sys.version}\n")
            f.write("="*100 + "\n\n")
        print(f"📝 Log file created: {self.log_file.absolute()}")
    
    def _log_call(self, tool_name: str, arguments: dict[str, Any], response: dict[str, Any]):
        """Log a single tool call with full details."""
        self.call_count += 1
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            # Call header
            f.write("\n" + "="*100 + "\n")
            f.write(f"CALL #{self.call_count}: {tool_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("="*100 + "\n\n")
            
            # INPUT section
            f.write("📥 INPUT:\n")
            f.write("-"*100 + "\n")
            f.write(json.dumps({
                "jsonrpc": "2.0",
                "id": self.call_count,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }, indent=2, ensure_ascii=False))
            f.write("\n\n")
            
            # Compact view
            f.write("Compact Input:\n")
            f.write(f"  Tool: {tool_name}\n")
            f.write(f"  Arguments: {json.dumps(arguments, ensure_ascii=False)}\n\n")
            
            # OUTPUT section
            f.write("📤 OUTPUT:\n")
            f.write("-"*100 + "\n")
            
            if response is None:
                f.write("Response: None (notification or error)\n")
            else:
                f.write(json.dumps(response, indent=2, ensure_ascii=False, default=str))
            f.write("\n\n")
            
            # Structured output summary
            if response and "result" in response:
                result = response.get("result", {})
                structured = result.get("structuredContent", {})
                
                f.write("Structured Content Summary:\n")
                if isinstance(structured, dict):
                    for key, value in structured.items():
                        if isinstance(value, (str, int, float, bool)):
                            f.write(f"  {key}: {value}\n")
                        elif isinstance(value, list):
                            f.write(f"  {key}: [{len(value)} items]\n")
                        elif isinstance(value, dict):
                            f.write(f"  {key}: {{dict with {len(value)} keys}}\n")
                        else:
                            f.write(f"  {key}: {type(value).__name__}\n")
                else:
                    f.write(f"  Type: {type(structured).__name__}\n")
            
            f.write("\n" + "="*100 + "\n")
        
        # Also print to console
        print(f"\n{'='*80}")
        print(f"CALL #{self.call_count}: {tool_name}")
        print(f"{'='*80}")
        print(f"📥 INPUT:")
        print(f"  Tool: {tool_name}")
        print(f"  Args: {json.dumps(arguments, ensure_ascii=False)}")
        print(f"\n📤 OUTPUT:")
        if response:
            result = response.get("result", {})
            structured = result.get("structuredContent", {})
            if isinstance(structured, dict):
                for key, value in list(structured.items())[:5]:  # Show first 5 keys
                    if isinstance(value, list):
                        print(f"  ✓ {key}: [{len(value)} items]")
                    elif isinstance(value, dict):
                        print(f"  ✓ {key}: {{dict}}")
                    else:
                        value_str = str(value)[:100]
                        print(f"  ✓ {key}: {value_str}...")
            else:
                print(f"  Response type: {type(structured).__name__}")
        else:
            print("  ⚠️  No response")
        print(f"{'='*80}")
    
    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and log the results."""
        request = {
            "jsonrpc": "2.0",
            "id": self.call_count + 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = self.server._handle_request(request)
        self._log_call(tool_name, arguments, response)
        return response
    
    def list_tools(self) -> dict[str, Any]:
        """List available tools and log it."""
        request = {
            "jsonrpc": "2.0",
            "id": self.call_count + 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = self.server._handle_request(request)
        
        # Log it
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*100 + "\n")
            f.write("AVAILABLE TOOLS LIST\n")
            f.write("="*100 + "\n\n")
            f.write("INPUT:\n")
            f.write(json.dumps(request, indent=2) + "\n\n")
            f.write("OUTPUT:\n")
            f.write(json.dumps(response, indent=2, default=str) + "\n")
            f.write("\n" + "="*100 + "\n")
        
        print(f"\n📋 Listed {len(response.get('result', {}).get('tools', []))} tools")
        return response
    
    def get_log_summary(self) -> dict:
        """Get summary of logged calls."""
        return {
            "total_calls": self.call_count,
            "log_file": str(self.log_file.absolute()),
            "workspace": str(self.workspace)
        }


def main():
    """Run comprehensive tool call logging."""
    print("="*80)
    print("MCP TOOL CALL DEBUG LOGGER")
    print("="*80)
    
    # Initialize logger
    workspace = Path.cwd()
    logger = ToolCallLogger(str(workspace))
    
    print(f"\n🎯 Workspace: {workspace}")
    print(f"📊 All calls will be logged to: {logger.log_file}")
    
    # Test 1: List Tools
    print("\n\n" + "="*80)
    print("TEST 1: List Available Tools")
    print("="*80)
    tools_response = logger.list_tools()
    
    if tools_response:
        tools = tools_response.get("result", {}).get("tools", [])
        print(f"\n✅ Found {len(tools)} tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool['name']} - {tool['description'][:60]}...")
    
    # Test 2: Get Index Status
    print("\n\n" + "="*80)
    print("TEST 2: Check Index Status")
    print("="*80)
    status_response = logger.call_tool("get_index_status", {})
    
    # Test 3: Search Codebase
    print("\n\n" + "="*80)
    print("TEST 3: Search Codebase")
    print("="*80)
    search_response = logger.call_tool(
        "search_codebase",
        {
            "query": "MCP server implementation",
            "limit": 5
        }
    )
    
    # Test 4: Graph Search
    print("\n\n" + "="*80)
    print("TEST 4: Graph Search - Symbols in File")
    print("="*80)
    graph_response = logger.call_tool(
        "graph_search",
        {
            "file_id": "src/ws_ctx_engine/mcp/server.py"
        }
    )
    
    # Test 5: Find Callers
    print("\n\n" + "="*80)
    print("TEST 5: Find Function Callers")
    print("="*80)
    callers_response = logger.call_tool(
        "find_callers",
        {
            "fn_name": "call_tool"
        }
    )
    
    # Test 6: Impact Analysis
    print("\n\n" + "="*80)
    print("TEST 6: Impact Analysis")
    print("="*80)
    impact_response = logger.call_tool(
        "impact_analysis",
        {
            "file_path": "src/ws_ctx_engine/mcp/tools.py"
        }
    )
    
    # Final Summary
    print("\n\n" + "="*80)
    print("📊 SESSION SUMMARY")
    print("="*80)
    summary = logger.get_log_summary()
    print(f"Total tool calls: {summary['total_calls']}")
    print(f"Log file: {summary['log_file']}")
    print(f"Workspace: {summary['workspace']}")
    print("\n💡 View detailed log with:")
    print(f"   cat {summary['log_file']}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
