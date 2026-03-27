#!/usr/bin/env python3
"""
MCP E2E Test for Qoder Integration -- Graph Tools

Tests the ws-ctx-engine MCP server graph tools end-to-end via the MCP stdio protocol,
matching the Qoder integration setup documented in docs/mcp/setup-guide/qoder/.

Usage:
    python3 scripts/mcp/mcp_e2e_qoder.py [--workspace PATH] [--qoder-config PATH] [--verbose]

Requirements:
    - ws-ctx-engine installed: pip install -e ".[dev]"
    - Optional: pycozo for graph tests: pip install "pycozo[embedded]"
    - Optional: wsctx index <workspace> run first for data-dependent tests

Environment:
    WSCTX_WORKSPACE   Override workspace path (default: current repo root)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WORKSPACE = str(Path(__file__).resolve().parents[2])
WSCTX_CMD = "wsctx"
OUTPUT_DIR = Path("test_results/mcp/qoder_e2e")

# Graph tools introduced in Phase B/C — must all appear in tools/list
EXPECTED_GRAPH_TOOLS = {
    "find_callers",
    "impact_analysis",
    "graph_search",
    "call_chain",
    "get_status",
}


# ---------------------------------------------------------------------------
# Persistent MCP Session (mirrors mcp_comprehensive_test.py)
# ---------------------------------------------------------------------------


class PersistentMCPSession:
    """Keep a single ``wsctx mcp`` process alive across multiple requests.

    Usage::

        with PersistentMCPSession(workspace) as session:
            result, ms = session.call("get_status", {})
    """

    COLD_START_TIMEOUT = 60  # seconds

    def __init__(self, workspace: str, cmd: str = WSCTX_CMD) -> None:
        self._workspace = workspace
        self._cmd = cmd
        self._proc: subprocess.Popen | None = None
        self._req_id = 0

    def __enter__(self) -> PersistentMCPSession:
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
        # MCP handshake -- fast, no model load needed
        self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "qoder-e2e-test", "version": "1.0"},
            },
            timeout=10,
        )
        return self

    def __exit__(self, *_: Any) -> None:
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()

    def call(self, tool: str, arguments: dict, timeout: float | None = None) -> tuple[dict, float]:
        """Call a tool and return ``(response_dict, elapsed_ms)``."""
        effective_timeout = timeout or self.COLD_START_TIMEOUT
        return self._send_request(
            "tools/call",
            {"name": tool, "arguments": arguments},
            timeout=effective_timeout,
        )

    def list_tools(self, timeout: float = 15.0) -> tuple[dict, float]:
        """Send tools/list and return ``(response_dict, elapsed_ms)``."""
        return self._send_request("tools/list", {}, timeout=timeout)

    def _send_request(self, method: str, params: dict, timeout: float) -> tuple[dict, float]:
        self._req_id += 1
        req = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": self._req_id,
                    "method": method,
                    "params": params,
                }
            )
            + "\n"
        )

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
            return {"error": "invalid json", "raw": str(raw)[:200]}, elapsed_ms


# ---------------------------------------------------------------------------
# TestResult
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    test_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    details: dict[str, Any]
    duration_ms: float
    error_message: str = ""


# ---------------------------------------------------------------------------
# Helper: extract tool result payload from MCP response
# ---------------------------------------------------------------------------


def _extract_payload(response: dict) -> dict | None:
    """Return the dict inside result.content[0].text, or None."""
    result = response.get("result", {})
    content = result.get("content", [])
    if not content or not isinstance(content, list):
        return None
    first = content[0]
    if not isinstance(first, dict):
        return None
    text = first.get("text", "")
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------


def test_tools_list_includes_graph_tools(session: PersistentMCPSession) -> TestResult:
    """tools/list response includes all 5 new graph/status tools."""
    response, ms = session.list_tools()
    tools_raw = response.get("result", {}).get("tools", [])
    found_names = {t.get("name") for t in tools_raw if isinstance(t, dict)}
    missing = EXPECTED_GRAPH_TOOLS - found_names
    passed = len(missing) == 0
    return TestResult(
        test_name="tools_list_includes_graph_tools",
        passed=passed,
        score=1.0 if passed else len(EXPECTED_GRAPH_TOOLS - missing) / len(EXPECTED_GRAPH_TOOLS),
        details={"found": sorted(found_names), "missing": sorted(missing)},
        duration_ms=ms,
        error_message=f"Missing tools: {sorted(missing)}" if missing else "",
    )


def test_get_status_returns_ready_field(session: PersistentMCPSession) -> TestResult:
    """get_status returns a dict with a 'ready' key."""
    response, ms = session.call("get_status", {})
    payload = _extract_payload(response)
    passed = isinstance(payload, dict) and "ready" in payload
    return TestResult(
        test_name="get_status_returns_ready_field",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Missing 'ready' key; got: {payload}",
    )


def test_get_status_structure(session: PersistentMCPSession) -> TestResult:
    """get_status response has graph_store, vector_backend, required_actions, and hint fields."""
    response, ms = session.call("get_status", {})
    payload = _extract_payload(response)
    checks = {
        "has_ready": isinstance(payload, dict) and "ready" in payload,
        "has_graph_store": isinstance(payload, dict) and "graph_store" in payload,
        "has_vector_backend": isinstance(payload, dict) and "vector_backend" in payload,
        "has_index_exists": isinstance(payload, dict) and "index_exists" in payload,
        "has_last_indexed_at": isinstance(payload, dict) and "last_indexed_at" in payload,
        "has_required_actions": isinstance(payload, dict) and "required_actions" in payload,
        "has_hint": isinstance(payload, dict) and "hint" in payload,
    }
    score = sum(checks.values()) / len(checks)
    passed = all(checks.values())
    return TestResult(
        test_name="get_status_structure",
        passed=passed,
        score=score,
        details={"checks": checks, "payload": payload},
        duration_ms=ms,
        error_message=(
            "" if passed else f"Missing fields: {[k for k, v in checks.items() if not v]}"
        ),
    )


def test_find_callers_invalid_arg(session: PersistentMCPSession) -> TestResult:
    """Empty fn_name returns INVALID_ARGUMENT error."""
    response, ms = session.call("find_callers", {"fn_name": ""})
    payload = _extract_payload(response)
    passed = isinstance(payload, dict) and payload.get("error") == "INVALID_ARGUMENT"
    return TestResult(
        test_name="find_callers_invalid_arg",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Expected INVALID_ARGUMENT; got: {payload}",
    )


def test_find_callers_valid_no_index(session: PersistentMCPSession) -> TestResult:
    """Valid fn_name when no index returns GRAPH_UNAVAILABLE or empty callers list."""
    response, ms = session.call("find_callers", {"fn_name": "some_function"})
    payload = _extract_payload(response)
    # Accept either GRAPH_UNAVAILABLE error or a callers list (possibly empty)
    passed = isinstance(payload, dict) and (
        payload.get("error") in ("GRAPH_UNAVAILABLE", "INDEX_NOT_FOUND") or "callers" in payload
    )
    return TestResult(
        test_name="find_callers_valid_no_index",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Unexpected response: {payload}",
    )


def test_impact_analysis_invalid_arg(session: PersistentMCPSession) -> TestResult:
    """Empty file_path returns INVALID_ARGUMENT."""
    response, ms = session.call("impact_analysis", {"file_path": ""})
    payload = _extract_payload(response)
    passed = isinstance(payload, dict) and payload.get("error") == "INVALID_ARGUMENT"
    return TestResult(
        test_name="impact_analysis_invalid_arg",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Expected INVALID_ARGUMENT; got: {payload}",
    )


def test_impact_analysis_valid_no_index(session: PersistentMCPSession) -> TestResult:
    """Valid file_path returns GRAPH_UNAVAILABLE or empty importers when no index."""
    response, ms = session.call("impact_analysis", {"file_path": "src/some_file.py"})
    payload = _extract_payload(response)
    passed = isinstance(payload, dict) and (
        payload.get("error") in ("GRAPH_UNAVAILABLE", "INDEX_NOT_FOUND") or "importers" in payload
    )
    return TestResult(
        test_name="impact_analysis_valid_no_index",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Unexpected response: {payload}",
    )


def test_graph_search_invalid_arg(session: PersistentMCPSession) -> TestResult:
    """Empty file_id returns INVALID_ARGUMENT."""
    response, ms = session.call("graph_search", {"file_id": ""})
    payload = _extract_payload(response)
    passed = isinstance(payload, dict) and payload.get("error") == "INVALID_ARGUMENT"
    return TestResult(
        test_name="graph_search_invalid_arg",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Expected INVALID_ARGUMENT; got: {payload}",
    )


def test_call_chain_invalid_arg_missing_to(session: PersistentMCPSession) -> TestResult:
    """Missing to_fn returns INVALID_ARGUMENT."""
    response, ms = session.call("call_chain", {"from_fn": "foo"})
    payload = _extract_payload(response)
    # Missing required parameter should give INVALID_ARGUMENT
    passed = isinstance(payload, dict) and payload.get("error") == "INVALID_ARGUMENT"
    return TestResult(
        test_name="call_chain_invalid_arg_missing_to",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if passed else f"Expected INVALID_ARGUMENT; got: {payload}",
    )


def test_call_chain_no_path(session: PersistentMCPSession) -> TestResult:
    """Unrelated functions return empty path list (not NOT_IMPLEMENTED)."""
    response, ms = session.call(
        "call_chain",
        {"from_fn": "totally_nonexistent_fn_abc123", "to_fn": "another_nonexistent_fn_xyz999"},
    )
    payload = _extract_payload(response)
    # Should return a path list (possibly empty) or GRAPH_UNAVAILABLE -- not NOT_IMPLEMENTED
    passed = isinstance(payload, dict) and (
        "path" in payload or payload.get("error") in ("GRAPH_UNAVAILABLE", "INDEX_NOT_FOUND")
    )
    not_implemented = isinstance(payload, dict) and payload.get("error") == "NOT_IMPLEMENTED"
    return TestResult(
        test_name="call_chain_no_path",
        passed=passed and not not_implemented,
        score=1.0 if (passed and not not_implemented) else 0.0,
        details={"payload": payload},
        duration_ms=ms,
        error_message="" if (passed and not not_implemented) else f"Unexpected: {payload}",
    )


# ---------------------------------------------------------------------------
# Index-dependent tests (only run when index exists)
# ---------------------------------------------------------------------------


def _index_exists(workspace: str) -> bool:
    """Return True if the workspace has been indexed (metadata.json present)."""
    metadata = Path(workspace) / ".ws-ctx-engine" / "metadata.json"
    return metadata.exists()


def _graph_available(session: PersistentMCPSession) -> bool:
    """Return True when the graph store is healthy (pycozo installed and indexed)."""
    response, _ = session.call("get_status", {})
    payload = _extract_payload(response)
    if not isinstance(payload, dict):
        return False
    return bool(payload.get("graph_store", {}).get("available", False))


def test_find_callers_with_real_data(session: PersistentMCPSession) -> TestResult:
    """fn_name='_query' returns non-empty callers when graph store is available."""
    if not _graph_available(session):
        return TestResult(
            test_name="find_callers_with_real_data",
            passed=True,
            score=1.0,
            details={"skipped": True, "reason": "Graph store unavailable (pycozo not installed)"},
            duration_ms=0.0,
            error_message="",
        )
    response, ms = session.call("find_callers", {"fn_name": "_query"})
    payload = _extract_payload(response)
    callers = payload.get("callers", []) if isinstance(payload, dict) else []
    passed = isinstance(callers, list) and len(callers) > 0
    return TestResult(
        test_name="find_callers_with_real_data",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"callers_count": len(callers), "sample": callers[:3]},
        duration_ms=ms,
        error_message="" if passed else f"Expected non-empty callers; got: {payload}",
    )


def test_graph_search_with_real_data(session: PersistentMCPSession) -> TestResult:
    """cozo_store.py returns non-empty symbols when graph store is available."""
    if not _graph_available(session):
        return TestResult(
            test_name="graph_search_with_real_data",
            passed=True,
            score=1.0,
            details={"skipped": True, "reason": "Graph store unavailable (pycozo not installed)"},
            duration_ms=0.0,
            error_message="",
        )
    response, ms = session.call(
        "graph_search", {"file_id": "src/ws_ctx_engine/graph/cozo_store.py"}
    )
    payload = _extract_payload(response)
    symbols = payload.get("symbols", []) if isinstance(payload, dict) else []
    sym_names = {s.get("sym", "").split("#")[-1] for s in symbols}
    expected = {"GraphStore", "_query", "callers_of"}
    found = expected & sym_names
    passed = len(found) == len(expected)
    return TestResult(
        test_name="graph_search_with_real_data",
        passed=passed,
        score=1.0 if passed else len(found) / len(expected),
        details={"symbols_count": len(symbols), "expected": list(expected), "found": list(found)},
        duration_ms=ms,
        error_message="" if passed else f"Missing symbols: {expected - sym_names}",
    )


def test_call_chain_real_path(session: PersistentMCPSession) -> TestResult:
    """callers_of→_query returns a non-empty path when graph store is available."""
    if not _graph_available(session):
        return TestResult(
            test_name="call_chain_real_path",
            passed=True,
            score=1.0,
            details={"skipped": True, "reason": "Graph store unavailable (pycozo not installed)"},
            duration_ms=0.0,
            error_message="",
        )
    response, ms = session.call("call_chain", {"from_fn": "callers_of", "to_fn": "_query"})
    payload = _extract_payload(response)
    path = payload.get("path", []) if isinstance(payload, dict) else []
    passed = isinstance(path, list) and len(path) > 0
    return TestResult(
        test_name="call_chain_real_path",
        passed=passed,
        score=1.0 if passed else 0.0,
        details={"path": path, "depth": payload.get("depth") if isinstance(payload, dict) else None},
        duration_ms=ms,
        error_message="" if passed else f"Expected non-empty path; got: {payload}",
    )


# ---------------------------------------------------------------------------
# Qoder config validation
# ---------------------------------------------------------------------------


def validate_qoder_config(config_path: str, workspace: str, verbose: bool = False) -> bool:
    """Load and validate a Qoder mcp.json config.

    Prints pass/fail lines.  Returns True if valid.
    """
    path = Path(config_path)
    if not path.exists():
        print(f"  Qoder config not found: {config_path}")
        return False

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"  Qoder config invalid JSON: {exc}")
        return False

    servers = data.get("mcpServers", {})
    # Find any entry with command "wsctx" or name containing "ws-ctx-engine"
    matching_entry = None
    for name, entry in servers.items():
        if entry.get("command") == "wsctx" or "ws-ctx-engine" in name:
            matching_entry = (name, entry)
            break

    if matching_entry is None:
        print("  Qoder config mismatch: no wsctx / ws-ctx-engine server entry found")
        return False

    entry_name, entry = matching_entry
    cmd = entry.get("command")
    args = entry.get("args", [])

    if cmd != "wsctx":
        print(f"  Qoder config mismatch: command should be 'wsctx', got '{cmd}'")
        return False

    if "mcp" not in args:
        print(f"  Qoder config mismatch: args should contain 'mcp', got {args}")
        return False

    if verbose:
        print(f"  Entry '{entry_name}': command={cmd}, args={args}")

    print(f"  Qoder config valid (entry: '{entry_name}')")
    return True


# ---------------------------------------------------------------------------
# Print results and write JSON report
# ---------------------------------------------------------------------------


def print_results(results: list[TestResult], workspace: str) -> None:
    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    total_ms = sum(r.duration_ms for r in results)
    overall_score = sum(r.score for r in results) / total if total else 0.0

    print()
    print("=" * 70)
    print("TEST COMPLETE -- Qoder E2E Integration")
    print("=" * 70)
    print(f"Workspace: {workspace}")
    print(f"Overall Score: {overall_score * 100:.1f}%")
    print(f"Passed: {passed_count}/{total}")
    print(f"Total duration: {total_ms:.0f}ms")
    print("-" * 70)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.test_name} ({r.score * 100:.0f}%,  {r.duration_ms:.0f}ms)")
        if r.error_message:
            print(f"         {r.error_message}")
    print("=" * 70)


def write_report(results: list[TestResult], workspace: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    overall_score = sum(r.score for r in results) / total if total else 0.0

    report = {
        "timestamp": timestamp,
        "workspace": workspace,
        "summary": {
            "total_tests": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "overall_score": overall_score,
            "pass_rate": passed_count / total if total else 0,
        },
        "results": [asdict(r) for r in results],
    }
    report_path = OUTPUT_DIR / f"report_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return report_path


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_all_tests(
    workspace: str | None = None,
    qoder_config: str | None = None,
    verbose: bool = False,
) -> bool:
    resolved_workspace = workspace or os.environ.get("WSCTX_WORKSPACE", DEFAULT_WORKSPACE)

    print("=" * 70)
    print("MCP E2E Test -- Qoder Integration (Graph Tools)")
    print("=" * 70)
    print(f"Workspace: {resolved_workspace}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Qoder config validation (optional)
    if qoder_config:
        print()
        print("Validating Qoder config...")
        validate_qoder_config(qoder_config, resolved_workspace, verbose=verbose)

    print("-" * 70)

    has_index = _index_exists(resolved_workspace)
    if not has_index:
        print("Note: No index found. Data-dependent tests will be skipped.")
        print("      Run 'wsctx index .' first to enable them.")
    print()

    results: list[TestResult] = []

    # Core tests (no index required)
    core_tests = [
        test_tools_list_includes_graph_tools,
        test_get_status_returns_ready_field,
        test_get_status_structure,
        test_find_callers_invalid_arg,
        test_find_callers_valid_no_index,
        test_impact_analysis_invalid_arg,
        test_impact_analysis_valid_no_index,
        test_graph_search_invalid_arg,
        test_call_chain_invalid_arg_missing_to,
        test_call_chain_no_path,
    ]

    # Index-dependent tests
    index_tests = [
        test_find_callers_with_real_data,
        test_graph_search_with_real_data,
        test_call_chain_real_path,
    ]

    try:
        with PersistentMCPSession(resolved_workspace) as session:
            for test_fn in core_tests:
                label = test_fn.__name__
                print(f"  Running: {label}...", end=" ", flush=True)
                try:
                    result = test_fn(session)
                    results.append(result)
                    status = "PASS" if result.passed else "FAIL"
                    print(f"{status} ({result.score * 100:.0f}%)")
                    if verbose and result.error_message:
                        print(f"           {result.error_message}")
                except Exception as exc:
                    print(f"ERROR: {exc}")
                    results.append(
                        TestResult(
                            test_name=label,
                            passed=False,
                            score=0.0,
                            details={"exception": str(exc)},
                            duration_ms=0.0,
                            error_message=str(exc),
                        )
                    )

            if has_index:
                print()
                print("  [Index-dependent tests]")
                for test_fn in index_tests:
                    label = test_fn.__name__
                    print(f"  Running: {label}...", end=" ", flush=True)
                    try:
                        result = test_fn(session)
                        results.append(result)
                        status = "PASS" if result.passed else "FAIL"
                        print(f"{status} ({result.score * 100:.0f}%)")
                        if verbose and result.error_message:
                            print(f"           {result.error_message}")
                    except Exception as exc:
                        print(f"ERROR: {exc}")
                        results.append(
                            TestResult(
                                test_name=label,
                                passed=False,
                                score=0.0,
                                details={"exception": str(exc)},
                                duration_ms=0.0,
                                error_message=str(exc),
                            )
                        )

    except Exception as exc:
        print(f"\nFATAL: Could not start MCP session: {exc}")
        print("Make sure 'wsctx' is installed and on PATH.")
        return False

    print_results(results, resolved_workspace)

    report_path = write_report(results, resolved_workspace)
    print(f"\nReport: {report_path}")

    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    return passed_count == total


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MCP E2E test for Qoder integration (graph tools).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Path to workspace to test (default: repo root or WSCTX_WORKSPACE env var).",
    )
    parser.add_argument(
        "--qoder-config",
        default=None,
        metavar="PATH",
        help="Path to Qoder mcp.json config to validate.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra detail on failures.",
    )
    args = parser.parse_args()

    success = run_all_tests(
        workspace=args.workspace,
        qoder_config=args.qoder_config,
        verbose=args.verbose,
    )
    sys.exit(0 if success else 1)
