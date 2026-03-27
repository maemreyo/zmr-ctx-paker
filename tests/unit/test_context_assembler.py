"""Tests for ContextAssembler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ws_ctx_engine.graph.signal_router import GraphIntent
from ws_ctx_engine.graph.context_assembler import AssemblyResult, ContextAssembler


def _make_store(*, healthy: bool = True, callers: list[str] | None = None, importers: list[str] | None = None):
    store = MagicMock()
    store.is_healthy = healthy
    store.callers_of.return_value = [{"caller_file": f} for f in (callers or [])]
    store.impact_of.return_value = importers or []
    return store


class TestContextAssemblerCallersOf:
    def test_adds_graph_files_not_in_vector(self):
        store = _make_store(callers=["session.py", "middleware.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9), ("user.py", 0.7)]
        result = assembler.assemble(vector, intent)
        paths = [p for p, _ in result.ranked_files]
        assert "session.py" in paths
        assert "middleware.py" in paths
        assert result.graph_augmented is True
        assert result.graph_files_added == 2

    def test_deduplication_keeps_higher_score(self):
        store = _make_store(callers=["auth.py"])  # already in vector
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9)]
        result = assembler.assemble(vector, intent)
        paths = [p for p, _ in result.ranked_files]
        assert paths.count("auth.py") == 1
        assert result.graph_files_added == 0

    def test_sorted_descending_by_score(self):
        store = _make_store(callers=["new.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9), ("user.py", 0.7)]
        result = assembler.assemble(vector, intent)
        scores = [s for _, s in result.ranked_files]
        assert scores == sorted(scores, reverse=True)


class TestContextAssemblerImpactOf:
    def test_impact_of_adds_importers(self):
        store = _make_store(importers=["main.py", "app.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.5)
        intent = GraphIntent(intent_type="impact_of", target="models.py")
        vector = [("models.py", 0.8)]
        result = assembler.assemble(vector, intent)
        paths = [p for p, _ in result.ranked_files]
        assert "main.py" in paths
        assert "app.py" in paths


class TestContextAssemblerDegradation:
    def test_unhealthy_store_returns_vector_unchanged(self):
        store = _make_store(healthy=False)
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9)]
        result = assembler.assemble(vector, intent)
        assert result.ranked_files == vector
        assert result.graph_augmented is False

    def test_none_intent_returns_vector_unchanged(self):
        store = _make_store()
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="none", target="")
        vector = [("auth.py", 0.9)]
        result = assembler.assemble(vector, intent)
        assert result.ranked_files == vector
        assert result.graph_augmented is False

    def test_empty_graph_results_no_augmentation(self):
        store = _make_store(callers=[])
        assembler = ContextAssembler(store, graph_query_weight=0.3)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9)]
        result = assembler.assemble(vector, intent)
        assert result.ranked_files == vector
        assert result.graph_augmented is False

    def test_weight_zero_gives_zero_score_to_graph_files(self):
        store = _make_store(callers=["new.py"])
        assembler = ContextAssembler(store, graph_query_weight=0.0)
        intent = GraphIntent(intent_type="callers_of", target="login")
        vector = [("auth.py", 0.9)]
        result = assembler.assemble(vector, intent)
        graph_scores = {p: s for p, s in result.ranked_files if p == "new.py"}
        assert graph_scores.get("new.py", -1) == 0.0
