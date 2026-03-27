"""Tests for ws_ctx_engine.retrieval.hybrid_engine (Phase 3 — TDD-first).

Covers:
- RRF fusion formula correctness
- Result ordering: highest-scoring items first
- top_k truncation
- Degenerate cases: one source empty, both empty
- Score normalisation to [0, 1]
- Consistent file paths preserved from inputs
"""

from unittest.mock import MagicMock

import pytest

from ws_ctx_engine.retrieval.hybrid_engine import HybridSearchEngine, rrf_score


# ---------------------------------------------------------------------------
# rrf_score unit tests
# ---------------------------------------------------------------------------


class TestRRFScore:
    def test_rank_1_with_default_k(self) -> None:
        """rrf_score(rank=1, k=60) == 1/61."""
        assert abs(rrf_score(1) - 1 / 61) < 1e-9

    def test_rank_increases_reduce_score(self) -> None:
        assert rrf_score(1) > rrf_score(10) > rrf_score(100)

    def test_custom_k(self) -> None:
        assert abs(rrf_score(1, k=0) - 1.0) < 1e-9  # k=0 → 1/(0+1) = 1.0
        assert abs(rrf_score(1, k=10) - 1 / 11) < 1e-9

    def test_score_always_positive(self) -> None:
        for rank in [1, 5, 50, 1000]:
            assert rrf_score(rank) > 0


# ---------------------------------------------------------------------------
# HybridSearchEngine fusion tests
# ---------------------------------------------------------------------------


def _make_engine(
    vector_results: list[tuple[str, float]],
    bm25_results: list[tuple[str, float]],
) -> HybridSearchEngine:
    mock_vector = MagicMock()
    mock_vector.search.return_value = vector_results

    mock_bm25 = MagicMock()
    mock_bm25.search.return_value = bm25_results
    mock_bm25._bm25 = object()  # non-None → index is built

    return HybridSearchEngine(vector_index=mock_vector, bm25_index=mock_bm25)


class TestHybridSearchEngineSearch:
    def test_returns_list_of_tuples(self) -> None:
        engine = _make_engine(
            vector_results=[("src/auth.py", 0.9), ("src/utils.py", 0.5)],
            bm25_results=[("src/auth.py", 10.0), ("src/session.py", 5.0)],
        )
        results = engine.search("authenticate", top_k=5)
        assert isinstance(results, list)
        for item in results:
            assert len(item) == 2

    def test_top_k_limits_output(self) -> None:
        engine = _make_engine(
            vector_results=[("a.py", 1.0), ("b.py", 0.8), ("c.py", 0.6)],
            bm25_results=[("a.py", 5.0), ("b.py", 3.0), ("d.py", 2.0)],
        )
        results = engine.search("query", top_k=2)
        assert len(results) <= 2

    def test_results_sorted_descending(self) -> None:
        engine = _make_engine(
            vector_results=[("a.py", 0.9), ("b.py", 0.5), ("c.py", 0.3)],
            bm25_results=[("b.py", 8.0), ("a.py", 2.0), ("c.py", 1.0)],
        )
        results = engine.search("query", top_k=10)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_scores_normalised_to_0_1(self) -> None:
        engine = _make_engine(
            vector_results=[("a.py", 0.9), ("b.py", 0.5)],
            bm25_results=[("a.py", 10.0), ("c.py", 1.0)],
        )
        results = engine.search("query", top_k=10)
        for _, score in results:
            assert 0.0 <= score <= 1.0 + 1e-9, f"Score out of range: {score}"

    def test_file_present_in_both_sources_ranks_higher(self) -> None:
        """A file in both vector and BM25 results should outrank a file in only one."""
        engine = _make_engine(
            vector_results=[("shared.py", 0.8), ("only_vec.py", 0.9)],
            bm25_results=[("shared.py", 5.0), ("only_bm25.py", 6.0)],
        )
        results = engine.search("query", top_k=10)
        path_to_score = dict(results)
        # shared.py appears in both lists; only_vec.py only in one
        assert path_to_score.get("shared.py", 0) >= path_to_score.get("only_vec.py", 0)

    def test_empty_vector_results_still_returns_bm25(self) -> None:
        engine = _make_engine(
            vector_results=[],
            bm25_results=[("a.py", 5.0), ("b.py", 2.0)],
        )
        results = engine.search("query", top_k=5)
        paths = [p for p, _ in results]
        assert "a.py" in paths or "b.py" in paths

    def test_empty_bm25_results_still_returns_vector(self) -> None:
        engine = _make_engine(
            vector_results=[("a.py", 0.9), ("b.py", 0.4)],
            bm25_results=[],
        )
        results = engine.search("query", top_k=5)
        paths = [p for p, _ in results]
        assert "a.py" in paths or "b.py" in paths

    def test_both_empty_returns_empty(self) -> None:
        engine = _make_engine(vector_results=[], bm25_results=[])
        results = engine.search("query", top_k=5)
        assert results == []

    def test_all_files_accounted_for(self) -> None:
        """Every file from either source must appear in the output."""
        vec = [("a.py", 0.9), ("b.py", 0.5)]
        bm25 = [("b.py", 4.0), ("c.py", 1.0)]
        engine = _make_engine(vector_results=vec, bm25_results=bm25)
        results = engine.search("query", top_k=10)
        paths = {p for p, _ in results}
        assert paths == {"a.py", "b.py", "c.py"}


# ---------------------------------------------------------------------------
# Integration with RetrievalEngine
# ---------------------------------------------------------------------------


class TestRetrievalEngineHybridIntegration:
    """Verify RetrievalEngine accepts a bm25_index and uses HybridSearchEngine."""

    def test_retrieval_engine_accepts_bm25_index_param(self) -> None:
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        mock_vector = MagicMock()
        mock_graph = MagicMock()
        mock_graph.pagerank.return_value = {}
        mock_bm25 = MagicMock()

        engine = RetrievalEngine(
            vector_index=mock_vector,
            graph=mock_graph,
            bm25_index=mock_bm25,
        )
        assert engine.bm25_index is mock_bm25

    def test_retrieval_engine_uses_hybrid_when_bm25_provided(self) -> None:
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        mock_vector = MagicMock()
        mock_vector.search.return_value = [("src/auth.py", 0.9)]
        mock_vector.get_file_symbols.return_value = {}

        mock_graph = MagicMock()
        mock_graph.pagerank.return_value = {"src/auth.py": 0.5}

        mock_bm25 = MagicMock()
        mock_bm25.search.return_value = [("src/auth.py", 5.0)]
        mock_bm25._bm25 = object()

        engine = RetrievalEngine(
            vector_index=mock_vector,
            graph=mock_graph,
            bm25_index=mock_bm25,
        )
        results = engine.retrieve(query="authenticate user", top_k=5)

        # BM25 search must have been called when bm25_index is provided
        mock_bm25.search.assert_called_once()
        assert isinstance(results, list)

    def test_retrieval_engine_works_without_bm25_index(self) -> None:
        """Default behaviour (no bm25_index) must be unchanged."""
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        mock_vector = MagicMock()
        mock_vector.search.return_value = [("src/auth.py", 0.9)]
        mock_vector.get_file_symbols.return_value = {}

        mock_graph = MagicMock()
        mock_graph.pagerank.return_value = {"src/auth.py": 0.5}

        engine = RetrievalEngine(
            vector_index=mock_vector,
            graph=mock_graph,
        )
        results = engine.retrieve(query="authenticate", top_k=5)
        assert isinstance(results, list)
