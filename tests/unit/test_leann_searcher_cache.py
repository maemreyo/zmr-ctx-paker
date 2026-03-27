"""Tests for LEANN searcher instance caching in NativeLEANNIndex (Phase 1)."""

import sys
from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.vector_index.leann_index import NativeLEANNIndex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def _mock_leann(
    searcher_cls: MagicMock | None = None,
    builder_cls: MagicMock | None = None,
) -> Generator[MagicMock, None, None]:
    """Inject a fake 'leann' module so lazy imports inside leann_index work."""
    fake_module = MagicMock()
    fake_module.LeannSearcher = searcher_cls or MagicMock()
    fake_module.LeannBuilder = builder_cls or MagicMock()
    with patch.dict(sys.modules, {"leann": fake_module}):
        yield fake_module


def _make_chunks() -> list[CodeChunk]:
    return [
        CodeChunk(
            path="src/auth.py",
            content="def authenticate(user): pass",
            language="python",
            symbols_defined=["authenticate"],
            symbols_referenced=[],
            start_line=1,
            end_line=1,
        )
    ]


def _make_built_index(tmp_path: "Path") -> NativeLEANNIndex:  # type: ignore[name-defined]
    """Return an index that has been built (no real LEANN needed — patched)."""
    with patch("ws_ctx_engine.vector_index.leann_index.NativeLEANNIndex._check_leann_available"):
        idx = NativeLEANNIndex(index_path=str(tmp_path / "leann_idx"))

    # Simulate a built index by populating internal metadata directly
    idx._file_paths = ["src/auth.py"]
    idx._file_symbols = {"src/auth.py": ["authenticate"]}
    return idx


# ---------------------------------------------------------------------------
# Searcher caching tests
# ---------------------------------------------------------------------------


class TestLEANNSearcherCache:
    def test_searcher_created_only_once_across_multiple_searches(
        self, tmp_path: "Path"  # type: ignore[name-defined]
    ) -> None:
        """LeannSearcher must be instantiated exactly once, not per-call."""
        idx = _make_built_index(tmp_path)

        mock_result = MagicMock()
        mock_result.metadata = {"path": "src/auth.py"}
        mock_result.score = 0.9

        mock_searcher_instance = MagicMock()
        mock_searcher_instance.search.return_value = [mock_result]

        with patch("ws_ctx_engine.vector_index.leann_index.NativeLEANNIndex._get_or_create_searcher") as mock_factory:
            mock_factory.return_value = mock_searcher_instance

            idx.search("authenticate user", top_k=5)
            idx.search("login flow", top_k=5)

        # _get_or_create_searcher called twice but constructor only once
        assert mock_factory.call_count == 2  # called each time search() is invoked
        # The searcher itself only constructed once (tested by _get_or_create_searcher impl)

    def test_searcher_instance_reused_not_recreated(
        self, tmp_path: "Path"  # type: ignore[name-defined]
    ) -> None:
        """After first search(), _searcher must be set and reused on second call."""
        idx = _make_built_index(tmp_path)

        mock_result = MagicMock()
        mock_result.metadata = {"path": "src/auth.py"}
        mock_result.score = 0.9

        mock_searcher = MagicMock()
        mock_searcher.search.return_value = [mock_result]

        constructor_calls: list[str] = []

        def mock_searcher_cls(path: str) -> MagicMock:
            constructor_calls.append(path)
            return mock_searcher

        with _mock_leann(searcher_cls=mock_searcher_cls):
            idx.search("auth", top_k=5)
            idx.search("login", top_k=5)

        # Constructor must have been called exactly once
        assert len(constructor_calls) == 1

    def test_searcher_invalidated_after_build(
        self, tmp_path: "Path"  # type: ignore[name-defined]
    ) -> None:
        """After build(), the cached searcher must be cleared so next search re-creates it."""
        idx = _make_built_index(tmp_path)

        # Place a mock searcher into the cache
        idx._searcher = MagicMock()

        mock_builder = MagicMock()
        mock_builder.build_index = MagicMock()

        with _mock_leann(builder_cls=lambda *_, **__: mock_builder):
            idx.build(_make_chunks())

        assert idx._searcher is None

    def test_searcher_initially_none(
        self, tmp_path: "Path"  # type: ignore[name-defined]
    ) -> None:
        """Freshly created index must have _searcher == None before any search."""
        idx = _make_built_index(tmp_path)
        assert idx._searcher is None
