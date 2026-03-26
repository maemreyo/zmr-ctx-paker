#!/usr/bin/env python3
"""
MCP Stress Test Script
Tests all MCP tools with various inputs including edge cases.
"""

import json
import subprocess
import time
import sys
import os
from datetime import datetime
from pathlib import Path

WORKSPACE = "/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker"
OUTPUT_DIR = Path("test_results/mcp/stress_test")
WSCTX_CMD = "wsctx"

def run_mcp_request(method: str, params: dict = None) -> dict:
    """Execute a raw MCP JSON-RPC request."""
    request = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params or {}
    }
    
    cmd = f'echo \'{json.dumps(request)}\' | {WSCTX_CMD} mcp --workspace {WORKSPACE}'
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {"error": result.stderr, "stdout": result.stdout}
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response", "raw": result.stdout}
            
    except subprocess.TimeoutExpired:
        return {"error": "Request timeout after 30 seconds"}
    except Exception as e:
        return {"error": str(e)}

def test_initialize():
    """Test MCP server initialization."""
    result = run_mcp_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "stress-test", "version": "1.0.0"}
    })
    return {
        "test": "initialize",
        "passed": "result" in result and "serverInfo" in result.get("result", {}),
        "response": result
    }

def test_tools_list():
    """Test listing all available tools."""
    result = run_mcp_request("tools/list")
    tools = result.get("result", {}).get("tools", [])
    return {
        "test": "tools/list",
        "passed": len(tools) > 0,
        "tools_count": len(tools),
        "tools": [t["name"] for t in tools],
        "response": result
    }

def test_get_index_status():
    """Test index status tool."""
    result = run_mcp_request("tools/call", {
        "name": "get_index_status",
        "arguments": {}
    })
    return {
        "test": "get_index_status",
        "passed": "result" in result,
        "response": result
    }

def test_get_domain_map():
    """Test domain map tool."""
    result = run_mcp_request("tools/call", {
        "name": "get_domain_map",
        "arguments": {}
    })
    return {
        "test": "get_domain_map",
        "passed": "result" in result,
        "response": result
    }

def test_search_codebase():
    """Test search_codebase with various queries."""
    test_cases = [
        {"query": "mcp", "limit": 5},
        {"query": "config", "limit": 10},
        {"query": "logger", "limit": 3},
        {"query": "test", "limit": 20},
        {"query": "", "limit": 5},
        {"query": "nonexistent_xyz_123", "limit": 5},
        {"query": "a" * 500, "limit": 5},
    ]
    
    results = []
    for tc in test_cases:
        result = run_mcp_request("tools/call", {
            "name": "search_codebase",
            "arguments": tc
        })
        results.append({
            "input": tc,
            "passed": "result" in result,
            "response": result
        })
    
    return {
        "test": "search_codebase",
        "test_cases": len(test_cases),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results
    }

def test_pack_context():
    """Test pack_context tool with various inputs."""
    test_cases = [
        {"query": "mcp config", "format": "json"},
        {"query": "logger", "format": "xml"},
        {"query": "test", "format": "md"},
        {"query": "search", "format": "yaml"},
        {"query": "test", "format": "zip"},
        {"query": "test", "token_budget": 1000},
        {"query": "test", "agent_phase": "discovery"},
        {"query": "test", "agent_phase": "edit"},
        {"query": "test", "agent_phase": "test"},
    ]
    
    results = []
    for tc in test_cases:
        result = run_mcp_request("tools/call", {
            "name": "pack_context",
            "arguments": tc
        })
        results.append({
            "input": tc,
            "passed": "result" in result,
            "response": result
        })
    
    return {
        "test": "pack_context",
        "test_cases": len(test_cases),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results
    }

def test_get_file_context():
    """Test get_file_context tool with various files."""
    test_cases = [
        {"path": "src/ws_ctx_engine/mcp/config.py"},
        {"path": "src/ws_ctx_engine/mcp/server.py"},
        {"path": "src/ws_ctx_engine/mcp_server.py"},
        {"path": "nonexistent_file.py"},
        {"path": ""},
        {"path": "src/ws_ctx_engine/mcp/config.py", "include_dependencies": False},
        {"path": "src/ws_ctx_engine/mcp/config.py", "include_dependents": False},
        {"path": "src/ws_ctx_engine/mcp/config.py", "include_dependencies": False, "include_dependents": False},
    ]
    
    results = []
    for tc in test_cases:
        result = run_mcp_request("tools/call", {
            "name": "get_file_context",
            "arguments": tc
        })
        results.append({
            "input": tc,
            "passed": "result" in result,
            "response": result
        })
    
    return {
        "test": "get_file_context",
        "test_cases": len(test_cases),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results
    }

