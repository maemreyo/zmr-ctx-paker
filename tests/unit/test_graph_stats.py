"""Tests for GraphStore.stats() and schema version."""
from __future__ import annotations
import pytest

pycozo = pytest.importorskip("pycozo")

from ws_ctx_engine.graph.cozo_store import GraphStore
from ws_ctx_engine.graph.builder import Node, Edge


class TestGraphStoreStats:
    def test_stats_empty_store(self):
        store = GraphStore("mem")
        assert store.is_healthy
        stats = store.stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        assert stats["healthy"] is True
        assert "schema_version" in stats
        assert "metrics" in stats

    def test_stats_after_upsert(self):
        store = GraphStore("mem")
        nodes = [Node(id="a.py", kind="file", name="a.py", file="a.py", language="python")]
        edges = []
        store.bulk_upsert(nodes, edges)
        stats = store.stats()
        assert stats["node_count"] == 1
        assert stats["edge_count"] == 0

    def test_stats_edge_count(self):
        store = GraphStore("mem")
        nodes = [
            Node(id="a.py", kind="file", name="a.py", file="a.py", language="python"),
            Node(id="a.py#fn", kind="function", name="fn", file="a.py", language="python"),
        ]
        edges = [Edge(src="a.py", relation="CONTAINS", dst="a.py#fn")]
        store.bulk_upsert(nodes, edges)
        stats = store.stats()
        assert stats["node_count"] == 2
        assert stats["edge_count"] == 1

    def test_schema_version_property(self):
        store = GraphStore("mem")
        assert store.schema_version == "1"

    def test_metrics_in_stats(self):
        store = GraphStore("mem")
        # Trigger a query
        store.callers_of("anything")
        stats = store.stats()
        assert stats["metrics"]["query_count"] >= 1

    def test_unhealthy_stats(self):
        """stats() on unhealthy store returns safe defaults."""
        store = GraphStore.__new__(GraphStore)
        store._healthy = False
        store._schema_version = "unknown"
        store._metrics = __import__("ws_ctx_engine.graph.metrics", fromlist=["GraphMetrics"]).GraphMetrics()
        stats = store.stats()
        assert stats["healthy"] is False
