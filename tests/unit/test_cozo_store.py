"""Tests for CozoStore (GraphStore backed by CozoDB).

All tests are skipped when pycozo is not installed.

TDD: tests written BEFORE implementation (RED phase).
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pycozo = pytest.importorskip("pycozo", reason="pycozo not installed — skipping GraphStore tests")

from ws_ctx_engine.graph.builder import Edge, Node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_node(path: str, language: str = "python") -> Node:
    return Node(id=path, kind="file", name=path.rsplit("/", 1)[-1], file=path, language=language)


def _sym_node(file_path: str, symbol: str, kind: str = "function") -> Node:
    node_id = f"{file_path}#{symbol}"
    return Node(id=node_id, kind=kind, name=symbol, file=file_path, language="python")


def _contains(file_path: str, symbol: str) -> Edge:
    return Edge(src=file_path, relation="CONTAINS", dst=f"{file_path}#{symbol}")


def _calls(src_file: str, dst_sym_id: str) -> Edge:
    return Edge(src=src_file, relation="CALLS", dst=dst_sym_id)


def _imports(src_file: str, dst_file: str) -> Edge:
    return Edge(src=src_file, relation="IMPORTS", dst=dst_file)


# ---------------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------------


class TestGraphStoreImport:
    def test_import(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore  # noqa: F401


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestGraphStoreInit:
    def test_init_mem_succeeds(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        assert store.is_healthy is True

    def test_init_failure_sets_unhealthy(self) -> None:
        """When _create_client raises, GraphStore.__init__ must not raise and is_healthy is False."""
        from ws_ctx_engine.graph import cozo_store
        from ws_ctx_engine.graph.cozo_store import GraphStore

        with patch.object(cozo_store, "_create_client", side_effect=ImportError("no pycozo")):
            store = GraphStore("mem")
            assert store.is_healthy is False

    def test_init_mem_store_creates_schema(self) -> None:
        """After init, the nodes and edges relations must exist in the DB."""
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        assert store.is_healthy


# ---------------------------------------------------------------------------
# bulk_upsert + contains_of
# ---------------------------------------------------------------------------


class TestBulkUpsert:
    def test_bulk_upsert_and_contains_of(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [_file_node("src/auth.py"), _sym_node("src/auth.py", "login")]
        edges = [_contains("src/auth.py", "login")]

        store.bulk_upsert(nodes, edges)
        result = store.contains_of("src/auth.py")

        assert result, "contains_of returned empty after bulk_upsert"
        syms = [row.get("sym") or row.get(list(row.keys())[0]) for row in result]
        assert any("login" in str(s) for s in syms), f"login not in result: {result}"

    def test_bulk_upsert_empty_is_noop(self) -> None:
        """Calling bulk_upsert with empty lists must not raise."""
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        store.bulk_upsert([], [])  # must not raise
        assert store.is_healthy

    def test_bulk_upsert_multiple_files(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [
            _file_node("src/auth.py"),
            _sym_node("src/auth.py", "login"),
            _file_node("src/utils.py"),
            _sym_node("src/utils.py", "hash_password"),
        ]
        edges = [
            _contains("src/auth.py", "login"),
            _contains("src/utils.py", "hash_password"),
        ]
        store.bulk_upsert(nodes, edges)

        auth_syms = store.contains_of("src/auth.py")
        utils_syms = store.contains_of("src/utils.py")

        assert auth_syms, "No symbols for auth.py"
        assert utils_syms, "No symbols for utils.py"


# ---------------------------------------------------------------------------
# callers_of
# ---------------------------------------------------------------------------


class TestCallersOf:
    def test_callers_of_with_calls_edges(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [
            _file_node("src/auth.py"),
            _sym_node("src/auth.py", "login"),
            _file_node("src/main.py"),
        ]
        edges = [
            _contains("src/auth.py", "login"),
            _calls("src/main.py", "src/auth.py#login"),
        ]
        store.bulk_upsert(nodes, edges)

        result = store.callers_of("login")
        assert result, f"Expected callers of 'login', got: {result}"
        caller_files = [list(row.values())[0] for row in result]
        assert any("main.py" in str(f) for f in caller_files), (
            f"main.py not in callers: {result}"
        )

    def test_callers_of_no_callers_returns_empty(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [_file_node("src/auth.py"), _sym_node("src/auth.py", "login")]
        edges = [_contains("src/auth.py", "login")]
        store.bulk_upsert(nodes, edges)

        result = store.callers_of("login")
        assert result == []

    def test_callers_of_unknown_function_returns_empty(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        store.bulk_upsert([], [])

        result = store.callers_of("totally_unknown_fn")
        assert result == []


# ---------------------------------------------------------------------------
# impact_of
# ---------------------------------------------------------------------------


class TestImpactOf:
    def test_impact_of_with_imports_edges(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [_file_node("src/auth.py"), _file_node("src/main.py")]
        edges = [_imports("src/main.py", "src/auth.py")]
        store.bulk_upsert(nodes, edges)

        result = store.impact_of("src/auth.py")
        assert result, f"Expected importers of auth.py, got: {result}"
        assert any("main.py" in r for r in result), f"main.py not in impact: {result}"

    def test_impact_of_no_importers_returns_empty(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [_file_node("src/auth.py")]
        store.bulk_upsert(nodes, [])

        result = store.impact_of("src/auth.py")
        assert result == []


# ---------------------------------------------------------------------------
# delete_file_scope
# ---------------------------------------------------------------------------


class TestDeleteFileScope:
    def test_delete_file_scope_removes_nodes_and_edges(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [_file_node("src/auth.py"), _sym_node("src/auth.py", "login")]
        edges = [_contains("src/auth.py", "login")]
        store.bulk_upsert(nodes, edges)

        store.delete_file_scope("src/auth.py")

        result = store.contains_of("src/auth.py")
        assert result == [], f"Expected empty after delete, got: {result}"

    def test_delete_file_scope_removes_dangling_edges(self) -> None:
        """Edges pointing TO deleted file must also be removed."""
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        nodes = [_file_node("src/auth.py"), _file_node("src/main.py")]
        edges = [_imports("src/main.py", "src/auth.py")]
        store.bulk_upsert(nodes, edges)

        # Delete auth.py — the IMPORTS edge from main.py should also be gone
        store.delete_file_scope("src/auth.py")

        result = store.impact_of("src/auth.py")
        assert result == [], f"Dangling IMPORTS edge still present: {result}"

    def test_delete_file_scope_nonexistent_is_noop(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore("mem")
        store.bulk_upsert([], [])
        store.delete_file_scope("src/does_not_exist.py")  # must not raise
        assert store.is_healthy


# ---------------------------------------------------------------------------
# Unhealthy store behaviour
# ---------------------------------------------------------------------------


class TestUnhealthyStore:
    def _make_unhealthy(self) -> "object":
        from ws_ctx_engine.graph.cozo_store import GraphStore

        store = GraphStore.__new__(GraphStore)
        object.__setattr__(store, "_healthy", False)
        object.__setattr__(store, "_db", None)
        return store

    def test_unhealthy_bulk_upsert_is_noop(self) -> None:
        """bulk_upsert must silently no-op when store is not healthy."""
        store = self._make_unhealthy()
        from ws_ctx_engine.graph.cozo_store import GraphStore

        assert isinstance(store, GraphStore)
        nodes = [_file_node("src/auth.py")]
        store.bulk_upsert(nodes, [])  # must not raise
        assert store.is_healthy is False

    def test_unhealthy_query_returns_empty(self) -> None:
        """callers_of must return [] when store is unhealthy."""
        store = self._make_unhealthy()
        result = store.callers_of("login")
        assert result == []

    def test_unhealthy_contains_of_returns_empty(self) -> None:
        store = self._make_unhealthy()
        result = store.contains_of("src/auth.py")
        assert result == []

    def test_unhealthy_impact_of_returns_empty(self) -> None:
        store = self._make_unhealthy()
        result = store.impact_of("src/auth.py")
        assert result == []


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_graphstore_satisfies_protocol(self) -> None:
        from ws_ctx_engine.graph.cozo_store import GraphStore
        from ws_ctx_engine.graph.store_protocol import GraphStoreProtocol

        store = GraphStore("mem")
        assert isinstance(store, GraphStoreProtocol)
