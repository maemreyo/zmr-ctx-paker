#!/usr/bin/env python3
"""
Demo script showing how to handle missing dependencies gracefully.

This demonstrates the recommended workflow when tools fail due to missing deps.
"""

import json
import sys
from pathlib import Path

from ws_ctx_engine.mcp.server import MCPStdioServer
from ws_ctx_engine.mcp.tools import MCPToolService


class GracefulToolHandler:
    """Xử lý tool calls một cách graceful khi thiếu dependencies."""
    
    def __init__(self, workspace: str):
        self.workspace = Path(workspace).resolve()
        self.server = MCPStdioServer(workspace=str(self.workspace))
        self.known_issues = {}
    
    def check_tool_health(self, tool_name: str) -> dict:
        """Kiểm tra xem tool có hoạt động không trước khi gọi."""
        
        # Test bằng cách gọi get_index_status trước
        response = self.server._handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_index_status",
                "arguments": {}
            }
        })
        
        if not response:
            return {
                "healthy": False,
                "reason": "No response from server",
                "suggestion": "Check if MCP server is running"
            }
        
        result = response.get("result", {}).get("structuredContent", {})
        
        # Check for errors
        if "error" in result:
            error_msg = result.get("message", "").lower()
            
            if "faiss" in error_msg or "vector" in error_msg:
                return {
                    "healthy": False,
                    "reason": "Missing FAISS dependency",
                    "missing_package": "faiss-cpu",
                    "install_cmd": "uv add faiss-cpu",
                    "affected_tools": ["search_codebase"],
                    "suggestion": "Install vector search backend"
                }
            
            if "pycozo" in error_msg or "graph" in error_msg:
                return {
                    "healthy": False,
                    "reason": "Missing PyCozo dependency",
                    "missing_package": "pycozo[embedded]",
                    "install_cmd": "uv add 'pycozo[embedded]'",
                    "affected_tools": ["find_callers", "impact_analysis", "graph_search", "call_chain"],
                    "suggestion": "Install graph database backend"
                }
        
        return {"healthy": True}
    
    def safe_call_tool(self, tool_name: str, arguments: dict, auto_fix: bool = True) -> dict:
        """Gọi tool với kiểm tra health và tự động đề xuất sửa."""
        
        print(f"\n{'='*80}")
        print(f"🔧 Gọi tool: {tool_name}")
        print(f"{'='*80}")
        
        # Check health first
        health = self.check_tool_health(tool_name)
        
        if not health["healthy"]:
            print(f"❌ Tool không hoạt động: {health['reason']}")
            
            if "missing_package" in health:
                print(f"\n💡 Nguyên nhân:")
                print(f"   Thiếu package: {health['missing_package']}")
                print(f"   Tools bị ảnh hưởng: {', '.join(health['affected_tools'])}")
                
                if auto_fix:
                    print(f"\n🔧 Đề xuất sửa:")
                    print(f"   {health['install_cmd']}")
                    
                    # Offer to fix
                    if tool_name in health["affected_tools"]:
                        print(f"\n⚠️  Tool bạn muốn gọi ({tool_name}) bị ảnh hưởng!")
                        return {
                            "error": "DEPENDENCY_MISSING",
                            "message": health["reason"],
                            "fix": {
                                "package": health["missing_package"],
                                "command": health["install_cmd"],
                                "tier": health.get("tier", "unknown")
                            }
                        }
            
            return {
                "error": "TOOL_UNAVAILABLE",
                "message": health["reason"],
                "suggestion": health.get("suggestion")
            }
        
        # If healthy, proceed with call
        print(f"✅ Tool hoạt động bình thường")
        
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = self.server._handle_request(request)
        
        # Check if response indicates missing dependency
        if response and "result" in response:
            structured = response["result"].get("structuredContent", {})
            
            if "error" in structured:
                error_msg = structured.get("message", "").lower()
                
                # Detect specific missing dependencies
                if "faiss" in error_msg:
                    print("\n❌ Lỗi: Thiếu FAISS")
                    print("💡 Chạy: uv add faiss-cpu")
                elif "pycozo" in error_msg:
                    print("\n❌ Lỗi: Thiếu PyCozo")
                    print("💡 Chạy: uv add 'pycozo[embedded]'")
        
        return response
    
    def interactive_fix_wizard(self):
        """Interactive wizard to help fix all missing dependencies."""
        print("\n" + "="*80)
        print("🎯 WIZARD: Tự động phát hiện và sửa thiếu dependencies")
        print("="*80)
        
        # Step 1: Diagnose
        print("\n📋 Bước 1/3: Đang chẩn đoán...")
        health = self.check_tool_health("search_codebase")
        
        if health["healthy"]:
            print("✅ Tất cả dependencies đã được cài!")
            return
        
        # Step 2: Show issues
        print("\n📋 Bước 2/3: Vấn đề phát hiện")
        print(f"   ❌ {health['reason']}")
        print(f"   📦 Package thiếu: {health['missing_package']}")
        print(f"   🔧 Tools bị ảnh hưởng:")
        for tool in health["affected_tools"]:
            print(f"      • {tool}")
        
        # Step 3: Offer fix
        print("\n📋 Bước 3/3: Đề xuất sửa")
        print("\n🎯 Tùy chọn 1 (Recommended - Cài tất cả):")
        print("   uv add ws-ctx-engine[all]")
        print("   → Cài đầy đủ tất cả dependencies")
        
        print("\n🎯 Tùy chọn 2 (Cài riêng lẻ):")
        print(f"   {health['install_cmd']}")
        print(f"   → Chỉ cài package thiếu")
        
        print("\n⚡ Tùy chọn 3 (Quick fix):")
        print("   pip install 'ws-ctx-engine[all]'")
        print("   → Dùng pip thay vì uv")
        
        # Ask user
        print("\n" + "="*80)
        choice = input("\nChọn phương án (1/2/3/q để thoát): ").strip()
        
        if choice == '1':
            print("\n🚀 Đang cài đặt: ws-ctx-engine[all]...")
            print("   (Đây là lệnh giả định - bạn cần chạy thủ công)")
            print(f"\n💡 Chạy lệnh này trong terminal:")
            print(f"   uv add ws-ctx-engine[all]")
        elif choice == '2':
            print(f"\n🚀 Đang cài đặt: {health['missing_package']}...")
            print(f"\n💡 Chạy lệnh này trong terminal:")
            print(f"   {health['install_cmd']}")
        elif choice == '3':
            print("\n🚀 Đang cài đặt với pip...")
            print(f"\n💡 Chạy lệnh này trong terminal:")
            print(f"   pip install 'ws-ctx-engine[all]'")
        else:
            print("\n👋 Thoát. Để sửa sau, chạy:")
            print(f"   {health['install_cmd']}")


