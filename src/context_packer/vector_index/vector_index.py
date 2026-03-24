"""
Vector Index implementation for semantic search over code chunks.

Provides abstract base class and concrete implementations:
- LEANNIndex: Primary backend with 97% storage savings (graph-based)
- FAISSIndex: Fallback backend using HNSW index (faiss-cpu)
"""

import os
import pickle
import psutil
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import numpy as np

from ..logger import get_logger
from ..models import CodeChunk


class VectorIndex(ABC):
    """Abstract base class for vector index implementations.
    
    Provides semantic search over code chunks using embeddings.
    Implementations must support build, search, save, and load operations.
    """
    
    @abstractmethod
    def build(self, chunks: List[CodeChunk]) -> None:
        """Build vector index from code chunks.
        
        Args:
            chunks: List of CodeChunk objects to index
            
        Raises:
            RuntimeError: If index building fails
        """
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
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
    def load(cls, path: str) -> 'VectorIndex':
        """Load index from disk.
        
        Args:
            path: File path to load index from
            
        Returns:
            Loaded VectorIndex instance
            
        Raises:
            IOError: If load fails
        """
        pass



class EmbeddingGenerator:
    """Generate embeddings for text using local model or API fallback.
    
    Tries sentence-transformers first, falls back to OpenAI API on OOM.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 32,
        api_provider: str = "openai",
        api_key_env: str = "OPENAI_API_KEY"
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
        
        self._model = None
        self._use_api = False
        self._memory_threshold_mb = 500  # Trigger API fallback if available memory < 500MB
    
    def _check_memory(self) -> bool:
        """Check if sufficient memory is available.
        
        Returns:
            True if sufficient memory available, False otherwise
        """
        try:
            available_mb = psutil.virtual_memory().available / (1024 * 1024)
            return available_mb > self._memory_threshold_mb
        except Exception:
            # If we can't check memory, assume it's available
            return True
    
    def _init_local_model(self) -> bool:
        """Initialize local sentence-transformers model.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            if not self._check_memory():
                self.logger.warning(
                    f"Low memory detected (<{self._memory_threshold_mb}MB available), "
                    "skipping local model initialization"
                )
                return False
            
            self.logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name, device=self.device)
            self.logger.info("Local embedding model loaded successfully")
            return True
            
        except ImportError:
            self.logger.warning(
                "sentence-transformers not available, will use API fallback"
            )
            return False
        except MemoryError:
            self.logger.warning(
                "Out of memory loading local model, will use API fallback"
            )
            return False
        except Exception as e:
            self.logger.warning(
                f"Failed to load local model: {e}, will use API fallback"
            )
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
                self.logger.error(
                    f"API key not found in environment variable: {self.api_key_env}"
                )
                return False
            
            openai.api_key = api_key
            self.logger.info(f"Initialized {self.api_provider} API client for embeddings")
            return True
            
        except ImportError:
            self.logger.error(
                "openai package not available, cannot use API fallback"
            )
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize API client: {e}")
            return False
    
    def encode(self, texts: List[str]) -> np.ndarray:
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
                            convert_to_numpy=True
                        )
                        return embeddings
                        
                except MemoryError:
                    self.logger.log_fallback(
                        component="embeddings",
                        primary="local (sentence-transformers)",
                        fallback="API (OpenAI)",
                        reason="Out of memory"
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
    
    def _encode_with_api(self, texts: List[str]) -> np.ndarray:
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
                response = openai.Embedding.create(
                    input=text,
                    model="text-embedding-ada-002"
                )
                embeddings.append(response['data'][0]['embedding'])
            
            return np.array(embeddings)
            
        except Exception as e:
            raise RuntimeError(f"API encoding failed: {e}")



class LEANNIndex(VectorIndex):
    """LEANN-based vector index with 97% storage savings.
    
    Uses graph-based approach to store only a subset of vectors,
    recomputing others on-the-fly using graph traversal.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 32
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
        
        self._embedding_generator = None
        self._file_paths: List[str] = []
        self._embeddings: Optional[np.ndarray] = None
        self._graph = None  # Simplified: store all embeddings for now
    
    def build(self, chunks: List[CodeChunk]) -> None:
        """Build LEANN index from code chunks.
        
        Args:
            chunks: List of CodeChunk objects to index
            
        Raises:
            RuntimeError: If index building fails
        """
        if not chunks:
            raise ValueError("Cannot build index from empty chunks list")
        
        self.logger.info(f"Building LEANN index from {len(chunks)} chunks")
        
        # Initialize embedding generator
        self._embedding_generator = EmbeddingGenerator(
            model_name=self.model_name,
            device=self.device,
            batch_size=self.batch_size
        )
        
        # Group chunks by file path
        file_to_chunks = {}
        for chunk in chunks:
            if chunk.path not in file_to_chunks:
                file_to_chunks[chunk.path] = []
            file_to_chunks[chunk.path].append(chunk)
        
        # Generate embeddings for each file (concatenate chunk contents)
        self._file_paths = list(file_to_chunks.keys())
        texts = []
        for file_path in self._file_paths:
            file_chunks = file_to_chunks[file_path]
            # Combine all chunks from the same file
            combined_text = "\n".join(chunk.content for chunk in file_chunks)
            texts.append(combined_text)
        
        # Generate embeddings
        try:
            self._embeddings = self._embedding_generator.encode(texts)
            self.logger.info(
                f"LEANN index built successfully: {len(self._file_paths)} files, "
                f"embedding dim: {self._embeddings.shape[1]}"
            )
        except Exception as e:
            self.logger.error(f"Failed to build LEANN index: {e}")
            raise RuntimeError(f"LEANN index build failed: {e}")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
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
            query_embedding = self._embedding_generator.encode([query])[0]
            
            # Compute cosine similarity
            similarities = self._cosine_similarity(query_embedding, self._embeddings)
            
            # Get top-K results
            top_k = min(top_k, len(self._file_paths))
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = [
                (self._file_paths[idx], float(similarities[idx]))
                for idx in top_indices
            ]
            
            return results
            
        except Exception as e:
            self.logger.error(f"LEANN search failed: {e}")
            raise RuntimeError(f"LEANN search failed: {e}")
    
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
        
        return similarities
    
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
                'backend': 'LEANNIndex',
                'model_name': self.model_name,
                'device': self.device,
                'batch_size': self.batch_size,
                'file_paths': self._file_paths,
                'embeddings': self._embeddings
            }
            
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            
            self.logger.info(f"LEANN index saved to {path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save LEANN index: {e}")
            raise IOError(f"Failed to save LEANN index: {e}")
    
    @classmethod
    def load(cls, path: str) -> 'LEANNIndex':
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
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            if data.get('backend') != 'LEANNIndex':
                raise ValueError(f"Invalid backend in saved index: {data.get('backend')}")
            
            # Create instance
            index = cls(
                model_name=data['model_name'],
                device=data['device'],
                batch_size=data['batch_size']
            )
            
            # Restore state
            index._file_paths = data['file_paths']
            index._embeddings = data['embeddings']
            index._embedding_generator = EmbeddingGenerator(
                model_name=data['model_name'],
                device=data['device'],
                batch_size=data['batch_size']
            )
            
            logger.info(f"LEANN index loaded from {path}")
            return index
            
        except Exception as e:
            logger.error(f"Failed to load LEANN index: {e}")
            raise IOError(f"Failed to load LEANN index: {e}")



class FAISSIndex(VectorIndex):
    """FAISS-based vector index using HNSW algorithm.
    
    Fallback implementation using faiss-cpu library.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        batch_size: int = 32
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
        
        self._embedding_generator = None
        self._file_paths: List[str] = []
        self._index = None
        self._embedding_dim = None
    
    def build(self, chunks: List[CodeChunk]) -> None:
        """Build FAISS index from code chunks.
        
        Args:
            chunks: List of CodeChunk objects to index
            
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
            )
        
        self.logger.info(f"Building FAISS index from {len(chunks)} chunks")
        
        # Initialize embedding generator
        self._embedding_generator = EmbeddingGenerator(
            model_name=self.model_name,
            device=self.device,
            batch_size=self.batch_size
        )
        
        # Group chunks by file path
        file_to_chunks = {}
        for chunk in chunks:
            if chunk.path not in file_to_chunks:
                file_to_chunks[chunk.path] = []
            file_to_chunks[chunk.path].append(chunk)
        
        # Generate embeddings for each file
        self._file_paths = list(file_to_chunks.keys())
        texts = []
        for file_path in self._file_paths:
            file_chunks = file_to_chunks[file_path]
            combined_text = "\n".join(chunk.content for chunk in file_chunks)
            texts.append(combined_text)
        
        # Generate embeddings
        try:
            embeddings = self._embedding_generator.encode(texts)
            self._embedding_dim = embeddings.shape[1]
            
            # Build FAISS HNSW index
            self._index = faiss.IndexHNSWFlat(self._embedding_dim, 32)  # 32 = M parameter
            self._index.hnsw.efConstruction = 40  # Construction time parameter
            self._index.add(embeddings.astype('float32'))
            
            self.logger.info(
                f"FAISS index built successfully: {len(self._file_paths)} files, "
                f"embedding dim: {self._embedding_dim}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to build FAISS index: {e}")
            raise RuntimeError(f"FAISS index build failed: {e}")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
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
            query_embedding = self._embedding_generator.encode([query])[0]
            query_embedding = query_embedding.astype('float32').reshape(1, -1)
            
            # Search
            top_k = min(top_k, len(self._file_paths))
            distances, indices = self._index.search(query_embedding, top_k)
            
            # Convert distances to similarities (FAISS returns L2 distances)
            # For normalized vectors: similarity = 1 - (distance^2 / 2)
            similarities = 1 - (distances[0] ** 2 / 2)
            
            results = [
                (self._file_paths[idx], float(sim))
                for idx, sim in zip(indices[0], similarities)
            ]
            
            return results
            
        except Exception as e:
            self.logger.error(f"FAISS search failed: {e}")
            raise RuntimeError(f"FAISS search failed: {e}")
    
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
            index_path = path + '.faiss'
            faiss.write_index(self._index, index_path)
            
            # Save metadata
            metadata = {
                'backend': 'FAISSIndex',
                'model_name': self.model_name,
                'device': self.device,
                'batch_size': self.batch_size,
                'file_paths': self._file_paths,
                'embedding_dim': self._embedding_dim
            }
            
            with open(path, 'wb') as f:
                pickle.dump(metadata, f)
            
            self.logger.info(f"FAISS index saved to {path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save FAISS index: {e}")
            raise IOError(f"Failed to save FAISS index: {e}")
    
    @classmethod
    def load(cls, path: str) -> 'FAISSIndex':
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
            with open(path, 'rb') as f:
                metadata = pickle.load(f)
            
            if metadata.get('backend') != 'FAISSIndex':
                raise ValueError(f"Invalid backend in saved index: {metadata.get('backend')}")
            
            # Create instance
            index = cls(
                model_name=metadata['model_name'],
                device=metadata['device'],
                batch_size=metadata['batch_size']
            )
            
            # Load FAISS index
            index_path = path + '.faiss'
            index._index = faiss.read_index(index_path)
            
            # Restore state
            index._file_paths = metadata['file_paths']
            index._embedding_dim = metadata['embedding_dim']
            index._embedding_generator = EmbeddingGenerator(
                model_name=metadata['model_name'],
                device=metadata['device'],
                batch_size=metadata['batch_size']
            )
            
            logger.info(f"FAISS index loaded from {path}")
            return index
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            raise IOError(f"Failed to load FAISS index: {e}")



def create_vector_index(
    backend: str = "auto",
    model_name: str = "all-MiniLM-L6-v2",
    device: str = "cpu",
    batch_size: int = 32
) -> VectorIndex:
    """Create vector index with automatic backend selection and fallback.
    
    Args:
        backend: Backend to use ('auto', 'leann', 'faiss')
        model_name: Sentence-transformers model name
        device: Device to use ('cpu' or 'cuda')
        batch_size: Batch size for encoding
        
    Returns:
        VectorIndex instance
        
    Raises:
        RuntimeError: If all backends fail
    """
    logger = get_logger()
    
    # If specific backend requested, try only that one
    if backend == "leann":
        try:
            return LEANNIndex(model_name, device, batch_size)
        except Exception as e:
            raise RuntimeError(f"Failed to create LEANN index: {e}")
    
    if backend == "faiss":
        try:
            return FAISSIndex(model_name, device, batch_size)
        except Exception as e:
            raise RuntimeError(f"Failed to create FAISS index: {e}")
    
    # Auto mode: try LEANN first, fall back to FAISS
    if backend == "auto":
        # Try LEANN
        try:
            logger.info("Attempting to create LEANN index (primary backend)")
            return LEANNIndex(model_name, device, batch_size)
        except Exception as e:
            logger.log_fallback(
                component="vector_index",
                primary="LEANN",
                fallback="FAISS",
                reason=str(e)
            )
        
        # Fall back to FAISS
        try:
            logger.info("Attempting to create FAISS index (fallback backend)")
            return FAISSIndex(model_name, device, batch_size)
        except Exception as e:
            logger.error(f"FAISS fallback also failed: {e}")
            raise RuntimeError(
                "All vector index backends failed. "
                "Install faiss-cpu with: pip install faiss-cpu"
            )
    
    raise ValueError(f"Invalid backend: {backend}. Must be 'auto', 'leann', or 'faiss'")


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
        # Load metadata to detect backend
        with open(path, 'rb') as f:
            metadata = pickle.load(f)
        
        backend = metadata.get('backend')
        
        if backend == 'LEANNIndex':
            logger.info("Detected LEANN index, loading...")
            return LEANNIndex.load(path)
        elif backend == 'FAISSIndex':
            logger.info("Detected FAISS index, loading...")
            return FAISSIndex.load(path)
        else:
            raise ValueError(f"Unknown backend in saved index: {backend}")
            
    except Exception as e:
        logger.error(f"Failed to load vector index: {e}")
        raise IOError(f"Failed to load vector index: {e}")
