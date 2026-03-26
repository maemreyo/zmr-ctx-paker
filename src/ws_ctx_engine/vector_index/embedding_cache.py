"""
Embedding cache for incremental indexing.

Persists content-hash → embedding vector mappings so that unchanged files
do not need to be re-embedded on incremental index rebuilds.

Storage layout under .ws-ctx-engine/
    embeddings.npy          — numpy array of shape (N, embedding_dim)
    embedding_index.json    — {"hash_to_idx": {"<sha256>": <row_index>, ...}}

The hash used is SHA-256 of the concatenated file content for all chunks
belonging to a file.  This guarantees that any content change invalidates
the cache entry.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("ws_ctx_engine")


class EmbeddingCache:
    """
    Disk-backed content-hash → embedding vector cache.

    Usage::

        cache = EmbeddingCache(cache_dir=Path(".ws-ctx-engine"))
        cache.load()

        for text, existing in zip(texts, cache.lookup_many(hashes)):
            if existing is None:
                vec = model.encode(text)
                cache.store(hash_, vec)
        cache.save()
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._embeddings_path = cache_dir / "embeddings.npy"
        self._index_path = cache_dir / "embedding_index.json"
        self._hash_to_idx: Dict[str, int] = {}
        self._vectors: Optional[np.ndarray] = None  # shape (N, dim)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load cache from disk.  No-op if files don't exist yet."""
        try:
            self._hash_to_idx = json.loads(
                self._index_path.read_text(encoding="utf-8")
            ).get("hash_to_idx", {})
            if self._embeddings_path.exists():
                self._vectors = np.load(str(self._embeddings_path))
                logger.info(f"Embedding cache loaded: {len(self._hash_to_idx)} entries")
            else:
                self._vectors = None
        except (FileNotFoundError, json.JSONDecodeError, Exception) as exc:
            logger.warning(f"Could not load embedding cache: {exc}")
            self._hash_to_idx = {}
            self._vectors = None

    def save(self) -> None:
        """Persist current cache to disk."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._index_path.write_text(
                json.dumps({"hash_to_idx": self._hash_to_idx}, ensure_ascii=False),
                encoding="utf-8",
            )
            if self._vectors is not None:
                np.save(str(self._embeddings_path), self._vectors)
            logger.info(f"Embedding cache saved: {len(self._hash_to_idx)} entries")
        except Exception as exc:
            logger.warning(f"Could not save embedding cache: {exc}")

    # ------------------------------------------------------------------
    # Lookup / store
    # ------------------------------------------------------------------

    def lookup(self, content_hash: str) -> Optional[np.ndarray]:
        """Return cached vector for *content_hash*, or None if not found."""
        idx = self._hash_to_idx.get(content_hash)
        if idx is None or self._vectors is None:
            return None
        if idx >= len(self._vectors):
            return None
        return self._vectors[idx]

    def store(self, content_hash: str, vector: np.ndarray) -> None:
        """Add or update the cached vector for *content_hash*."""
        if content_hash in self._hash_to_idx:
            idx = self._hash_to_idx[content_hash]
            if self._vectors is not None and idx < len(self._vectors):
                self._vectors[idx] = vector
                return

        # Append a new row
        vec2d = vector.reshape(1, -1)
        if self._vectors is None:
            self._vectors = vec2d
        else:
            self._vectors = np.vstack([self._vectors, vec2d])
        self._hash_to_idx[content_hash] = len(self._vectors) - 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def content_hash(text: str) -> str:
        """SHA-256 hex digest of *text*."""
        return hashlib.sha256(text.encode()).hexdigest()

    @property
    def size(self) -> int:
        return len(self._hash_to_idx)
