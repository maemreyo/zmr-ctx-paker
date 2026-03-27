"""Tests for SignalRouter (query intent detection)."""

from __future__ import annotations

import pytest

from ws_ctx_engine.graph.signal_router import GraphIntent, classify_graph_intent, needs_graph


class TestNeedsGraph:
    def test_callers_query_returns_true(self):
        assert needs_graph("what calls authenticate") is True

    def test_callers_variant(self):
        assert needs_graph("who calls login") is True

    def test_imports_query_returns_true(self):
        assert needs_graph("who imports the config module") is True

    def test_impact_query_returns_true(self):
        assert needs_graph("impact of changing models.py") is True

    def test_depends_on_returns_true(self):
        assert needs_graph("what depends on the auth module") is True

    def test_where_defined_returns_true(self):
        assert needs_graph("where is authenticate defined") is True

    def test_semantic_query_returns_false(self):
        assert needs_graph("show me the main function") is False

    def test_how_query_returns_false(self):
        assert needs_graph("how does pagination work") is False

    def test_empty_query_returns_false(self):
        assert needs_graph("") is False

    def test_case_insensitive(self):
        assert needs_graph("What CALLS authenticate") is True


class TestClassifyGraphIntent:
    def test_callers_of_intent(self):
        intent = classify_graph_intent("find callers of authenticate")
        assert intent.intent_type == "callers_of"
        assert "authenticate" in intent.target

    def test_impact_of_intent(self):
        intent = classify_graph_intent("what breaks if I change models.py")
        assert intent.intent_type == "impact_of"

    def test_imports_is_impact(self):
        intent = classify_graph_intent("who imports config")
        assert intent.intent_type == "impact_of"

    def test_none_intent_for_semantic(self):
        intent = classify_graph_intent("how does caching work")
        assert intent.intent_type == "none"
        assert intent.target == ""

    def test_graph_intent_is_frozen(self):
        intent = GraphIntent(intent_type="none", target="")
        with pytest.raises((AttributeError, TypeError)):
            intent.intent_type = "callers_of"  # type: ignore
