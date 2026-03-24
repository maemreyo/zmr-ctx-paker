"""
Native LEANN vector index using the actual LEANN library.

LEANN (Low-Storage Vector Index) provides 97% storage savings compared to
traditional vector databases by using graph-based selective recomputation.

Reference: https://github.com/yichuan-w/LEANN
"""

import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..logger import get_logger
from ..models import CodeChunk
from .vector_index import VectorIndex


class NativeLEANNIndex(VectorIndex):
    """Native LEANN vector index with 97% storage savings.

    Uses the actual LEANN library which implements graph-based selective
    recomputation instead of storing all embeddings.

    Usage:
        pip install leann  # or: pip install ctx-packer[leann]

        index = NativeLEANNIndex(index_path="./leann_index")
        index.build(chunks)
        results = index.search("authentication logic", top_k=10)
    """

    def __init__(
        self,
        index_path: str = "./leann_index",
        backend: str = "hnsw",
        chunk_size: int = 256,
        overlap: int = 32,
    ):
        """Initialize Native LEANN index.

        Args:
            index_path: Base path for LEANN index (without extension).
                       LEANN will create .meta.json, .passages.jsonl, etc. alongside this.
            backend: Backend to use ('hnsw' or 'diskann')
            chunk_size: Token chunk size for text splitting
            overlap: Overlap between chunks

        Raises:
            ImportError: If leann library is not available
        """
        self.index_path = str(Path(index_path).resolve())
        self.backend = backend
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.logger = get_logger()

        self._builder = None
        self._searcher = None
        self._file_paths: List[str] = []
        self._file_symbols: Dict[str, List[str]] = {}
        self._chunk_to_file: Dict[int, str] = {}

        self._check_leann_available()

    def _check_leann_available(self) -> None:
        """Check if leann library is available.

        Raises:
            ImportError: If leann library is not available
        """
        try:
            from leann import LeannBuilder, LeannSearcher
        except ImportError:
            raise ImportError(
                "leann library not available. "
                "Install with: pip install leann or: pip install ctx-packer[leann]"
            )

    def build(self, chunks: List[CodeChunk]) -> None:
        """Build LEANN index from code chunks.

        Args:
            chunks: List of CodeChunk objects to index

        Raises:
            RuntimeError: If index building fails
        """
        if not chunks:
            raise ValueError("Cannot build index from empty chunks list")

        from leann import LeannBuilder

        self.logger.info(f"Building Native LEANN index from {len(chunks)} chunks")

        self._builder = LeannBuilder(backend_name=self.backend)

        self._file_paths = []
        self._file_symbols = {}
        self._chunk_to_file = {}

        file_to_chunks: Dict[str, List[CodeChunk]] = {}
        for i, chunk in enumerate(chunks):
            if chunk.path not in file_to_chunks:
                file_to_chunks[chunk.path] = []
            file_to_chunks[chunk.path].append(chunk)
            self._chunk_to_file[i] = chunk.path

        for file_path, file_chunks in file_to_chunks.items():
            self._file_paths.append(file_path)

            combined_content = "\n".join(chunk.content for chunk in file_chunks)

            self._builder.add_text(
                combined_content,
                metadata={
                    "path": file_path,
                    "num_chunks": len(file_chunks),
                }
            )

            symbols: List[str] = []
            for chunk in file_chunks:
                symbols.extend(chunk.symbols_defined)
            self._file_symbols[file_path] = symbols

        try:
            parent_dir = Path(self.index_path).parent
            parent_dir.mkdir(parents=True, exist_ok=True)
            self._builder.build_index(self.index_path)
            self.logger.info(
                f"Native LEANN index built successfully: {len(self._file_paths)} files"
            )
        except Exception as e:
            self.logger.error(f"Failed to build Native LEANN index: {e}")
            raise RuntimeError(f"Native LEANN index build failed: {e}")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search for relevant files using LEANN.

        Args:
            query: Natural language search query
            top_k: Number of results to return

        Returns:
            List of (file_path, similarity_score) tuples, ordered by descending similarity

        Raises:
            RuntimeError: If search fails
        """
        if not self._file_paths:
            raise RuntimeError("Index not built. Call build() first.")

        if not query:
            raise ValueError("Query cannot be empty")

        from leann import LeannSearcher

        try:
            self._searcher = LeannSearcher(self.index_path)
            results = self._searcher.search(query, top_k=top_k * 2)

            file_scores: Dict[str, float] = {}
            for result in results:
                metadata = result.metadata
                file_path = metadata.get('path', '') if isinstance(metadata, dict) else getattr(metadata, 'path', '')

                if file_path and file_path in self._file_paths:
                    score = float(getattr(result, 'score', 0.0))
                    if file_path not in file_scores or score > file_scores[file_path]:
                        file_scores[file_path] = score

            sorted_files = sorted(
                file_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]

            return sorted_files

        except Exception as e:
            self.logger.error(f"Native LEANN search failed: {e}")
            raise RuntimeError(f"Native LEANN search failed: {e}")

    def get_file_symbols(self) -> Dict[str, List[str]]:
        """Get mapping of file paths to symbols defined in those files."""
        return self._file_symbols

    def save(self, path: str) -> None:
        """Persist LEANN index metadata to disk.

        Note: LEANN index itself is already persisted at self.index_path.
        This saves only the metadata (file_paths, symbols mapping).

        Args:
            path: File path to save metadata
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)

            data = {
                'backend': 'NativeLEANNIndex',
                'index_path': self.index_path,
                'backend_name': self.backend,
                'chunk_size': self.chunk_size,
                'overlap': self.overlap,
                'file_paths': self._file_paths,
                'file_symbols': self._file_symbols,
            }

            with open(path, 'wb') as f:
                pickle.dump(data, f)

            self.logger.info(f"Native LEANN metadata saved to {path}")

        except Exception as e:
            self.logger.error(f"Failed to save Native LEANN metadata: {e}")
            raise IOError(f"Failed to save Native LEANN metadata: {e}")

    @classmethod
    def load(cls, path: str) -> 'NativeLEANNIndex':
        """Load Native LEANN index from disk.

        Args:
            path: File path to load metadata from

        Returns:
            Loaded NativeLEANNIndex instance

        Raises:
            IOError: If load fails
        """
        logger = get_logger()

        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)

            if data.get('backend') != 'NativeLEANNIndex':
                raise ValueError(
                    f"Invalid backend in saved index: {data.get('backend')}"
                )

            index = cls(
                index_path=data['index_path'],
                backend=data.get('backend_name', 'hnsw'),
                chunk_size=data.get('chunk_size', 256),
                overlap=data.get('overlap', 32),
            )

            index._file_paths = data['file_paths']
            index._file_symbols = data.get('file_symbols', {})

            logger.info(f"Native LEANN index loaded from {path}")
            return index

        except Exception as e:
            logger.error(f"Failed to load Native LEANN index: {e}")
            raise IOError(f"Failed to load Native LEANN index: {e}")


def create_native_leann_index(
    index_path: str = "./leann_index",
    backend: str = "hnsw",
    chunk_size: int = 256,
    overlap: int = 32,
) -> NativeLEANNIndex:
    """Create Native LEANN index.

    Args:
        index_path: Path to store/load the LEANN index
        backend: Backend to use ('hnsw' or 'diskann')
        chunk_size: Token chunk size for text splitting
        overlap: Overlap between chunks

    Returns:
        NativeLEANNIndex instance

    Raises:
        RuntimeError: If LEANN is not available or index creation fails
    """
    logger = get_logger()

    try:
        return NativeLEANNIndex(
            index_path=index_path,
            backend=backend,
            chunk_size=chunk_size,
            overlap=overlap,
        )
    except Exception as e:
        logger.error(f"Failed to create Native LEANN index: {e}")
        raise RuntimeError(f"Failed to create Native LEANN index: {e}")
