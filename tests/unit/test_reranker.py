"""Tests for ws_ctx_engine.retrieval.reranker (Phase 4 — TDD-first).

Covers:
- CrossEncoderReranker.rerank() correct ordering
- Scores normalised to [0, 1]
- top_k truncation
- CrossEncoder unavailable → returns input order unchanged
- Env-var WSCTX_ENABLE_RERANKER guards
- Integration: RetrievalEngine applies reranker when enabled
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.retrieval.reranker import CrossEncoderReranker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CANDIDATES = [
    ("src/auth.py", "def authenticate(user, password): return check(user, password)"),
    ("src/session.py", "def create_session(user): return token(user)"),
    ("src/database.py", "def query_db(sql): return cursor.execute(sql)"),
    ("src/utils.py", "def hash_password(pw): return sha256(pw)"),
]


def _make_reranker(scores: list[float]) -> CrossEncoderReranker:
    """Return a CrossEncoderReranker with a mocked CrossEncoder."""
    reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
    mock_model = MagicMock()
    mock_model.predict.return_value = scores
    reranker._model = mock_model
    reranker._load_attempted = True  # model is already "loaded"
    reranker.model_name = "BAAI/bge-reranker-v2-m3"
    reranker.device = "cpu"
    return reranker


# ---------------------------------------------------------------------------
# CrossEncoderReranker.rerank()
# ---------------------------------------------------------------------------


class TestCrossEncoderRerankerRerank:
    def test_returns_list_of_tuples(self) -> None:
        reranker = _make_reranker([0.9, 0.3, 0.1, 0.5])
        results = reranker.rerank("authenticate user", CANDIDATES, top_k=4)
        assert isinstance(results, list)
        for item in results:
            assert len(item) == 2

    def test_results_sorted_by_score_descending(self) -> None:
        reranker = _make_reranker([0.9, 0.3, 0.1, 0.5])
        results = reranker.rerank("authenticate", CANDIDATES, top_k=4)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_limits_results(self) -> None:
        reranker = _make_reranker([0.9, 0.3, 0.1, 0.5])
        results = reranker.rerank("authenticate", CANDIDATES, top_k=2)
        assert len(results) == 2

    def test_highest_scoring_doc_ranked_first(self) -> None:
        """Mock model gives auth.py score 0.9 — it must be first."""
        reranker = _make_reranker([0.9, 0.3, 0.1, 0.5])
        results = reranker.rerank("authenticate", CANDIDATES, top_k=4)
        assert results[0][0] == "src/auth.py"

    def test_scores_normalised_to_0_1(self) -> None:
        reranker = _make_reranker([5.0, -1.0, 2.0, 0.0])
        results = reranker.rerank("query", CANDIDATES, top_k=4)
        for _, score in results:
            assert 0.0 <= score <= 1.0 + 1e-9

    def test_empty_candidates_returns_empty(self) -> None:
        reranker = _make_reranker([])
        results = reranker.rerank("query", [], top_k=5)
        assert results == []

    def test_single_candidate_returns_score_1(self) -> None:
        reranker = _make_reranker([3.7])
        results = reranker.rerank("query", CANDIDATES[:1], top_k=1)
        assert len(results) == 1
        assert abs(results[0][1] - 1.0) < 1e-9

    def test_cross_encoder_called_with_query_content_pairs(self) -> None:
        """predict() must receive list of [query, content] pairs."""
        reranker = _make_reranker([0.9, 0.3, 0.1, 0.5])
        reranker.rerank("my query", CANDIDATES, top_k=4)

        call_args = reranker._model.predict.call_args[0][0]
        assert len(call_args) == len(CANDIDATES)
        for pair in call_args:
            assert pair[0] == "my query"

    def test_paths_preserved_in_output(self) -> None:
        reranker = _make_reranker([0.1, 0.2, 0.8, 0.5])
        results = reranker.rerank("query", CANDIDATES, top_k=4)
        output_paths = {p for p, _ in results}
        input_paths = {p for p, _ in CANDIDATES}
        assert output_paths == input_paths


# ---------------------------------------------------------------------------
# CrossEncoder unavailable — graceful fallback
# ---------------------------------------------------------------------------


class TestCrossEncoderUnavailable:
    def _unavailable_reranker(self) -> CrossEncoderReranker:
        """Build a CrossEncoderReranker that simulates a failed model load."""
        reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
        reranker._model = None
        reranker._load_attempted = True  # prevent lazy re-load in rerank()
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.device = "cpu"
        return reranker

    def test_rerank_returns_input_order_when_model_none(self) -> None:
        """If _model is None (import failed), preserve input order."""
        reranker = self._unavailable_reranker()
        results = reranker.rerank("authenticate", CANDIDATES, top_k=4)
        output_paths = [p for p, _ in results]
        input_paths = [p for p, _ in CANDIDATES]
        assert output_paths == input_paths[:4]

    def test_rerank_scores_are_uniform_when_model_none(self) -> None:
        reranker = self._unavailable_reranker()
        results = reranker.rerank("query", CANDIDATES[:2], top_k=2)
        scores = {s for _, s in results}
        # All scores equal when falling back
        assert len(scores) == 1


# ---------------------------------------------------------------------------
# WSCTX_ENABLE_RERANKER env-var
# ---------------------------------------------------------------------------


class TestEnvVarBehaviour:
    def test_is_enabled_returns_true_when_env_set(self) -> None:
        with patch.dict(os.environ, {"WSCTX_ENABLE_RERANKER": "1"}):
            assert CrossEncoderReranker.is_enabled()

    def test_is_enabled_returns_false_by_default(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "WSCTX_ENABLE_RERANKER"}
        with patch.dict(os.environ, env, clear=True):
            assert not CrossEncoderReranker.is_enabled()

    def test_is_enabled_false_for_zero(self) -> None:
        with patch.dict(os.environ, {"WSCTX_ENABLE_RERANKER": "0"}):
            assert not CrossEncoderReranker.is_enabled()


# ---------------------------------------------------------------------------
# Integration: RetrievalEngine applies reranker
# ---------------------------------------------------------------------------


class TestRetrievalEngineRerankerIntegration:
    def _make_engine_with_content(self, reranker: CrossEncoderReranker | None = None):
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        mock_vector = MagicMock()
        mock_vector.search.return_value = [
            ("src/auth.py", 0.9),
            ("src/session.py", 0.5),
            ("src/utils.py", 0.3),
        ]
        mock_vector.get_file_symbols.return_value = {}

        mock_graph = MagicMock()
        mock_graph.pagerank.return_value = {
            "src/auth.py": 0.6,
            "src/session.py": 0.3,
            "src/utils.py": 0.1,
        }

        content_map = {
            "src/auth.py": "def authenticate(user, password): ...",
            "src/session.py": "def create_session(user): ...",
            "src/utils.py": "def hash_password(pw): ...",
        }

        return RetrievalEngine(
            vector_index=mock_vector,
            graph=mock_graph,
            content_map=content_map,
            reranker=reranker,
        )

    def test_engine_accepts_reranker_param(self) -> None:
        mock_reranker = MagicMock(spec=CrossEncoderReranker)
        mock_reranker.rerank.return_value = [("src/auth.py", 1.0), ("src/session.py", 0.5)]
        engine = self._make_engine_with_content(reranker=mock_reranker)
        assert engine.reranker is mock_reranker

    def test_engine_calls_reranker_when_provided(self) -> None:
        mock_reranker = MagicMock(spec=CrossEncoderReranker)
        mock_reranker.rerank.return_value = [
            ("src/auth.py", 1.0),
            ("src/session.py", 0.5),
        ]
        engine = self._make_engine_with_content(reranker=mock_reranker)
        engine.retrieve(query="authenticate user", top_k=5)

        mock_reranker.rerank.assert_called_once()

    def test_engine_works_without_reranker(self) -> None:
        engine = self._make_engine_with_content(reranker=None)
        results = engine.retrieve(query="authenticate", top_k=5)
        assert isinstance(results, list)

    def test_reranker_receives_content_not_path_only(self) -> None:
        """rerank() must be called with (path, content) pairs, not (path, score)."""
        captured: list = []

        def fake_rerank(query, candidates, top_k):
            captured.extend(candidates)
            return [(p, 1.0) for p, _ in candidates[:top_k]]

        mock_reranker = MagicMock(spec=CrossEncoderReranker)
        mock_reranker.rerank.side_effect = fake_rerank

        engine = self._make_engine_with_content(reranker=mock_reranker)
        engine.retrieve(query="authenticate", top_k=5)

        # Each candidate must be a (path, text_content) pair — not a float score
        for path, content in captured:
            assert isinstance(content, str), f"Expected str content, got {type(content)}"
            assert not content.replace(".", "").isdigit(), "Content looks like a score, not text"
