"""Tests for PageRank caching in IGraphRepoMap and NetworkXRepoMap (Phase 1)."""

from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.models import CodeChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunks() -> list[CodeChunk]:
    return [
        CodeChunk(
            path="a.py",
            content="def foo(): pass",
            language="python",
            symbols_defined=["foo"],
            symbols_referenced=[],
            start_line=1,
            end_line=1,
        ),
        CodeChunk(
            path="b.py",
            content="import a",
            language="python",
            symbols_defined=[],
            symbols_referenced=["foo"],
            start_line=1,
            end_line=1,
        ),
    ]


# ---------------------------------------------------------------------------
# IGraphRepoMap cache tests
# ---------------------------------------------------------------------------


class TestIGraphPageRankCache:
    @pytest.fixture()
    def igraph_map(self) -> "IGraphRepoMap":
        pytest.importorskip("igraph")
        from ws_ctx_engine.graph.graph import IGraphRepoMap

        g = IGraphRepoMap()
        g.build(_make_chunks())
        return g

    def test_cache_hit_returns_same_dict_instance(self, igraph_map: "IGraphRepoMap") -> None:
        """Second call must return the exact same dict object (cache hit)."""
        r1 = igraph_map.pagerank()
        r2 = igraph_map.pagerank()
        assert r1 is r2

    def test_underlying_compute_called_only_once(self, igraph_map: "IGraphRepoMap") -> None:
        """The underlying igraph.pagerank() must be called exactly once for same args."""
        call_count = 0
        original = igraph_map.graph.pagerank  # type: ignore[attr-defined]

        def counted(*args: object, **kwargs: object) -> list:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        igraph_map.graph.pagerank = counted  # type: ignore[attr-defined]

        igraph_map.pagerank()
        igraph_map.pagerank()
        igraph_map.pagerank()

        assert call_count == 1

    def test_cache_invalidated_after_build(self, igraph_map: "IGraphRepoMap") -> None:
        """After re-building the graph, the next pagerank() must recompute."""
        r1 = igraph_map.pagerank()
        igraph_map.build(_make_chunks())  # rebuild clears cache
        r2 = igraph_map.pagerank()
        # They are equal in value but must be different objects (recomputed)
        assert r1 is not r2

    def test_different_changed_files_produce_different_results(
        self, igraph_map: "IGraphRepoMap"
    ) -> None:
        """Different changed_files arguments yield different (boosted) scores."""
        r_none = igraph_map.pagerank(changed_files=None)
        r_a = igraph_map.pagerank(changed_files=["a.py"])
        # a.py gets boosted, so its score must differ
        assert r_none["a.py"] != r_a["a.py"]


# ---------------------------------------------------------------------------
# NetworkXRepoMap cache tests
# ---------------------------------------------------------------------------


class TestNetworkXPageRankCache:
    @pytest.fixture()
    def nx_map(self) -> "NetworkXRepoMap":
        pytest.importorskip("networkx")
        from ws_ctx_engine.graph.graph import NetworkXRepoMap

        g = NetworkXRepoMap()
        g.build(_make_chunks())
        return g

    def test_cache_hit_returns_same_dict_instance(self, nx_map: "NetworkXRepoMap") -> None:
        r1 = nx_map.pagerank()
        r2 = nx_map.pagerank()
        assert r1 is r2

    def test_underlying_compute_called_only_once(self, nx_map: "NetworkXRepoMap") -> None:
        call_count = 0
        original_pr = nx_map._nx.pagerank  # type: ignore[attr-defined]

        def counted(*args: object, **kwargs: object) -> dict:
            nonlocal call_count
            call_count += 1
            return original_pr(*args, **kwargs)

        nx_map._nx.pagerank = counted  # type: ignore[attr-defined]

        nx_map.pagerank()
        nx_map.pagerank()

        assert call_count == 1

    def test_cache_invalidated_after_build(self, nx_map: "NetworkXRepoMap") -> None:
        r1 = nx_map.pagerank()
        nx_map.build(_make_chunks())
        r2 = nx_map.pagerank()
        assert r1 is not r2