def demo_workflow():
    """Demo workflow xử lý thiếu dependencies."""
    print("="*80)
    print("DEMO: XỬ LÝ THIẾU DEPENDENCIES")
    print("="*80)
    
    handler = GracefulToolHandler(".")
    
    # Scenario 1: Try to use search_codebase without FAISS
    print("\n\n📝 KỊCH BẢN 1: Search codebase khi thiếu FAISS")
    print("-"*80)
    
    result = handler.safe_call_tool(
        "search_codebase",
        {"query": "test", "limit": 5},
        auto_fix=True
    )
    
    if "error" in result and "fix" in result:
        print("\n✅ Phát hiện lỗi! Đề xuất:")
        print(f"   Package: {result['fix']['package']}")
        print(f"   Command: {result['fix']['command']}")
    
    # Scenario 2: Try graph operations without PyCozo
    print("\n\n📝 KỊCH BẢN 2: Graph analysis khi thiếu PyCozo")
    print("-"*80)
    
    result = handler.safe_call_tool(
        "graph_search",
        {"file_id": "src/test.py"},
        auto_fix=True
    )
    
    if "error" in result and "fix" in result:
        print("\n✅ Phát hiện lỗi! Đề xuất:")
        print(f"   Package: {result['fix']['package']}")
        print(f"   Command: {result['fix']['command']}")
    
    # Scenario 3: Interactive wizard
    print("\n\n📝 KỊCH BẢN 3: Interactive Wizard")
    print("-"*80)
    
    handler.interactive_fix_wizard()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_workflow()
    else:
        # Normal usage
        handler = GracefulToolHandler(".")
        
        print("Usage:")
        print("  --demo : Run demo workflow")
        print("  --check : Check tool health")
        print("  --fix : Interactive fix wizard")
        print()
        
        if len(sys.argv) > 1 and sys.argv[1] == "--check":
            health = handler.check_tool_health("search_codebase")
            print(json.dumps(health, indent=2))
        elif len(sys.argv) > 1 and sys.argv[1] == "--fix":
            handler.interactive_fix_wizard()
        else:
            print("Run with --demo to see example workflows")
