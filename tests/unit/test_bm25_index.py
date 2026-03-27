"""Tests for ws_ctx_engine.retrieval.bm25_index (Phase 3 — TDD-first)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.retrieval.bm25_index import BM25Index


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(
    path: str,
    content: str,
    language: str = "python",
    symbols_defined: list[str] | None = None,
) -> CodeChunk:
    return CodeChunk(
        path=path,
        content=content,
        language=language,
        start_line=1,
        end_line=5,
        symbols_defined=symbols_defined or [],
        symbols_referenced=[],
    )


AUTH_CHUNKS = [
    _chunk("src/auth.py", "def authenticate(user, password): return check(user, password)", symbols_defined=["authenticate"]),
    _chunk("src/session.py", "def create_session(user): return token(user)", symbols_defined=["create_session"]),
    _chunk("src/database.py", "def query_db(sql): return cursor.execute(sql)", symbols_defined=["query_db"]),
    _chunk("src/utils.py", "def hash_password(pw): return sha256(pw)", symbols_defined=["hash_password"]),
]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


class TestBM25IndexBuild:
    def test_build_does_not_raise(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)  # should not raise

    def test_build_with_empty_list(self) -> None:
        idx = BM25Index()
        idx.build([])  # edge case — no error

    def test_build_stores_chunk_count(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        assert idx.size == len(AUTH_CHUNKS)

    def test_rebuild_replaces_previous_index(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        idx.build(AUTH_CHUNKS[:2])
        assert idx.size == 2


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestBM25IndexSearch:
    def test_search_returns_list(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("authenticate user", top_k=5)
        assert isinstance(results, list)

    def test_search_returns_path_score_tuples(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("authenticate", top_k=5)
        for item in results:
            assert len(item) == 2
            path, score = item
            assert isinstance(path, str)
            assert isinstance(score, float)

    def test_search_top_k_limits_results(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("user password", top_k=2)
        assert len(results) <= 2

    def test_relevant_doc_ranked_first(self) -> None:
        """'authenticate' query should rank src/auth.py first."""
        pytest.importorskip("rank_bm25", reason="rank-bm25 not installed")
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("authenticate", top_k=4)
        assert results, "Expected at least one result"
        top_path = results[0][0]
        assert top_path == "src/auth.py", f"Expected src/auth.py first, got {top_path}"

    def test_scores_are_non_negative(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("authenticate user password", top_k=4)
        for _, score in results:
            assert score >= 0.0

    def test_search_on_empty_index_returns_empty(self) -> None:
        idx = BM25Index()
        idx.build([])
        results = idx.search("anything", top_k=5)
        assert results == []

    def test_search_unknown_query_returns_results_or_empty(self) -> None:
        """A query with no matching tokens should not raise."""
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("xyzzy nonexistent zork", top_k=5)
        assert isinstance(results, list)

    def test_results_sorted_by_score_descending(self) -> None:
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)
        results = idx.search("hash password sha256", top_k=4)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# rank-bm25 unavailable — graceful fallback
# ---------------------------------------------------------------------------


class TestBM25IndexFallback:
    def test_search_returns_empty_when_rank_bm25_missing(self) -> None:
        """If rank_bm25 is not installed, search() must return [] not raise."""
        idx = BM25Index()
        idx.build(AUTH_CHUNKS)

        with patch.dict(sys.modules, {"rank_bm25": None}):  # type: ignore[dict-item]
            # Simulate missing by making the internal bm25 object None
            idx._bm25 = None
            results = idx.search("authenticate", top_k=5)

        assert results == []
