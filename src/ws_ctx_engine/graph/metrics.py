"""Lightweight in-process query metrics for GraphStore."""

from __future__ import annotations

from collections import deque


class GraphMetrics:
    """Mutable metrics collector — one instance per GraphStore."""

    _MAX_LATENCIES = 1000

    def __init__(self) -> None:
        self.query_count: int = 0
        self.error_count: int = 0
        self._latencies: deque[float] = deque(maxlen=self._MAX_LATENCIES)
        self._last_latency_ms: float = 0.0

    def record(self, latency_ms: float, *, error: bool) -> None:
        self.query_count += 1
        if error:
            self.error_count += 1
        self._latencies.append(latency_ms)
        self._last_latency_ms = latency_ms

    def snapshot(self) -> dict:
        avg = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        return {
            "query_count": self.query_count,
            "error_count": self.error_count,
            "avg_latency_ms": avg,
            "last_latency_ms": self._last_latency_ms,
        }
