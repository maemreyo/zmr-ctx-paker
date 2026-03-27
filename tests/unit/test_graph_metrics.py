"""Tests for GraphMetrics in-process collector."""
from __future__ import annotations
import pytest
from ws_ctx_engine.graph.metrics import GraphMetrics


class TestGraphMetrics:
    def test_initial_state(self):
        m = GraphMetrics()
        snap = m.snapshot()
        assert snap["query_count"] == 0
        assert snap["error_count"] == 0
        assert snap["avg_latency_ms"] == 0.0

    def test_record_success(self):
        m = GraphMetrics()
        m.record(5.0, error=False)
        snap = m.snapshot()
        assert snap["query_count"] == 1
        assert snap["error_count"] == 0
        assert snap["avg_latency_ms"] == pytest.approx(5.0)

    def test_record_error(self):
        m = GraphMetrics()
        m.record(2.0, error=True)
        snap = m.snapshot()
        assert snap["query_count"] == 1
        assert snap["error_count"] == 1

    def test_avg_latency_multiple(self):
        m = GraphMetrics()
        m.record(10.0, error=False)
        m.record(20.0, error=False)
        snap = m.snapshot()
        assert snap["avg_latency_ms"] == pytest.approx(15.0)

    def test_bounded_deque_caps_at_1000(self):
        m = GraphMetrics()
        for i in range(1500):
            m.record(float(i), error=False)
        snap = m.snapshot()
        assert snap["query_count"] == 1500
        # avg should only reflect last 1000
        assert snap["avg_latency_ms"] == pytest.approx(sum(range(500, 1500)) / 1000)

    def test_snapshot_is_dict(self):
        m = GraphMetrics()
        snap = m.snapshot()
        assert isinstance(snap, dict)
        assert "query_count" in snap
        assert "error_count" in snap
        assert "avg_latency_ms" in snap
        assert "last_latency_ms" in snap
