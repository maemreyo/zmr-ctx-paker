"""
Backend selection with automatic fallback logic.

Provides centralized backend selection for all components with graceful degradation.
"""

from typing import Optional

from .config import Config
from .graph import RepoMapGraph, create_graph
from .logger import get_logger
from .vector_index import VectorIndex, create_vector_index


class BackendSelector:
    """
    Automatic backend selection with fallback chains.
    
    Implements graceful degradation hierarchy:
    - Level 1: igraph + LEANN + local embeddings (optimal)
    - Level 2: NetworkX + LEANN + local embeddings
    - Level 3: NetworkX + FAISS + local embeddings
    - Level 4: NetworkX + FAISS + API embeddings
    - Level 5: NetworkX + TF-IDF (no embeddings)
    - Level 6: File size ranking only (no graph)
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize backend selector with configuration.
        
        Args:
            config: Configuration instance (uses defaults if None)
        """
        self.config = config or Config()
        self.logger = get_logger()
    
    def select_vector_index(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> VectorIndex:
        """
        Select vector index backend with fallback chain.
        
        Tries backends in order based on configuration:
        1. LEANN (if configured or auto)
        2. FAISS (if LEANN fails or configured)
        3. TF-IDF (minimal fallback if all fail)
        
        Args:
            model_name: Embedding model name (uses config default if None)
            device: Device to use ('cpu' or 'cuda', uses config default if None)
            batch_size: Batch size for embeddings (uses config default if None)
        
        Returns:
            VectorIndex instance with selected backend
        
        Raises:
            RuntimeError: If all backends fail
        """
        # Use config defaults if not specified
        model_name = model_name or self.config.embeddings["model"]
        device = device or self.config.embeddings["device"]
        batch_size = batch_size or self.config.embeddings["batch_size"]
        
        backend_config = self.config.backends["vector_index"]
        
        # Use existing create_vector_index which already implements fallback
        try:
            return create_vector_index(
                backend=backend_config,
                model_name=model_name,
                device=device,
                batch_size=batch_size
            )
        except RuntimeError as e:
            # All backends failed
            self.logger.error(f"All vector index backends failed: {e}")
            raise
    
    def select_graph(
        self,
        boost_factor: Optional[float] = None
    ) -> RepoMapGraph:
        """
        Select graph backend with fallback chain.
        
        Tries backends in order based on configuration:
        1. igraph (if configured or auto)
        2. NetworkX (if igraph fails or configured)
        3. File size ranking (minimal fallback if all fail)
        
        Args:
            boost_factor: Factor to boost changed file scores (default: 2.0)
        
        Returns:
            RepoMapGraph instance with selected backend
        
        Raises:
            RuntimeError: If all backends fail
        """
        boost_factor = boost_factor or 2.0
        backend_config = self.config.backends["graph"]
        
        # Use existing create_graph which already implements fallback
        try:
            return create_graph(
                backend=backend_config,
                boost_factor=boost_factor
            )
        except RuntimeError as e:
            # All backends failed
            self.logger.error(f"All graph backends failed: {e}")
            raise
    
    def select_embeddings_backend(self) -> str:
        """
        Select embeddings backend based on configuration.
        
        Returns:
            Backend name: 'local', 'api', or 'auto'
        """
        return self.config.backends["embeddings"]
    
    def get_fallback_level(self) -> int:
        """
        Determine current fallback level based on available backends.
        
        Returns:
            Fallback level (1-6):
            - 1: igraph + LEANN + local embeddings (optimal)
            - 2: NetworkX + LEANN + local embeddings
            - 3: NetworkX + FAISS + local embeddings
            - 4: NetworkX + FAISS + API embeddings
            - 5: NetworkX + TF-IDF (no embeddings)
            - 6: File size ranking only (no graph)
        """
        # Check graph backend
        graph_backend = self.config.backends["graph"]
        has_igraph = graph_backend == "igraph" or graph_backend == "auto"
        
        # Check vector index backend
        vector_backend = self.config.backends["vector_index"]
        has_leann = vector_backend == "leann" or vector_backend == "auto"
        has_faiss = vector_backend == "faiss" or vector_backend == "auto"
        
        # Check embeddings backend
        embeddings_backend = self.config.backends["embeddings"]
        has_local = embeddings_backend == "local" or embeddings_backend == "auto"
        has_api = embeddings_backend == "api" or embeddings_backend == "auto"
        
        # Determine level
        if has_igraph and has_leann and has_local:
            return 1  # Optimal
        elif has_leann and has_local:
            return 2  # NetworkX + LEANN + local
        elif has_faiss and has_local:
            return 3  # NetworkX + FAISS + local
        elif has_faiss and has_api:
            return 4  # NetworkX + FAISS + API
        elif has_faiss:
            return 5  # NetworkX + TF-IDF
        else:
            return 6  # File size ranking only
    
    def log_current_configuration(self) -> None:
        """Log the current backend configuration."""
        level = self.get_fallback_level()
        
        level_descriptions = {
            1: "Optimal (igraph + LEANN + local embeddings)",
            2: "Good (NetworkX + LEANN + local embeddings)",
            3: "Acceptable (NetworkX + FAISS + local embeddings)",
            4: "Degraded (NetworkX + FAISS + API embeddings)",
            5: "Minimal (NetworkX + TF-IDF)",
            6: "Fallback only (file size ranking)"
        }
        
        self.logger.info(
            f"Backend configuration | level={level} | "
            f"description={level_descriptions[level]} | "
            f"vector_index={self.config.backends['vector_index']} | "
            f"graph={self.config.backends['graph']} | "
            f"embeddings={self.config.backends['embeddings']}"
        )


def create_backend_selector(config: Optional[Config] = None) -> BackendSelector:
    """
    Create a BackendSelector instance.
    
    Args:
        config: Configuration instance (uses defaults if None)
    
    Returns:
        BackendSelector instance
    """
    return BackendSelector(config)
