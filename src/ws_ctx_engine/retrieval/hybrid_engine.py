"""Hybrid search engine combining vector and BM25 results via Reciprocal Rank Fusion.

Reciprocal Rank Fusion (RRF) formula (Cormack et al. 2009)::

    score(d) = Σ  1 / (k + rank_i(d))

where *k* = 60 (standard constant that dampens the influence of very high
ranks) and the sum is taken over each result list *i* that contains document
*d*.  Final scores are min-max normalised to ``[0, 1]``.

Usage::

    engine = HybridSearchEngine(vector_index=vi, bm25_index=bm25)
    results = engine.search("authenticate user session", top_k=20)
    # → [("src/auth.py", 1.0), ("src/session.py", 0.82), ...]
"""

from typing import Any

_RRF_K = 60  # Standard constant — empirically optimal across many benchmarks


def rrf_score(rank: int, k: int = _RRF_K) -> float:
    """Return the RRF contribution for a document at *rank* (1-indexed).

    Args:
        rank: 1-indexed position in a ranked list.
        k: Smoothing constant (default 60).

    Returns:
        ``1 / (k + rank)``
    """
    return 1.0 / (k + rank)


class HybridSearchEngine:
    """Fuses vector-search and BM25 ranked lists with Reciprocal Rank Fusion.

    Args:
        vector_index: Any object with ``search(query, top_k) → list[(path, score)]``.
        bm25_index: Any object with ``search(query, top_k) → list[(path, score)]``.
        rrf_k: RRF smoothing constant (default 60).
    """

    def __init__(
        self,
        vector_index: Any,
        bm25_index: Any,
        rrf_k: int = _RRF_K,
    ) -> None:
        self.vector_index = vector_index
        self.bm25_index = bm25_index
        self._rrf_k = rrf_k

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Run hybrid search and return top-*k* results.

        Fetches ``top_k * 3`` candidates from each source (to ensure good
        coverage before fusion), applies RRF, normalises scores, and returns
        the final top-*k* list sorted descending.

        Args:
            query: Natural language or code query string.
            top_k: Maximum number of results to return.

        Returns:
            List of ``(file_path, normalised_score)`` tuples sorted by score
            descending with scores in ``[0, 1]``.
        """
        fetch_k = max(top_k * 3, 50)

        vec_results: list[tuple[str, float]] = self.vector_index.search(query, fetch_k)
        bm25_results: list[tuple[str, float]] = self.bm25_index.search(query, fetch_k)

        rrf_scores: dict[str, float] = {}

        for rank, (path, _) in enumerate(vec_results, start=1):
            rrf_scores[path] = rrf_scores.get(path, 0.0) + rrf_score(rank, self._rrf_k)

        for rank, (path, _) in enumerate(bm25_results, start=1):
            rrf_scores[path] = rrf_scores.get(path, 0.0) + rrf_score(rank, self._rrf_k)

        if not rrf_scores:
            return []

        # Min-max normalise to [0, 1]
        min_s = min(rrf_scores.values())
        max_s = max(rrf_scores.values())
        if max_s > min_s:
            normalised = {p: (s - min_s) / (max_s - min_s) for p, s in rrf_scores.items()}
        else:
            normalised = {p: 1.0 for p in rrf_scores}

        ranked = sorted(normalised.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
