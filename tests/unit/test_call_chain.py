"""Tests for GraphStore.find_path() BFS and handle_call_chain."""
from __future__ import annotations
import pytest

pycozo = pytest.importorskip("pycozo")

from ws_ctx_engine.graph.cozo_store import GraphStore
from ws_ctx_engine.graph.builder import Node, Edge


def _make_call_graph() -> GraphStore:
    """
    Graph (file-level CALLS model, matching what chunks_to_full_graph produces):
      a.py contains fn_a          → file a.py CALLS fn_c
      c.py contains fn_b          → file c.py has no outgoing CALLS
      b.py contains fn_c, fn_d   → file b.py CALLS fn_d

    Call chain: fn_a →(via a.py→fn_c)→ fn_c →(via b.py→fn_d)→ fn_d
    fn_b has no path to fn_d.
    """
    store = GraphStore("mem")
    nodes = [
        Node(id="a.py", kind="file", name="a.py", file="a.py", language="python"),
        Node(id="b.py", kind="file", name="b.py", file="b.py", language="python"),
        Node(id="c.py", kind="file", name="c.py", file="c.py", language="python"),
        Node(id="a.py#fn_a", kind="function", name="fn_a", file="a.py", language="python"),
        Node(id="c.py#fn_b", kind="function", name="fn_b", file="c.py", language="python"),
        Node(id="b.py#fn_c", kind="function", name="fn_c", file="b.py", language="python"),
        Node(id="b.py#fn_d", kind="function", name="fn_d", file="b.py", language="python"),
    ]
    edges = [
        Edge(src="a.py", relation="CONTAINS", dst="a.py#fn_a"),
        Edge(src="c.py", relation="CONTAINS", dst="c.py#fn_b"),
        Edge(src="b.py", relation="CONTAINS", dst="b.py#fn_c"),
        Edge(src="b.py", relation="CONTAINS", dst="b.py#fn_d"),
        # FILE-level CALLS: a.py calls fn_c; b.py calls fn_d
        Edge(src="a.py", relation="CALLS", dst="b.py#fn_c"),
        Edge(src="b.py", relation="CALLS", dst="b.py#fn_d"),
    ]
    store.bulk_upsert(nodes, edges)
    return store


class TestFindPath:
    def test_direct_call_depth1(self):
        store = _make_call_graph()
        path = store.find_path("fn_a", "fn_c")
        assert path == ["fn_a", "fn_c"]

    def test_two_hop_path(self):
        store = _make_call_graph()
        path = store.find_path("fn_a", "fn_d")
        assert path == ["fn_a", "fn_c", "fn_d"]

    def test_no_path_returns_empty(self):
        store = _make_call_graph()
        path = store.find_path("fn_b", "fn_d")
        assert path == []

    def test_max_depth_respected(self):
        store = _make_call_graph()
        # Path exists at depth 2, but max_depth=1 should return empty
        path = store.find_path("fn_a", "fn_d", max_depth=1)
        assert path == []

    def test_same_function_returns_single(self):
        store = _make_call_graph()
        path = store.find_path("fn_a", "fn_a")
        assert path == ["fn_a"]

    def test_nonexistent_function_returns_empty(self):
        store = _make_call_graph()
        path = store.find_path("nonexistent", "fn_c")
        assert path == []

    def test_cycle_no_infinite_loop(self):
        """Cyclic call graph must terminate."""
        store = GraphStore("mem")
        nodes = [
            Node(id="x.py", kind="file", name="x.py", file="x.py", language="python"),
            Node(id="x.py#ping", kind="function", name="ping", file="x.py", language="python"),
            Node(id="x.py#pong", kind="function", name="pong", file="x.py", language="python"),
        ]
        edges = [
            Edge(src="x.py", relation="CONTAINS", dst="x.py#ping"),
            Edge(src="x.py", relation="CONTAINS", dst="x.py#pong"),
            # FILE-level CALLS: x.py calls both ping and pong (mutual recursion)
            Edge(src="x.py", relation="CALLS", dst="x.py#ping"),
            Edge(src="x.py", relation="CALLS", dst="x.py#pong"),
        ]
        store.bulk_upsert(nodes, edges)
        path = store.find_path("ping", "nonexistent")
        assert path == []  # terminates, no infinite loop


class TestHandleCallChain:
    def test_returns_real_path(self):
        from ws_ctx_engine.mcp.graph_tools import handle_call_chain
        store = _make_call_graph()
        result = handle_call_chain(store, {"from_fn": "fn_a", "to_fn": "fn_d"})
        assert result.get("error") is None or result.get("error") != "NOT_IMPLEMENTED"
        assert "path" in result

    def test_no_path_returns_empty_path(self):
        from ws_ctx_engine.mcp.graph_tools import handle_call_chain
        store = _make_call_graph()
        result = handle_call_chain(store, {"from_fn": "fn_b", "to_fn": "fn_d"})
        assert result["path"] == []

    def test_missing_args_returns_invalid(self):
        from ws_ctx_engine.mcp.graph_tools import handle_call_chain
        result = handle_call_chain(None, {"from_fn": "fn_a"})
        assert result["error"] == "INVALID_ARGUMENT"

    def test_unhealthy_store_returns_graph_unavailable(self):
        from ws_ctx_engine.mcp.graph_tools import handle_call_chain
        from unittest.mock import MagicMock
        store = MagicMock()
        store.is_healthy = False
        result = handle_call_chain(store, {"from_fn": "fn_a", "to_fn": "fn_c"})
        assert result["error"] == "GRAPH_UNAVAILABLE"
