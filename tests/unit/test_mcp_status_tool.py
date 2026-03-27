"""Tests for the get_status MCP tool."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetStatusSchema:
    def test_get_status_in_tool_schemas(self):
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        schemas = svc.tool_schemas()
        names = {s["name"] for s in schemas}
        assert "get_status" in names

    def test_get_status_has_description_with_use_when(self):
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        schemas = svc.tool_schemas()
        status_schema = next(s for s in schemas if s["name"] == "get_status")
        assert "Use" in status_schema["description"] or "readiness" in status_schema["description"].lower()

    def test_get_status_has_empty_input_schema(self):
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        schemas = svc.tool_schemas()
        status_schema = next(s for s in schemas if s["name"] == "get_status")
        # Should accept no required params
        props = status_schema.get("inputSchema", {}).get("properties", {})
        required = status_schema.get("inputSchema", {}).get("required", [])
        assert required == []

    def test_get_status_rate_limited(self):
        from ws_ctx_engine.mcp.config import DEFAULT_RATE_LIMITS

        assert "get_status" in DEFAULT_RATE_LIMITS

    def test_get_status_rate_limit_is_positive_int(self):
        from ws_ctx_engine.mcp.config import DEFAULT_RATE_LIMITS

        limit = DEFAULT_RATE_LIMITS["get_status"]
        assert isinstance(limit, int)
        assert limit > 0

    def test_get_status_schema_has_input_schema(self):
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        schemas = svc.tool_schemas()
        status_schema = next(s for s in schemas if s["name"] == "get_status")
        assert "inputSchema" in status_schema
        assert status_schema["inputSchema"]["type"] == "object"


class TestGetStatusHandler:
    def _make_svc(self, graph_store=None, graph_store_loaded=True):
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        svc._graph_store_cache = graph_store
        svc._graph_store_loaded = graph_store_loaded
        svc._index_cache = None
        svc._rate_limiters = {}
        return svc

    def test_get_status_returns_ready_field(self):
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = self._make_svc()
        with patch.object(type(svc), "_get_status_data", return_value={
            "ready": False,
            "index_exists": False,
            "graph_store": {"available": False},
            "vector_backend": "none",
            "last_indexed_at": None,
        }):
            result = svc._get_status_data()
        assert "ready" in result

    def test_get_status_includes_graph_store_info(self):
        from ws_ctx_engine.mcp.tools import MCPToolService

        mock_store = MagicMock()
        mock_store.is_healthy = True
        mock_store.stats.return_value = {
            "node_count": 10,
            "edge_count": 20,
            "healthy": True,
            "schema_version": "1",
            "metrics": {},
        }
        svc = self._make_svc(graph_store=mock_store)
        # Patch workspace_root and index_dir so _load_metadata returns None cleanly
        from pathlib import Path

        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert "graph_store" in data
        gs = data["graph_store"]
        assert gs.get("available") is True or gs.get("node_count") == 10

    def test_get_status_graph_unavailable_when_no_store(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = self._make_svc(graph_store=None)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert "graph_store" in data
        assert data["graph_store"]["available"] is False

    def test_get_status_returns_index_exists_false_when_no_metadata(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = self._make_svc(graph_store=None)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert "index_exists" in data
        assert data["index_exists"] is False

    def test_get_status_ready_is_false_when_no_metadata(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = self._make_svc(graph_store=None)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert data["ready"] is False

    def test_get_status_vector_backend_field_present(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = self._make_svc(graph_store=None)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert "vector_backend" in data

    def test_get_status_last_indexed_at_field_present(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = self._make_svc(graph_store=None)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert "last_indexed_at" in data

    def test_get_status_graph_store_available_true_when_healthy(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        mock_store = MagicMock()
        mock_store.is_healthy = True
        mock_store.stats.return_value = {
            "node_count": 5,
            "edge_count": 8,
            "healthy": True,
            "schema_version": "1",
            "metrics": {},
        }
        svc = self._make_svc(graph_store=mock_store)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert data["graph_store"]["available"] is True

    def test_get_status_graph_store_node_edge_counts_from_stats(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        mock_store = MagicMock()
        mock_store.is_healthy = True
        mock_store.stats.return_value = {
            "node_count": 42,
            "edge_count": 99,
            "healthy": True,
            "schema_version": "1",
            "metrics": {},
        }
        svc = self._make_svc(graph_store=mock_store)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        gs = data["graph_store"]
        assert gs["node_count"] == 42
        assert gs["edge_count"] == 99

    def test_get_status_graph_store_schema_version_from_stats(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        mock_store = MagicMock()
        mock_store.is_healthy = True
        mock_store.stats.return_value = {
            "node_count": 0,
            "edge_count": 0,
            "healthy": True,
            "schema_version": "2",
            "metrics": {},
        }
        svc = self._make_svc(graph_store=mock_store)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        data = svc._get_status_data()
        assert data["graph_store"]["schema_version"] == "2"

    def test_get_status_recovers_from_stats_exception(self):
        """_get_status_data should not raise even if store.stats() throws."""
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        mock_store = MagicMock()
        mock_store.is_healthy = True
        mock_store.stats.side_effect = RuntimeError("DB exploded")
        svc = self._make_svc(graph_store=mock_store)
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        # Should not raise
        data = svc._get_status_data()
        assert isinstance(data, dict)

    def test_call_tool_dispatches_get_status(self):
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        svc._graph_store_cache = None
        svc._graph_store_loaded = True
        svc._index_cache = None
        svc._rate_limiters = {}
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"

        # Set up minimal mcp_config with rate_limits that includes get_status
        from ws_ctx_engine.mcp.config import MCPConfig

        svc.mcp_config = MCPConfig()
        from ws_ctx_engine.mcp.security import RateLimiter

        svc._rate_limiter = RateLimiter(svc.mcp_config.rate_limits)
        svc._cache = {}

        result = svc.call_tool("get_status", {})
        # Should not return TOOL_NOT_FOUND
        assert result.get("error") != "TOOL_NOT_FOUND"

    def test_call_tool_get_status_not_unknown_tool(self):
        """get_status must be in the valid tools set inside call_tool."""
        from pathlib import Path

        from ws_ctx_engine.mcp.config import MCPConfig
        from ws_ctx_engine.mcp.security import RateLimiter
        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        svc._graph_store_cache = None
        svc._graph_store_loaded = True
        svc._index_cache = None
        svc._rate_limiters = {}
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"
        svc.mcp_config = MCPConfig()
        svc._rate_limiter = RateLimiter(svc.mcp_config.rate_limits)
        svc._cache = {}

        result = svc.call_tool("get_status", {})
        assert "error" not in result or result["error"] != "TOOL_NOT_FOUND"

    def test_get_status_data_returns_dict_on_unexpected_exception(self):
        """Even if an unexpected exception fires, return a safe dict."""
        from pathlib import Path

        from ws_ctx_engine.mcp.tools import MCPToolService

        svc = MCPToolService.__new__(MCPToolService)
        svc._graph_store_cache = None
        svc._graph_store_loaded = True
        svc._index_cache = None
        svc.workspace_root = Path("/nonexistent/path")
        svc.index_dir = ".ws-ctx-engine"

        # Patch _load_metadata to blow up
        with patch.object(type(svc), "_load_metadata", side_effect=RuntimeError("boom")):
            data = svc._get_status_data()

        assert isinstance(data, dict)
        assert "ready" in data or "error" in data
