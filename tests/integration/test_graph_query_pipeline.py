"""
Integration test for Phase 3: graph augmentation in the query pipeline.

Uses pycozo in-memory store via a mock GraphStore to avoid the full
CozoDB/RocksDB dependency, while still exercising the real ContextAssembler
and SignalRouter code paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.graph.context_assembler import AssemblyResult, ContextAssembler
from ws_ctx_engine.graph.signal_router import GraphIntent, classify_graph_intent, needs_graph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(*, healthy: bool = True, callers: list[str] | None = None, importers: list[str] | None = None) -> MagicMock:
    store = MagicMock()
    store.is_healthy = healthy
    store.callers_of.return_value = [{"caller_file": f} for f in (callers or [])]
    store.impact_of.return_value = importers or []
    return store


# ---------------------------------------------------------------------------
# Signal router integration
# ---------------------------------------------------------------------------


class TestSignalRouterIntegration:
    """Verify cross-file queries are routed to graph; semantic ones are not."""

    @pytest.mark.parametrize(
        "query",
        [
            "what calls authenticate",
            "find callers of login",
            "who imports config",
            "impact of changing models.py",
            "what breaks if I change auth.py",
            "what depends on the database module",
            "where is validate defined",
        ],
    )
    def test_cross_file_queries_need_graph(self, query: str) -> None:
        assert needs_graph(query) is True, f"Expected needs_graph=True for: {query!r}"

    @pytest.mark.parametrize(
        "query",
        [
            "how does authentication work",
            "show me the main function",
            "explain the retry logic",
            "what is the token budget",
            "",
        ],
    )
    def test_semantic_queries_dont_need_graph(self, query: str) -> None:
        assert needs_graph(query) is False, f"Expected needs_graph=False for: {query!r}"


# ---------------------------------------------------------------------------
# ContextAssembler integration — callers_of
# ---------------------------------------------------------------------------


class TestContextAssemblerCallersOfIntegration:
    """Three-file fixture: auth.py calls login(); session.py and middleware.py also call login()."""

    def _vector_results(self) -> list[tuple[str, float]]:
        return [("auth.py", 0.85), ("user.py", 0.60)]

    def test_callers_of_augments_results(self) -> None:
        store = _make_store(callers=["session.py", "middleware.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = classify_graph_intent("what calls login")

        result = assembler.assemble(self._vector_results(), intent)

        assert result.graph_augmented is True
        assert result.graph_files_added == 2
        paths = [p for p, _ in result.ranked_files]
        assert "session.py" in paths
        assert "middleware.py" in paths

    def test_scores_sorted_descending(self) -> None:
        store = _make_store(callers=["session.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")

        result = assembler.assemble(self._vector_results(), intent)

        scores = [s for _, s in result.ranked_files]
        assert scores == sorted(scores, reverse=True)

    def test_no_duplicate_files(self) -> None:
        """If graph returns a file already in vector results, it must appear exactly once."""
        store = _make_store(callers=["auth.py", "new_caller.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")

        result = assembler.assemble(self._vector_results(), intent)

        paths = [p for p, _ in result.ranked_files]
        assert paths.count("auth.py") == 1
        assert "new_caller.py" in paths

    def test_semantic_query_skips_graph(self) -> None:
        """A purely semantic query must not trigger graph augmentation."""
        store = _make_store(callers=["session.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = classify_graph_intent("how does caching work")

        result = assembler.assemble(self._vector_results(), intent)

        assert result.graph_augmented is False
        assert result.ranked_files == self._vector_results()
        store.callers_of.assert_not_called()


# ---------------------------------------------------------------------------
# ContextAssembler integration — impact_of
# ---------------------------------------------------------------------------


class TestContextAssemblerImpactOfIntegration:
    def test_impact_of_adds_dependent_files(self) -> None:
        store = _make_store(importers=["main.py", "app.py", "cli.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.4)
        intent = classify_graph_intent("what breaks if I change models.py")

        vector = [("models.py", 0.9), ("db.py", 0.5)]
        result = assembler.assemble(vector, intent)

        paths = [p for p, _ in result.ranked_files]
        assert "main.py" in paths
        assert "app.py" in paths
        assert "cli.py" in paths
        assert result.graph_files_added == 3

    def test_impact_of_graph_score_respects_weight(self) -> None:
        store = _make_store(importers=["new_file.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.5)
        intent = GraphIntent(intent_type="impact_of", target="models.py")

        vector = [("models.py", 1.0)]
        result = assembler.assemble(vector, intent)

        score_map = dict(result.ranked_files)
        # max_score=1.0, weight=0.5 → graph file score = 0.5
        assert score_map["new_file.py"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Degradation — unhealthy store
# ---------------------------------------------------------------------------


class TestDegradationIntegration:
    def test_unhealthy_store_passes_through(self) -> None:
        store = _make_store(healthy=False)
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9), ("user.py", 0.7)]

        result = assembler.assemble(vector, intent)

        assert result.ranked_files == vector
        assert result.graph_augmented is False
        store.callers_of.assert_not_called()

    def test_store_exception_passes_through(self) -> None:
        store = _make_store(healthy=True)
        store.callers_of.side_effect = RuntimeError("DB exploded")
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9)]

        result = assembler.assemble(vector, intent)

        assert result.ranked_files == vector
        assert result.graph_augmented is False

    def test_empty_vector_with_graph_results(self) -> None:
        """Edge case: empty vector results, graph still contributes."""
        store = _make_store(callers=["session.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")

        result = assembler.assemble([], intent)

        # max_score defaults to 1.0 when vector_results is empty
        assert result.graph_augmented is True
        assert result.graph_files_added == 1
        paths = [p for p, _ in result.ranked_files]
        assert "session.py" in paths
