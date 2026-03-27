"""Cross-encoder reranker for improving top-N retrieval precision.

Uses a ``CrossEncoder`` model (default: ``BAAI/bge-reranker-v2-m3``) to score
each (query, chunk_content) pair and re-sort the candidate list.  This is an
optional post-processing step applied after the hybrid search.

Enable via environment variable::

    WSCTX_ENABLE_RERANKER=1

The CrossEncoder is loaded lazily on the **first call** to
:meth:`CrossEncoderReranker.rerank`, so construction is instantaneous and
startup time is unaffected when the feature is disabled.

If ``sentence-transformers`` is not installed or the model fails to load,
:meth:`rerank` falls back to returning the candidates in their original order
with uniform scores.
"""

import os
from typing import Any

from ..logger import get_logger

logger = get_logger()

_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class CrossEncoderReranker:
    """Reranks retrieval candidates using a cross-encoder model.

    Args:
        model_name: HuggingFace model ID for the cross-encoder.
        device: Target device (``"cpu"`` or ``"cuda"``).

    .. warning:: **License notice for alternative models**

        The default model ``BAAI/bge-reranker-v2-m3`` is licensed under
        **Apache 2.0** and is safe for commercial use.

        ``jinaai/jina-reranker-v3`` (and ``v2``) are licensed under
        **CC BY-NC 4.0** — non-commercial use only.  For production /
        commercial deployments either:

        1. Obtain a commercial licence from Jina AI, or
        2. Use ``BAAI/bge-reranker-v2-m3`` (the default) instead.
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._model: Any = None
        self._load_attempted: bool = False
        # Model is NOT loaded here — loading is deferred to the first rerank() call.

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_enabled() -> bool:
        """Return True when ``WSCTX_ENABLE_RERANKER=1`` is set."""
        return os.environ.get("WSCTX_ENABLE_RERANKER", "").strip() == "1"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rerank(
        self,
        query: str,
        candidates: list[tuple[str, str]],
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Rerank *candidates* using the cross-encoder model.

        Args:
            query: The search query string.
            candidates: List of ``(file_path, content_text)`` pairs to rerank.
            top_k: Maximum number of results to return.

        Returns:
            List of ``(file_path, normalised_score)`` tuples sorted by score
            descending, with scores in ``[0, 1]``.  If the model is unavailable
            the original order is returned with uniform score ``1.0``.
        """
        if not candidates:
            return []

        # Lazy-load on first use (only attempt once to avoid repeated I/O on failure)
        if self._model is None and not self._load_attempted:
            self._try_load()

        if self._model is None:
            # Model unavailable — fall back to input order, uniform scores
            return [(path, 1.0) for path, _ in candidates[:top_k]]

        pairs = [[query, content] for _, content in candidates]
        raw = self._model.predict(pairs)
        raw_scores: list[float] = raw.tolist() if hasattr(raw, "tolist") else list(raw)

        # Min-max normalise to [0, 1]
        min_s = min(raw_scores)
        max_s = max(raw_scores)
        if max_s > min_s:
            norm = [(s - min_s) / (max_s - min_s) for s in raw_scores]
        else:
            norm = [1.0] * len(raw_scores)

        ranked = sorted(
            zip([p for p, _ in candidates], norm),
            key=lambda x: x[1],
            reverse=True,
        )
        return list(ranked[:top_k])

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _try_load(self) -> None:
        self._load_attempted = True
        try:
            from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]

            logger.info(f"[Reranker] Loading model={self.model_name} device={self.device}")
            self._model = CrossEncoder(self.model_name, device=self.device)
            logger.info(f"[Reranker] Model loaded: {self.model_name}")
        except ImportError:
            logger.warning("[Reranker] sentence-transformers not installed — reranker disabled")
        except Exception as e:
            logger.warning(f"[Reranker] Failed to load {self.model_name!r}: {e}")
