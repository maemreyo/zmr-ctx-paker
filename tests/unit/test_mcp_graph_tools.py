"""Unit tests for MCP graph tool handlers."""
from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest


def _make_store(
    *,
    healthy: bool = True,
    callers: list[dict] | None = None,
    importers: list[str] | None = None,
    contains: list[dict] | None = None,
) -> MagicMock:
    store = MagicMock()
    store.is_healthy = healthy
    store.callers_of.return_value = callers or []
    store.impact_of.return_value = importers or []
    store.contains_of.return_value = contains or []
    return store


class TestFindCallers:
    def test_returns_callers(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _make_store(callers=[{"caller_file": "api.py", "caller_name": "login"}])
        result = handle_find_callers(store, {"fn_name": "authenticate"})
        assert result["callers"] == [{"caller_file": "api.py", "caller_name": "login"}]
        assert result.get("error") is None

    def test_empty_fn_name_returns_invalid_argument(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _make_store()
        result = handle_find_callers(store, {"fn_name": ""})
        assert result["error"] == "INVALID_ARGUMENT"

    def test_missing_fn_name_returns_invalid_argument(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _make_store()
        result = handle_find_callers(store, {})
        assert result["error"] == "INVALID_ARGUMENT"

    def test_unhealthy_store_returns_graph_unavailable(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _make_store(healthy=False)
        result = handle_find_callers(store, {"fn_name": "authenticate"})
        assert result["error"] == "GRAPH_UNAVAILABLE"
        assert "wsctx index" in result["message"]

    def test_none_store_returns_graph_unavailable(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        result = handle_find_callers(None, {"fn_name": "authenticate"})
        assert result["error"] == "GRAPH_UNAVAILABLE"

    def test_no_callers_returns_empty_list(self):
        from ws_ctx_engine.mcp.graph_tools import handle_find_callers
        store = _make_store(callers=[])
        result = handle_find_callers(store, {"fn_name": "authenticate"})
        assert result["callers"] == []
        assert result.get("error") is None


class TestImpactAnalysis:
    def test_returns_importers(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _make_store(importers=["api.py", "main.py"])
        result = handle_impact_analysis(store, {"file_path": "auth.py"})
        assert result["importers"] == ["api.py", "main.py"]
        assert result.get("error") is None

    def test_empty_file_path_returns_invalid_argument(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _make_store()
        result = handle_impact_analysis(store, {"file_path": ""})
        assert result["error"] == "INVALID_ARGUMENT"

    def test_missing_file_path_returns_invalid_argument(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _make_store()
        result = handle_impact_analysis(store, {})
        assert result["error"] == "INVALID_ARGUMENT"

    def test_unhealthy_store_returns_graph_unavailable(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _make_store(healthy=False)
        result = handle_impact_analysis(store, {"file_path": "auth.py"})
        assert result["error"] == "GRAPH_UNAVAILABLE"

    def test_no_importers_returns_empty_list(self):
        from ws_ctx_engine.mcp.graph_tools import handle_impact_analysis
        store = _make_store(importers=[])
        result = handle_impact_analysis(store, {"file_path": "auth.py"})
        assert result["importers"] == []


class TestGraphSearch:
    def test_returns_symbols(self):
        from ws_ctx_engine.mcp.graph_tools import handle_graph_search
        store = _make_store(contains=[{"id": "auth#login", "name": "login", "kind": "function"}])
        result = handle_graph_search(store, {"file_id": "auth.py"})
        assert len(result["symbols"]) == 1
        assert result["symbols"][0]["name"] == "login"

    def test_empty_file_id_returns_invalid_argument(self):
        from ws_ctx_engine.mcp.graph_tools import handle_graph_search
        store = _make_store()
        result = handle_graph_search(store, {"file_id": ""})
        assert result["error"] == "INVALID_ARGUMENT"

    def test_none_store_returns_graph_unavailable(self):
        from ws_ctx_engine.mcp.graph_tools import handle_graph_search
        result = handle_graph_search(None, {"file_id": "auth.py"})
        assert result["error"] == "GRAPH_UNAVAILABLE"


class TestCallChain:
    def test_no_store_returns_graph_unavailable(self):
        from ws_ctx_engine.mcp.graph_tools import handle_call_chain
        result = handle_call_chain(None, {"from_fn": "main", "to_fn": "authenticate"})
        assert result["error"] == "GRAPH_UNAVAILABLE"

    def test_missing_args_returns_invalid_argument(self):
        from ws_ctx_engine.mcp.graph_tools import handle_call_chain
        result = handle_call_chain(None, {"from_fn": "main"})
        assert result["error"] == "INVALID_ARGUMENT"


class TestMCPToolServiceSchemas:
    def test_graph_tools_in_schemas(self):
        """All 4 graph tools must appear in tool_schemas()."""
        from ws_ctx_engine.mcp.tools import MCPToolService
        svc = MCPToolService.__new__(MCPToolService)
        schemas = svc.tool_schemas()
        names = {s["name"] for s in schemas}
        assert "find_callers" in names
        assert "impact_analysis" in names
        assert "graph_search" in names
        assert "call_chain" in names

    def test_graph_tools_have_descriptions(self):
        from ws_ctx_engine.mcp.tools import MCPToolService
        svc = MCPToolService.__new__(MCPToolService)
        schemas = svc.tool_schemas()
        graph_schemas = {s["name"]: s for s in schemas if s["name"] in ("find_callers", "impact_analysis", "graph_search", "call_chain")}
        for name, schema in graph_schemas.items():
            assert len(schema.get("description", "")) > 20, f"{name} needs a longer description"
            assert "Use when" in schema.get("description", ""), f"{name} description should include 'Use when'"


class TestRateLimits:
    def test_graph_tools_have_rate_limits(self):
        from ws_ctx_engine.mcp.config import DEFAULT_RATE_LIMITS
        assert "find_callers" in DEFAULT_RATE_LIMITS
        assert "impact_analysis" in DEFAULT_RATE_LIMITS
        assert "graph_search" in DEFAULT_RATE_LIMITS
        assert "call_chain" in DEFAULT_RATE_LIMITS
        assert DEFAULT_RATE_LIMITS["call_chain"] <= DEFAULT_RATE_LIMITS["find_callers"]