def test_session_clear():
    """Test session_clear tool."""
    test_cases = [
        {"session_id": None},
        {"session_id": "test_session_1"},
        {"session_id": ""},
    ]
    
    results = []
    for tc in test_cases:
        args = {k: v for k, v in tc.items() if v is not None}
        result = run_mcp_request("tools/call", {
            "name": "session_clear",
            "arguments": args
        })
        results.append({
            "input": tc,
            "passed": "result" in result,
            "response": result
        })
    
    return {
        "test": "session_clear",
        "test_cases": len(test_cases),
        "passed_count": sum(1 for r in results if r["passed"]),
        "results": results
    }

def test_invalid_method():
    """Test calling non-existent method."""
    result = run_mcp_request("invalid_method_xyz")
    return {
        "test": "invalid_method",
        "test_cases": 1,
        "passed_count": 1 if "error" in result else 0,
        "passed": "error" in result,
        "response": result
    }

def test_invalid_tool():
    """Test calling non-existent tool."""
    result = run_mcp_request("tools/call", {
        "name": "nonexistent_tool_xyz",
        "arguments": {}
    })
    has_error = False
    if "result" in result:
        content = result.get("result", {}).get("content", [])
        if content and isinstance(content[0], dict):
            text = content[0].get("text", "")
            has_error = "error" in text.lower() or "TOOL_NOT_FOUND" in text
    
    return {
        "test": "invalid_tool",
        "test_cases": 1,
        "passed_count": 1 if has_error else 0,
        "passed": has_error,
        "response": result
    }

def test_concurrent_requests():
    """Test concurrent request handling."""
    import concurrent.futures
    
    def make_request(i):
        return run_mcp_request("tools/call", {
            "name": "get_index_status",
            "arguments": {}
        })
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    passed = sum(1 for r in results if "result" in r)
    return {
        "test": "concurrent_requests",
        "test_cases": 5,
        "total": 5,
        "passed": passed,
        "passed_count": passed
    }

def run_all_tests():
    """Run all stress tests."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"stress_test_{timestamp}.json"
    summary_file = OUTPUT_DIR / f"summary_{timestamp}.txt"
    
    print(f"Running MCP Stress Tests...")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Timestamp: {timestamp}")
    print("-" * 50)
    
    tests = [
        ("Initialize", test_initialize),
        ("Tools List", test_tools_list),
        ("Get Index Status", test_get_index_status),
        ("Get Domain Map", test_get_domain_map),
        ("Search Codebase", test_search_codebase),
        ("Pack Context", test_pack_context),
        ("Get File Context", test_get_file_context),
        ("Session Clear", test_session_clear),
        ("Invalid Method", test_invalid_method),
        ("Invalid Tool", test_invalid_tool),
        ("Concurrent Requests", test_concurrent_requests),
    ]
    
    results = []
    start_time = time.time()
    
    for name, test_func in tests:
        print(f"Running: {name}...", end=" ", flush=True)
        try:
            result = test_func()
            results.append(result)
            passed = result.get("passed_count", result.get("passed", False))
            status = "✓" if passed else "✗"
            print(f"{status}")
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({
                "test": name,
                "passed": False,
                "error": str(e)
            })
    
    elapsed = time.time() - start_time
    
    total_passed = sum(
        1 for r in results 
        if r.get("passed_count", r.get("passed", False))
    )
    total_tests = len(results)
    
    summary = f"""
MCP Stress Test Summary
========================
Timestamp: {timestamp}
Total Tests: {total_tests}
Passed: {total_passed}
Failed: {total_tests - total_passed}
Duration: {elapsed:.2f}s

Detailed Results:
-----------------
"""
    for r in results:
        test_name = r.get("test", "unknown")
        if "passed_count" in r:
            status = "✓" if r["passed_count"] == r["test_cases"] else "✗"
            summary += f"{status} {test_name}: {r['passed_count']}/{r['test_cases']} passed\n"
        else:
            status = "✓" if r.get("passed") else "✗"
            summary += f"{status} {test_name}\n"
    
    summary += f"\nOutput saved to: {output_file}"
    
    print("-" * 50)
    print(summary)
    
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "elapsed_seconds": elapsed,
            "results": results
        }, f, indent=2, default=str)
    
    with open(summary_file, "w") as f:
        f.write(summary)
    
    print(f"\nResults saved to: {output_file}")
    print(f"Summary saved to: {summary_file}")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
