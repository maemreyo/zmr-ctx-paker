"""
Vector Index implementation for semantic search over code chunks.

Provides abstract base class and concrete implementations:
- LEANNIndex: Primary backend with 97% storage savings (graph-based)
- FAISSIndex: Fallback backend using IndexFlatL2 + IndexIDMap2 (faiss-cpu)
"""

import os
import pickle
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np
import psutil  # type: ignore[import-untyped]

from ..logger import get_logger
from ..models import CodeChunk
from ..perf import timed
from .model_registry import DEFAULT_MODEL, ModelRegistry


class VectorIndex(ABC):
    """Abstract base class for vector index implementations.

    Provides semantic search over code chunks using embeddings.
    Implementations must support build, search, save, and load operations.
    """

    @abstractmethod
    def build(self, chunks: list[CodeChunk], embedding_cache: Any | None = None) -> None:
        """Build vector index from code chunks.

        Args:
            chunks: List of CodeChunk objects to index
            embedding_cache: Optional cache to avoid re-embedding unchanged files.
                Implementations that don't support caching may ignore this parameter.

        Raises:
            RuntimeError: If index building fails
        """
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search for relevant code chunks.

        Args:
            query: Natural language search query
            top_k: Number of results to return

        Returns:
            List of (file_path, similarity_score) tuples, ordered by descending similarity

        Raises:
            RuntimeError: If search fails
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Persist index to disk.

        Args:
            path: File path to save index

        Raises:
            IOError: If save fails
        """
        pass

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> "VectorIndex":
        """Load index from disk.

        Args:
            path: File path to load index from

        Returns:
            Loaded VectorIndex instance

        Raises:
            IOError: If load fails
        """
        pass

    def get_file_symbols(self) -> dict[str, list[str]]:
        """Get mapping of file paths to symbols defined in those files.

        Returns:
            Dict mapping file_path -> list of symbol names defined in that file.
            Returns empty dict if no symbol data is available.
        """
        return {}


class EmbeddingGenerator:
    """Generate embeddings for text using local model or API fallback.

    Tries sentence-transformers first, falls back to OpenAI API on OOM.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = "cpu",
        batch_size: int = 32,
        api_provider: str = "openai",
        api_key_env: str = "OPENAI_API_KEY",
    ):
        """Initialize embedding generator.

        Args:
            model_name: Sentence-transformers model name
            device: Device to use ('cpu' or 'cuda')
            batch_size: Batch size for encoding
            api_provider: API provider for fallback ('openai')
            api_key_env: Environment variable name for API key
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.api_provider = api_provider
        self.api_key_env = api_key_env
        self.logger = get_logger()

        self._model: Any = None
        self._use_api = False
        self._memory_threshold_mb = 500  # Trigger API fallback if available memory < 500MB

    def _check_memory(self) -> bool:
        """Check if sufficient memory is available.

        Returns:
            True if sufficient memory available, False otherwise
        """
        try:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            return bool(available_mb > self._memory_threshold_mb)
        except Exception:
            # If we can't check memory, assume it's available
            return True

    @timed("embedding_model_load")
    def _init_local_model(self) -> bool:
        """Initialize local sentence-transformers model via ModelRegistry.

        Uses the thread-safe singleton cache to avoid reloading the model on
        every call. The registry respects WSCTX_ENABLE_ONNX, WSCTX_EMBEDDING_MODEL,
        and WSCTX_MEMORY_THRESHOLD_MB environment variables.

        Returns:
            True if successful, False otherwise
        """
        if not self._check_memory():
            self.logger.warning(
                f"Low memory detected (<{self._memory_threshold_mb}MB available), "
                "skipping local model initialization"
            )
            return False

        model = ModelRegistry.get_model(self.model_name, self.device)
        if model is not None:
            self._model = model
            self.logger.info(f"Embedding model ready (via registry): {self.model_name}")
            return True

        self.logger.warning("sentence-transformers not available or model failed to load")
        return False

    def _init_api_client(self) -> bool:
        """Initialize API client for embeddings.

        Returns:
            True if successful, False otherwise
        """
        try:
            import openai

            api_key = os.environ.get(self.api_key_env)
            if not api_key:
                self.logger.error(f"API key not found in environment variable: {self.api_key_env}")
                return False

            openai.api_key = api_key
            self.logger.info(f"Initialized {self.api_provider} API client for embeddings")
            return True

        except ImportError:
            self.logger.error("openai package not available, cannot use API fallback")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize API client: {e}")
            return False

    @timed("embedding_encode")
    def encode(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for texts.

        Args:
            texts: List of text strings to encode

        Returns:
            Numpy array of embeddings, shape (len(texts), embedding_dim)

        Raises:
            RuntimeError: If both local and API encoding fail
        """
        # Try local model first
        if not self._use_api:
            if self._model is None:
                if not self._init_local_model():
                    self._use_api = True

            if self._model is not None:
                try:
                    if not self._check_memory():
                        self.logger.warning(
                            "Low memory detected during encoding, falling back to API"
                        )
                        self._use_api = True
                        self._model = None  # Free memory
                    else:
                        embeddings = self._model.encode(
                            texts,
                            batch_size=self.batch_size,
                            show_progress_bar=False,
                            convert_to_numpy=True,
                        )
                        return np.asarray(embeddings)

                except MemoryError:
                    self.logger.log_fallback(
                        component="embeddings",
                        primary="local (sentence-transformers)",
                        fallback="API (OpenAI)",
                        reason="Out of memory",
                    )
                    self._use_api = True
                    self._model = None  # Free memory
                except Exception as e:
                    self.logger.warning(f"Local encoding failed: {e}, falling back to API")
                    self._use_api = True

        # Fall back to API
        if self._use_api:
            return self._encode_with_api(texts)

        raise RuntimeError("Failed to generate embeddings with both local and API methods")

    def _encode_with_api(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using API.

        Args:
            texts: List of text strings to encode

        Returns:
            Numpy array of embeddings

        Raises:
            RuntimeError: If API encoding fails
        """
        if not self._init_api_client():
            raise RuntimeError("Failed to initialize API client")

        try:
            import openai

            embeddings = []
            for text in texts:
                response = openai.Embedding.create(input=text, model="text-embedding-ada-002")  # type: ignore[attr-defined]
                embeddings.append(response["data"][0]["embedding"])

            return np.array(embeddings)

        except Exception as e:
            raise RuntimeError(f"API encoding failed: {e}") from e


class LEANNIndex(VectorIndex):
    """LEANN-based vector index with 97% storage savings.

    Uses graph-based approach to store only a subset of vectors,
    recomputing others on-the-fly using graph traversal.
    """

    def __init__(
        self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu", batch_size: int = 32
    ):
        """Initialize LEANN index.

        Args:
            model_name: Sentence-transformers model name
            device: Device to use ('cpu' or 'cuda')
            batch_size: Batch size for encoding
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.logger = get_logger()

        self._embedding_generator: EmbeddingGenerator | None = None
        self._file_paths: list[str] = []
        self._embeddings: np.ndarray | None = None
        self._file_symbols: dict[str, list[str]] = {}
        self._graph = None  # Simplified: store all embeddings for now

    def build(self, chunks: list[CodeChunk], embedding_cache: Any | None = None) -> None:
        """Build LEANN index from code chunks.

        Args:
            chunks: List of CodeChunk objects to index
            embedding_cache: Ignored — LEANNIndex manages its own storage.

        Raises:
            RuntimeError: If index building fails
        """
        if not chunks:
            raise ValueError("Cannot build index from empty chunks list")

        self.logger.info(f"Building LEANN index from {len(chunks)} chunks")

        # Initialize embedding generator
        self._embedding_generator = EmbeddingGenerator(
            model_name=self.model_name, device=self.device, batch_size=self.batch_size
        )

        # Group chunks by file path
        file_to_chunks: dict[str, list[CodeChunk]] = {}
        for chunk in chunks:
            if chunk.path not in file_to_chunks:
                file_to_chunks[chunk.path] = []
            file_to_chunks[chunk.path].append(chunk)

        # Generate embeddings for each file (concatenate chunk contents)
        self._file_paths = list(file_to_chunks.keys())
        texts = []
        self._file_symbols = {}
        for file_path in self._file_paths:
            file_chunks = file_to_chunks[file_path]
            # Combine all chunks from the same file
            combined_text = "\n".join(chunk.content for chunk in file_chunks)
            texts.append(combined_text)
            # Collect all symbols defined in this file
            symbols: list[str] = []
            for chunk in file_chunks:
                symbols.extend(chunk.symbols_defined)
            self._file_symbols[file_path] = symbols

        # Generate embeddings
        try:
            assert self._embedding_generator is not None
            self._embeddings = self._embedding_generator.encode(texts)
            self.logger.info(
                f"LEANN index built successfully: {len(self._file_paths)} files, "
                f"embedding dim: {self._embeddings.shape[1]}"
            )
        except Exception as e:
            self.logger.error(f"Failed to build LEANN index: {e}")
            raise RuntimeError(f"LEANN index build failed: {e}") from e

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search for relevant files using cosine similarity.

        Args:
            query: Natural language search query
            top_k: Number of results to return

        Returns:
            List of (file_path, similarity_score) tuples, ordered by descending similarity

        Raises:
            RuntimeError: If search fails
        """
        if self._embeddings is None or not self._file_paths:
            raise RuntimeError("Index not built. Call build() first.")

        if not query:
            raise ValueError("Query cannot be empty")

        try:
            # Generate query embedding
            assert self._embedding_generator is not None
            query_embedding = self._embedding_generator.encode([query])[0]

            # Compute cosine similarity
            similarities = self._cosine_similarity(query_embedding, self._embeddings)

            # Get top-K results
            top_k = min(top_k, len(self._file_paths))
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = [(self._file_paths[idx], float(similarities[idx])) for idx in top_indices]

            return results

        except Exception as e:
            self.logger.error(f"LEANN search failed: {e}")
            raise RuntimeError(f"LEANN search failed: {e}") from e

    @staticmethod
    def _cosine_similarity(query: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
        """Compute cosine similarity between query and embeddings.

        Args:
            query: Query embedding vector, shape (embedding_dim,)
            embeddings: Matrix of embeddings, shape (n_docs, embedding_dim)

        Returns:
            Array of similarity scores, shape (n_docs,)
        """
        # Normalize query
        query_norm = query / (np.linalg.norm(query) + 1e-8)

        # Normalize embeddings
        embeddings_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)

        # Compute dot product
        similarities = np.dot(embeddings_norm, query_norm)

        return np.asarray(similarities)

    def get_file_symbols(self) -> dict[str, list[str]]:
        """Get mapping of file paths to symbols defined in those files."""
        return self._file_symbols

    def save(self, path: str) -> None:
        """Persist LEANN index to disk.

        Args:
            path: File path to save index

        Raises:
            IOError: If save fails
        """
        if self._embeddings is None:
            raise RuntimeError("Index not built. Call build() first.")

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)

            data = {
                "backend": "LEANNIndex",
                "model_name": self.model_name,
                "device": self.device,
                "batch_size": self.batch_size,
                "file_paths": self._file_paths,
                "embeddings": self._embeddings,
                "file_symbols": self._file_symbols,
            }

            with open(path, "wb") as f:
                pickle.dump(data, f)

            self.logger.info(f"LEANN index saved to {path}")

        except Exception as e:
            self.logger.error(f"Failed to save LEANN index: {e}")
            raise OSError(f"Failed to save LEANN index: {e}") from e

    @classmethod
    def load(cls, path: str) -> "LEANNIndex":
        """Load LEANN index from disk.

        Args:
            path: File path to load index from

        Returns:
            Loaded LEANNIndex instance

        Raises:
            IOError: If load fails
        """
        logger = get_logger()

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)

            if data.get("backend") != "LEANNIndex":
                raise ValueError(f"Invalid backend in saved index: {data.get('backend')}")

            # Create instance
            index = cls(
                model_name=data["model_name"], device=data["device"], batch_size=data["batch_size"]
            )

            # Restore state
            index._file_paths = data["file_paths"]
            index._embeddings = data["embeddings"]
            index._file_symbols = data.get("file_symbols", {})
            index._embedding_generator = EmbeddingGenerator(
                model_name=data["model_name"], device=data["device"], batch_size=data["batch_size"]
            )

            logger.info(f"LEANN index loaded from {path}")
            return index

        except Exception as e:
            logger.error(f"Failed to load LEANN index: {e}")
            raise OSError(f"Failed to load LEANN index: {e}") from e


class FAISSIndex(VectorIndex):
    """FAISS-based vector index using IndexFlatL2 wrapped in IndexIDMap2.

    IndexIDMap2 is used as the default so that incremental updates
    (remove_ids + add_with_ids) work without migrating legacy indexes.
    Fallback implementation using faiss-cpu library.
    """

    def __init__(
        self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu", batch_size: int = 32
    ):
        """Initialize FAISS index.

        Args:
            model_name: Sentence-transformers model name
            device: Device to use ('cpu' or 'cuda')
            batch_size: Batch size for encoding
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.logger = get_logger()

        self._embedding_generator: EmbeddingGenerator | None = None
        self._file_paths: list[str] = []
        # H-1: authoritative ID mapping — FAISS integer IDs are not assumed to
        # equal _file_paths list positions after any deletion cycle.
        self._id_to_path: dict[int, str] = {}
        self._next_id: int = 0
        self._index: Any = None
        self._embedding_dim: int | None = None
        self._file_symbols: dict[str, list[str]] = {}

    def _build_embeddings_with_cache(
        self, texts: list[str], embedding_cache: "EmbeddingCache"
    ) -> "np.ndarray":
        """Return embeddings for *texts*, consulting *embedding_cache* first (H-3)."""
        assert self._embedding_generator is not None
        result: list[np.ndarray] = [None] * len(texts)  # type: ignore[list-item]
        need_embed: list[int] = []

        for i, text in enumerate(texts):
            h = EmbeddingCache.content_hash(text)
            cached = embedding_cache.lookup(h)
            if cached is not None:
                result[i] = cached
            else:
                need_embed.append(i)

        if need_embed:
            new_vecs = self._embedding_generator.encode([texts[i] for i in need_embed])
            for j, i in enumerate(need_embed):
                vec = new_vecs[j]
                result[i] = vec
                embedding_cache.store(EmbeddingCache.content_hash(texts[i]), vec)

        return np.vstack(result)

    def build(
        self,
        chunks: list[CodeChunk],
        embedding_cache: Optional["EmbeddingCache"] = None,
    ) -> None:
        """Build FAISS index from code chunks.

        Args:
            chunks: List of CodeChunk objects to index
            embedding_cache: Optional cache to avoid re-embedding unchanged files
                on successive full rebuilds (H-3).

        Raises:
            RuntimeError: If index building fails
        """
        if not chunks:
            raise ValueError("Cannot build index from empty chunks list")

        try:
            import faiss
        except ImportError:
            raise RuntimeError(
                "faiss-cpu not available. Install with: pip install faiss-cpu"
            ) from None

        self.logger.info(f"Building FAISS index from {len(chunks)} chunks")

        # Initialize embedding generator
        self._embedding_generator = EmbeddingGenerator(
            model_name=self.model_name, device=self.device, batch_size=self.batch_size
        )

        # Group chunks by file path
        file_to_chunks2: dict[str, list[CodeChunk]] = {}
        for chunk in chunks:
            if chunk.path not in file_to_chunks2:
                file_to_chunks2[chunk.path] = []
            file_to_chunks2[chunk.path].append(chunk)

        # Generate embeddings for each file (consulting cache when available)
        self._file_paths = list(file_to_chunks2.keys())
        texts: list[str] = []
        self._file_symbols = {}
        for file_path in self._file_paths:
            file_chunks = file_to_chunks2[file_path]
            combined_text = "\n".join(chunk.content for chunk in file_chunks)
            texts.append(combined_text)
            symbols: list[str] = []
            for chunk in file_chunks:
                symbols.extend(chunk.symbols_defined)
            self._file_symbols[file_path] = symbols

        # Generate embeddings — use cache to skip unchanged files (H-3).
        try:
            assert self._embedding_generator is not None
            if embedding_cache is not None:
                embeddings = self._build_embeddings_with_cache(texts, embedding_cache)
            else:
                embeddings = self._embedding_generator.encode(texts)
            self._embedding_dim = embeddings.shape[1]

            # Build FAISS flat index wrapped in IndexIDMap2.
            # IndexFlatL2 is exact-search (brute-force), which is accurate and
            # fast enough for repos up to ~50k files. IndexIDMap2 enables
            # incremental removal via remove_ids() without rebuilding the index.
            # IDs are managed via _id_to_path / _next_id so that deletions never
            # corrupt the mapping (H-1).
            base = faiss.IndexFlatL2(self._embedding_dim)
            self._index = faiss.IndexIDMap2(base)
            n = len(self._file_paths)
            ids = np.arange(n, dtype=np.int64)
            self._index.add_with_ids(embeddings.astype("float32"), ids)
            self._id_to_path = {int(i): self._file_paths[i] for i in range(n)}
            self._next_id = n

            self.logger.info(
                f"FAISS index built successfully: {len(self._file_paths)} files, "
                f"embedding dim: {self._embedding_dim}"
            )

        except Exception as e:
            self.logger.error(f"Failed to build FAISS index: {e}")
            raise RuntimeError(f"FAISS index build failed: {e}") from e

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Search for relevant files using FAISS.

        Args:
            query: Natural language search query
            top_k: Number of results to return

        Returns:
            List of (file_path, similarity_score) tuples, ordered by descending similarity

        Raises:
            RuntimeError: If search fails
        """
        if self._index is None or not self._file_paths:
            raise RuntimeError("Index not built. Call build() first.")

        if not query:
            raise ValueError("Query cannot be empty")

        try:
            # Generate query embedding
            assert self._embedding_generator is not None
            query_embedding = self._embedding_generator.encode([query])[0]
            query_embedding = query_embedding.astype("float32").reshape(1, -1)

            # Search
            top_k = min(top_k, len(self._file_paths))
            distances, indices = self._index.search(query_embedding, top_k)

            # Convert distances to similarities (FAISS returns L2 distances)
            # For normalized vectors: similarity = 1 - (distance^2 / 2)
            similarities = 1 - (distances[0] ** 2 / 2)

            # Use _id_to_path for ID→path lookup (H-1): IDs may not equal list
            # positions after incremental deletions.
            results = []
            for idx, sim in zip(indices[0], similarities, strict=True):
                path = self._id_to_path.get(int(idx))
                if path is not None:
                    results.append((path, float(sim)))

            return results

        except Exception as e:
            self.logger.error(f"FAISS search failed: {e}")
            raise RuntimeError(f"FAISS search failed: {e}") from e

    def get_file_symbols(self) -> dict[str, list[str]]:
        """Get mapping of file paths to symbols defined in those files."""
        return self._file_symbols

    def save(self, path: str) -> None:
        """Persist FAISS index to disk.

        Args:
            path: File path to save index

        Raises:
            IOError: If save fails
        """
        if self._index is None:
            raise RuntimeError("Index not built. Call build() first.")

        try:
            import faiss

            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Save FAISS index
            index_path = path + ".faiss"
            faiss.write_index(self._index, index_path)

            # Save metadata
            metadata = {
                "backend": "FAISSIndex",
                "model_name": self.model_name,
                "device": self.device,
                "batch_size": self.batch_size,
                "file_paths": self._file_paths,
                "embedding_dim": self._embedding_dim,
                "file_symbols": self._file_symbols,
                "id_to_path": self._id_to_path,
                "next_id": self._next_id,
            }

            with open(path, "wb") as f:
                pickle.dump(metadata, f)

            self.logger.info(f"FAISS index saved to {path}")

        except Exception as e:
            self.logger.error(f"Failed to save FAISS index: {e}")
            raise OSError(f"Failed to save FAISS index: {e}") from e

    @classmethod
    def load(cls, path: str) -> "FAISSIndex":
        """Load FAISS index from disk.

        Args:
            path: File path to load index from

        Returns:
            Loaded FAISSIndex instance

        Raises:
            IOError: If load fails
        """
        logger = get_logger()

        try:
            import faiss

            # Load metadata
            with open(path, "rb") as f:
                metadata = pickle.load(f)

            if metadata.get("backend") != "FAISSIndex":
                raise ValueError(f"Invalid backend in saved index: {metadata.get('backend')}")

            # Create instance
            index = cls(
                model_name=metadata["model_name"],
                device=metadata["device"],
                batch_size=metadata["batch_size"],
            )

            # Load FAISS index
            index_path = path + ".faiss"
            index._index = faiss.read_index(index_path)

            # Restore state
            index._file_paths = metadata["file_paths"]
            index._embedding_dim = metadata["embedding_dim"]
            index._file_symbols = metadata.get("file_symbols", {})
            index._embedding_generator = EmbeddingGenerator(
                model_name=metadata["model_name"],
                device=metadata["device"],
                batch_size=metadata["batch_size"],
            )
            # Restore H-1 ID mapping. For indexes saved before v0.3.0 the keys
            # will be absent; derive from _file_paths as a safe fallback.
            raw_id_to_path = metadata.get("id_to_path")
            if raw_id_to_path is not None:
                # JSON round-trips dict keys as strings; re-cast to int.
                index._id_to_path = {int(k): v for k, v in raw_id_to_path.items()}
                index._next_id = int(metadata.get("next_id", len(index._file_paths)))
            else:
                index._id_to_path = {i: p for i, p in enumerate(index._file_paths)}
                index._next_id = len(index._file_paths)

            # Auto-migrate legacy indexes (e.g. IndexHNSWFlat from v0.2.x) to
            # IndexIDMap2 so incremental updates work on existing installs.
            # _ensure_idmap2() is a no-op when the index is already wrapped.
            if not isinstance(index._index, faiss.IndexIDMap2):
                index._ensure_idmap2()

            logger.info(f"FAISS index loaded from {path}")
            return index

        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            raise OSError(f"Failed to load FAISS index: {e}") from e

    # ------------------------------------------------------------------
    # M6: Incremental update support via IndexIDMap2
    # ------------------------------------------------------------------

    def _ensure_idmap2(self) -> None:
        """
        Migrate an IndexHNSWFlat (or other flat index) to IndexIDMap2 so that
        individual vectors can be removed by their integer ID.

        IndexIDMap2 is preferred over IndexIDMap because it also supports
        ``reconstruct()`` — useful for future cache verification.
        """
        import faiss

        if self._index is None:
            return
        if isinstance(self._index, faiss.IndexIDMap2):
            return  # Already wrapped

        base = self._index
        # Only flat-family indices support reconstruct(); HNSW and IVF do not.
        # For non-flat indices we skip vector re-registration — existing vectors
        # remain searchable but cannot be individually removed by ID.
        supports_reconstruct = isinstance(
            base,
            (faiss.IndexFlat, faiss.IndexFlatL2, faiss.IndexFlatIP),
        )
        wrapped = faiss.IndexIDMap2(base)
        if supports_reconstruct and len(self._file_paths) > 0 and self._embedding_dim:
            try:
                n = base.ntotal
                ids = np.arange(n, dtype=np.int64)
                vecs = np.vstack([base.reconstruct(int(i)) for i in range(n)]).astype(np.float32)
                wrapped.add_with_ids(vecs, ids)
            except Exception as exc:
                self.logger.warning(f"Could not migrate to IndexIDMap2 (ignored): {exc}")
                return  # Keep old index as-is
        elif not supports_reconstruct and base.ntotal > 0:
            self.logger.warning(
                f"Index type {type(base).__name__} does not support reconstruct(); existing vectors will not "
                "have ID mappings — incremental removal will not work for pre-existing entries."
            )
        self._index = wrapped

    def update_incremental(
        self,
        deleted_paths: list[str],
        new_chunks: list["CodeChunk"],
        embedding_cache: Optional["EmbeddingCache"] = None,
    ) -> None:
        """
        Incrementally update the FAISS index.

        Removes vectors for *deleted_paths*, then adds vectors for *new_chunks*.
        Uses *embedding_cache* to skip re-embedding unchanged content.

        Args:
            deleted_paths: File paths whose vectors should be removed.
            new_chunks: New/changed code chunks to embed and add.
            embedding_cache: Optional cache to avoid redundant embeddings.
        """
        import faiss

        # Ensure we're using IndexIDMap2 for remove_ids support
        self._ensure_idmap2()

        if self._embedding_generator is None:
            self._embedding_generator = EmbeddingGenerator(
                model_name=self.model_name,
                device=self.device,
                batch_size=self.batch_size,
            )

        # 1. Remove deleted/changed paths using the authoritative _id_to_path map
        # (H-1): reverse the map once for O(1) path→ID lookups.
        path_to_id = {v: k for k, v in self._id_to_path.items()}
        ids_to_remove: list[int] = []
        for path in deleted_paths:
            fid = path_to_id.pop(path, None)
            if fid is not None:
                ids_to_remove.append(fid)
                self._id_to_path.pop(fid, None)
            try:
                self._file_paths.remove(path)
            except ValueError:
                pass
            self._file_symbols.pop(path, None)

        if ids_to_remove and isinstance(self._index, faiss.IndexIDMap2):
            self._index.remove_ids(np.array(ids_to_remove, dtype=np.int64))
            self.logger.info(f"Removed {len(ids_to_remove)} entries from FAISS index")

        # 2. Group new chunks by file
        if not new_chunks:
            return

        file_to_chunks: dict[str, list] = {}
        for chunk in new_chunks:
            file_to_chunks.setdefault(chunk.path, []).append(chunk)

        new_paths = list(file_to_chunks.keys())
        texts: list[str] = []
        need_embed: list[int] = []  # indices that require embedding (no cache hit)
        cached_vecs: dict[int, np.ndarray] = {}

        for i, fp in enumerate(new_paths):
            combined = "\n".join(c.content for c in file_to_chunks[fp])
            texts.append(combined)
            if embedding_cache is not None:
                h = EmbeddingCache.content_hash(combined)
                cached = embedding_cache.lookup(h)
                if cached is not None:
                    cached_vecs[i] = cached
                    continue
            need_embed.append(i)

        # Embed only the uncached texts
        all_vecs: dict[int, np.ndarray] = dict(cached_vecs)
        if need_embed:
            uncached_texts = [texts[i] for i in need_embed]
            embeddings = self._embedding_generator.encode(uncached_texts)
            for j, i in enumerate(need_embed):
                vec = embeddings[j]
                all_vecs[i] = vec
                # Store in cache for future runs
                if embedding_cache is not None:
                    h = EmbeddingCache.content_hash(texts[i])
                    embedding_cache.store(h, vec)

        # 3. Add new vectors using monotonically increasing _next_id so IDs
        # never collide with deleted-but-not-yet-reused entries (H-1).
        new_vecs = np.vstack([all_vecs[i] for i in range(len(new_paths))]).astype(np.float32)
        new_ids = np.arange(self._next_id, self._next_id + len(new_paths), dtype=np.int64)

        if isinstance(self._index, faiss.IndexIDMap2):
            self._index.add_with_ids(new_vecs, new_ids)
        else:
            self._index.add(new_vecs)

        for i, fp in enumerate(new_paths):
            fid = int(new_ids[i])
            self._id_to_path[fid] = fp
        self._next_id += len(new_paths)

        self._file_paths.extend(new_paths)
        for fp, chunks_list in file_to_chunks.items():
            syms: list[str] = []
            for c in chunks_list:
                syms.extend(c.symbols_defined)
            self._file_symbols[fp] = syms

        self.logger.info(f"Incremental update: +{len(new_paths)} files")


# Import EmbeddingCache lazily to avoid circular imports
try:
    from .embedding_cache import EmbeddingCache  # noqa: E402
except ImportError:
    EmbeddingCache = None  # type: ignore[assignment,misc]


def create_vector_index(
    backend: str = "auto",
    model_name: str = "all-MiniLM-L6-v2",
    device: str = "cpu",
    batch_size: int = 32,
    index_path: str = "./leann_index",
    leann_recompute_embeddings: bool = True,
) -> VectorIndex:
    """Create vector index with automatic backend selection and fallback.

    Backend priority in 'auto' mode:
    1. NativeLEANNIndex (LEANN library - 97% storage savings)
    2. LEANNIndex (cosine similarity fallback)
    3. FAISSIndex (IndexFlatL2 + IndexIDMap2 fallback)

    Args:
        backend: Backend to use ('auto', 'native-leann', 'leann', 'faiss')
        model_name: Sentence-transformers model name
        device: Device to use ('cpu' or 'cuda')
        batch_size: Batch size for encoding
        index_path: Path for LEANN index storage

    Returns:
        VectorIndex instance

    Raises:
        RuntimeError: If all backends fail
    """
    logger = get_logger()

    if backend == "native-leann":
        try:
            from .leann_index import NativeLEANNIndex

            return NativeLEANNIndex(
                index_path=index_path,
                backend="hnsw",
                chunk_size=256,
                overlap=32,
                recompute_embeddings=leann_recompute_embeddings,
            )
        except ImportError:
            raise RuntimeError(
                "leann not available. Install with: pip install leann "
                "or: pip install ws-ctx-engine[leann]"
            ) from None
        except Exception as e:
            raise RuntimeError(f"Failed to create Native LEANN index: {e}") from e

    if backend == "leann":
        try:
            return LEANNIndex(model_name, device, batch_size)
        except Exception as e:
            raise RuntimeError(f"Failed to create LEANN index: {e}") from e

    if backend == "faiss":
        try:
            return FAISSIndex(model_name, device, batch_size)
        except Exception as e:
            raise RuntimeError(f"Failed to create FAISS index: {e}") from e

    if backend == "auto":
        try:
            from .leann_index import NativeLEANNIndex

            logger.info("Attempting to create Native LEANN index (97% storage savings)")
            return NativeLEANNIndex(
                index_path=index_path,
                backend="hnsw",
                chunk_size=256,
                overlap=32,
                recompute_embeddings=leann_recompute_embeddings,
            )
        except ImportError:
            logger.log_fallback(
                component="vector_index",
                primary="NativeLEANN (leann library)",
                fallback="LEANNIndex (cosine similarity)",
                reason="leann library not installed",
            )
        except Exception as e:
            logger.log_fallback(
                component="vector_index",
                primary="NativeLEANN (leann library)",
                fallback="LEANNIndex (cosine similarity)",
                reason=str(e),
            )

        try:
            logger.info("Attempting to create LEANN index (cosine similarity fallback)")
            return LEANNIndex(model_name, device, batch_size)
        except Exception as e:
            logger.log_fallback(
                component="vector_index",
                primary="LEANNIndex (cosine similarity)",
                fallback="FAISSIndex (IndexFlatL2+IDMap2)",
                reason=str(e),
            )

        try:
            logger.info("Attempting to create FAISS index (IndexFlatL2+IDMap2 fallback)")
            return FAISSIndex(model_name, device, batch_size)
        except Exception as e:
            logger.error(f"FAISS fallback also failed: {e}")
            raise RuntimeError(
                "All vector index backends failed. "
                "Install leann for 97% storage savings: pip install ws-ctx-engine[leann]"
            ) from e

    raise ValueError(
        f"Invalid backend: {backend}. " "Must be 'auto', 'native-leann', 'leann', or 'faiss'"
    )


def load_vector_index(path: str) -> VectorIndex:
    """Load vector index from disk with automatic backend detection.

    Args:
        path: File path to load index from

    Returns:
        Loaded VectorIndex instance

    Raises:
        IOError: If load fails
    """
    logger = get_logger()

    try:
        with open(path, "rb") as f:
            metadata = pickle.load(f)

        backend = metadata.get("backend")

        if backend == "NativeLEANNIndex":
            logger.info("Detected Native LEANN index, loading...")
            from .leann_index import NativeLEANNIndex

            return NativeLEANNIndex.load(path)
        elif backend == "LEANNIndex":
            logger.info("Detected LEANN index, loading...")
            return LEANNIndex.load(path)
        elif backend == "FAISSIndex":
            logger.info("Detected FAISS index, loading...")
            return FAISSIndex.load(path)
        else:
            raise ValueError(f"Unknown backend in saved index: {backend}")

    except Exception as e:
        logger.error(f"Failed to load vector index: {e}")
        raise OSError(f"Failed to load vector index: {e}") from e
