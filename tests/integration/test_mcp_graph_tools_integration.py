"""Integration tests for MCP graph tools with real in-memory GraphStore."""
from __future__ import annotations
import pytest

pycozo = pytest.importorskip("pycozo")

from ws_ctx_engine.graph.cozo_store import GraphStore
from ws_ctx_engine.graph.node_id import normalize_node_id
from ws_ctx_engine.graph.builder import Node, Edge


def _build_test_store() -> GraphStore:
    """Create in-memory GraphStore with known fixture data."""
    store = GraphStore("mem")
    nodes = [
        Node(id="auth.py", kind="file", name="auth.py", file="auth.py", language="python"),
        Node(id="api.py", kind="file", name="api.py", file="api.py", language="python"),
        Node(id="main.py", kind="file", name="main.py", file="main.py", language="python"),
        Node(id="auth.py#authenticate", kind="function", name="authenticate", file="auth.py", language="python"),
        Node(id="auth.py#validate", kind="function", name="validate", file="auth.py", language="python"),
        Node(id="api.py#login", kind="function", name="login", file="api.py", language="python"),
        Node(id="api.py#handle_request", kind="function", name="handle_request", file="api.py", language="python"),
    ]
    edges = [
        Edge(src="auth.py", relation="CONTAINS", dst="auth.py#authenticate"),
        Edge(src="auth.py", relation="CONTAINS", dst="auth.py#validate"),
        Edge(src="api.py", relation="CONTAINS", dst="api.py#login"),
        Edge(src="api.py", relation="CONTAINS", dst="api.py#handle_request"),
        Edge(src="api.py#login", relation="CALLS", dst="auth.py#authenticate"),
        Edge(src="api.py#handle_request", relation="CALLS", dst="auth.py#authenticate"),
        Edge(src="api.py", relation="IMPORTS", dst="auth.py"),
        Edge(src="main.py", relation="IMPORTS", dst="api.py"),
    ]
    store.bulk_upsert(nodes, edges)
    return store


class TestFindCallersIntegration:
    def test_returns_callers_of_authenticate(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _build_test_store()
        result = handle_find_callers(store, {"fn_name": "authenticate"})
        assert result.get("error") is None
        # caller_file holds the calling node ID (e.g. "api.py#login"),
        # so check that at least one caller originates from api.py
        caller_files = {c["caller_file"] for c in result["callers"]}
        assert any("api.py" in cf for cf in caller_files)

    def test_no_callers_returns_empty(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _build_test_store()
        result = handle_find_callers(store, {"fn_name": "nonexistent_function"})
        assert result["callers"] == []


class TestImpactAnalysisIntegration:
    def test_returns_importers_of_auth(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _build_test_store()
        result = handle_impact_analysis(store, {"file_path": "auth.py"})
        assert result.get("error") is None
        assert "api.py" in result["importers"]

    def test_no_importers_returns_empty(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _build_test_store()
        result = handle_impact_analysis(store, {"file_path": "main.py"})
        assert result["importers"] == []


class TestGraphSearchIntegration:
    def test_returns_symbols_in_auth(self):
        from ws_ctx_engine.mcp.graph_tools import handle_graph_search
        store = _build_test_store()
        result = handle_graph_search(store, {"file_id": "auth.py"})
        assert result.get("error") is None
        # GraphStore.contains_of returns {"sym": <node_id>, "kind": <kind>}
        symbol_ids = {s["sym"] for s in result["symbols"]}
        assert "auth.py#authenticate" in symbol_ids
        assert "auth.py#validate" in symbol_ids

    def test_empty_file_returns_empty_symbols(self):
        from ws_ctx_engine.mcp.graph_tools import handle_graph_search
        store = _build_test_store()
        result = handle_graph_search(store, {"file_id": "main.py"})
        assert result["symbols"] == []
