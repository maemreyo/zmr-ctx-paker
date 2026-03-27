"""
ContextAssembler — merges vector retrieval results with GraphStore query results.

The assembler is a pure score-merger. It does NOT call BudgetManager — that
stays downstream in query.py. The output replaces the ranked_files list before
budget selection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .signal_router import GraphIntent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssemblyResult:
    """Frozen result of graph-augmented assembly."""

    ranked_files: list[tuple[str, float]]
    graph_augmented: bool
    graph_files_added: int


class ContextAssembler:
    """
    Merges chunk-RAG (vector) results with graph-RAG results.

    Graph files not already in the vector result set are inserted with a
    score of ``max_vector_score * graph_query_weight``.  Files that appear
    in both retain their existing (higher) vector score.  The final list is
    returned sorted descending by score.

    Degrades gracefully: any exception or unhealthy store returns the
    original vector results unchanged.
    """

    def __init__(self, graph_store: Any, graph_query_weight: float = 0.3) -> None:
        self._store = graph_store
        self._weight = graph_query_weight

    def assemble(
        self,
        vector_results: list[tuple[str, float]],
        intent: GraphIntent,
    ) -> AssemblyResult:
        """
        Merge vector retrieval results with graph query results.

        Args:
            vector_results: List of (file_path, score) from vector retrieval.
            intent: Classified query intent from ``classify_graph_intent()``.

        Returns:
            AssemblyResult with the merged ranked list and augmentation metadata.
        """
        # Fast-path: no graph involvement needed
        if intent.intent_type == "none":
            return AssemblyResult(
                ranked_files=vector_results,
                graph_augmented=False,
                graph_files_added=0,
            )

        if not self._store.is_healthy:
            return AssemblyResult(
                ranked_files=vector_results,
                graph_augmented=False,
                graph_files_added=0,
            )

        try:
            return self._merge(vector_results, intent)
        except Exception as exc:
            logger.warning("ContextAssembler.assemble failed (returning vector only): %s", exc)
            return AssemblyResult(
                ranked_files=vector_results,
                graph_augmented=False,
                graph_files_added=0,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge(
        self,
        vector_results: list[tuple[str, float]],
        intent: GraphIntent,
    ) -> AssemblyResult:
        graph_paths = self._fetch_graph_paths(intent)

        if not graph_paths:
            return AssemblyResult(
                ranked_files=vector_results,
                graph_augmented=False,
                graph_files_added=0,
            )

        # Build a dict for O(1) lookup of existing vector scores
        existing: dict[str, float] = {path: score for path, score in vector_results}

        max_score: float = max((s for _, s in vector_results), default=1.0)
        graph_score = max_score * self._weight

        new_files: list[tuple[str, float]] = []
        for path in graph_paths:
            if path not in existing:
                new_files.append((path, graph_score))

        if not new_files:
            # All graph files were already in the vector result — no net addition
            return AssemblyResult(
                ranked_files=vector_results,
                graph_augmented=False,
                graph_files_added=0,
            )

        merged = list(vector_results) + new_files
        merged.sort(key=lambda t: t[1], reverse=True)

        return AssemblyResult(
            ranked_files=merged,
            graph_augmented=True,
            graph_files_added=len(new_files),
        )

    def _fetch_graph_paths(self, intent: GraphIntent) -> list[str]:
        """Dispatch to the correct GraphStore method and normalise the result."""
        if intent.intent_type == "callers_of":
            rows = self._store.callers_of(intent.target)
            return self._extract_paths_from_caller_rows(rows)

        if intent.intent_type == "impact_of":
            result = self._store.impact_of(intent.target)
            # impact_of returns list[str] directly per the GraphStore contract
            if isinstance(result, list):
                return [str(r) for r in result if isinstance(r, str)]
            return []

        return []

    @staticmethod
    def _extract_paths_from_caller_rows(rows: list[Any]) -> list[str]:
        """
        Normalise callers_of() rows → plain file-path strings.

        GraphStore returns ``list[dict]`` with a ``caller_file`` key.
        Robustly falls back to first dict value if the key is absent.
        """
        paths: list[str] = []
        for row in rows:
            if isinstance(row, dict):
                if "caller_file" in row:
                    paths.append(str(row["caller_file"]))
                else:
                    first = next(iter(row.values()), None)
                    if first is not None:
                        paths.append(str(first))
            elif isinstance(row, str):
                paths.append(row)
        return paths
