"""BM25 index over CodeChunk content for keyword-based retrieval.

Wraps ``rank-bm25`` (BM25Okapi) and exposes a simple build/search interface
that mirrors the VectorIndex API so the two are interchangeable in the hybrid
engine.

If ``rank-bm25`` is not installed, :meth:`BM25Index.search` returns an empty
list instead of raising, preserving the graceful-degradation contract used
throughout the codebase.
"""

import pickle
from pathlib import Path
from typing import Any

from ..models import CodeChunk
from .code_tokenizer import tokenize_code, tokenize_query



class BM25Index:
    """BM25Okapi index over a corpus of :class:`CodeChunk` objects.

    Usage::

        idx = BM25Index()
        idx.build(chunks)
        results = idx.search("authenticate user", top_k=10)
        # → [("src/auth.py", 0.92), ("src/session.py", 0.41), ...]
    """

    def __init__(self) -> None:
        self._bm25: Any = None
        self._paths: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of documents currently indexed."""
        return len(self._paths)

    def build(self, chunks: list[CodeChunk]) -> None:
        """Build (or rebuild) the BM25 index from *chunks*.

        Tokenises each chunk's content and feeds the token lists to
        ``BM25Okapi``.  Any previously built index is discarded.

        Args:
            chunks: List of code chunks to index.
        """
        if not chunks:
            self._bm25 = None
            self._paths = []
            return

        try:
            from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]
        except ImportError:
            self._bm25 = None
            self._paths = [c.path for c in chunks]
            return

        corpus: list[list[str]] = []
        self._paths = []
        for chunk in chunks:
            tokens = tokenize_code(chunk.content)
            corpus.append(tokens if tokens else [""])
            self._paths.append(chunk.path)

        self._bm25 = BM25Okapi(corpus)

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Return the top-*k* chunks most relevant to *query*.

        Args:
            query: Natural language or code query string.
            top_k: Maximum number of results to return.

        Returns:
            List of ``(file_path, bm25_score)`` tuples sorted by score
            descending.  Returns ``[]`` if the index is empty or
            ``rank-bm25`` is unavailable.
        """
        if self._bm25 is None or not self._paths:
            return []

        tokens = tokenize_query(query)
        if not tokens:
            return []

        scores: list[float] = self._bm25.get_scores(tokens).tolist()

        # Pair with paths, sort, deduplicate by path (keep highest score)
        path_score: dict[str, float] = {}
        for path, score in zip(self._paths, scores):
            if score > path_score.get(path, -1.0):
                path_score[path] = score

        ranked = sorted(path_score.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialise the index to *path* using pickle.

        Args:
            path: Destination file path (created along with any missing parents).
        """
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            pickle.dump({"bm25": self._bm25, "paths": self._paths}, f)

    @classmethod
    def load(cls, path: str) -> "BM25Index":
        """Load a previously saved index from *path*.

        Args:
            path: Source file path produced by :meth:`save`.

        Returns:
            Populated :class:`BM25Index` instance.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)
        idx = cls()
        idx._bm25 = data.get("bm25")
        idx._paths = data.get("paths", [])
        return idx
