"""
Backend selection with automatic fallback logic.

Provides centralized backend selection for all components with graceful degradation.
"""

from ..config import Config
from ..graph import RepoMapGraph, create_graph
from ..logger import get_logger
from ..vector_index import VectorIndex, create_vector_index


class BackendSelector:
    """
    Automatic backend selection with fallback chains.

    Implements graceful degradation hierarchy:
    - Level 1: igraph + NativeLEANN + local embeddings (optimal, 97% storage savings)
    - Level 2: NetworkX + NativeLEANN + local embeddings
    - Level 3: NetworkX + LEANNIndex + local embeddings
    - Level 4: NetworkX + FAISS + local embeddings
    - Level 5: NetworkX + FAISS + API embeddings
    - Level 6: File size ranking only (no graph)
    """

    def __init__(self, config: Config | None = None):
        """
        Initialize backend selector with configuration.

        Args:
            config: Configuration instance (uses defaults if None)
        """
        self.config = config or Config()
        self.logger = get_logger()

    def select_vector_index(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
        index_path: str | None = None,
    ) -> VectorIndex:
        """
        Select vector index backend with fallback chain.

        Tries backends in order based on configuration:
        1. NativeLEANN (leann library - 97% storage savings)
        2. LEANNIndex (cosine similarity fallback)
        3. FAISSIndex (HNSW fallback)

        Args:
            model_name: Embedding model name (uses config default if None)
            device: Device to use ('cpu' or 'cuda', uses config default if None)
            batch_size: Batch size for embeddings (uses config default if None)
            index_path: Path for LEANN index storage

        Returns:
            VectorIndex instance with selected backend

        Raises:
            RuntimeError: If all backends fail
        """
        model_name = model_name or self.config.embeddings["model"]
        device = device or self.config.embeddings["device"]
        batch_size = batch_size or self.config.embeddings["batch_size"]
        index_path = index_path or "./leann_index"

        backend_config = self.config.backends["vector_index"]

        try:
            return create_vector_index(
                backend=backend_config,
                model_name=model_name,
                device=device,
                batch_size=batch_size,
                index_path=index_path,
            )
        except RuntimeError as e:
            self.logger.error(f"All vector index backends failed: {e}")
            raise

    def select_graph(self, boost_factor: float | None = None) -> RepoMapGraph:
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
            return create_graph(backend=backend_config, boost_factor=boost_factor)
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
            - 1: igraph + NativeLEANN + local embeddings (optimal, 97% storage savings)
            - 2: NetworkX + NativeLEANN + local embeddings
            - 3: NetworkX + LEANNIndex + local embeddings
            - 4: NetworkX + FAISS + local embeddings
            - 5: NetworkX + FAISS + API embeddings
            - 6: File size ranking only (no graph)
        """
        graph_backend = self.config.backends["graph"]
        has_igraph = graph_backend == "igraph" or graph_backend == "auto"

        vector_backend = self.config.backends["vector_index"]
        has_native_leann = vector_backend == "native-leann" or vector_backend == "auto"
        has_leann = vector_backend == "leann"
        has_faiss = vector_backend == "faiss"

        embeddings_backend = self.config.backends["embeddings"]
        has_local = embeddings_backend == "local" or embeddings_backend == "auto"
        has_api = embeddings_backend == "api"

        if has_igraph and has_native_leann and has_local:
            return 1
        elif has_native_leann and has_local:
            return 2
        elif has_leann and has_local:
            return 3
        elif has_faiss and has_local:
            return 4
        elif has_faiss and has_api:
            return 5
        else:
            return 6

    def log_current_configuration(self) -> None:
        """Log the current backend configuration."""
        level = self.get_fallback_level()

        level_descriptions = {
            1: "Optimal (igraph + NativeLEANN + local embeddings, 97% storage savings)",
            2: "Good (NetworkX + NativeLEANN + local embeddings)",
            3: "Acceptable (NetworkX + LEANNIndex + local embeddings)",
            4: "Degraded (NetworkX + FAISS + local embeddings)",
            5: "Minimal (NetworkX + FAISS + API embeddings)",
            6: "Fallback only (file size ranking)",
        }

        self.logger.info(
            f"Backend configuration | level={level} | "
            f"description={level_descriptions[level]} | "
            f"vector_index={self.config.backends['vector_index']} | "
            f"graph={self.config.backends['graph']} | "
            f"embeddings={self.config.backends['embeddings']}"
        )


def create_backend_selector(config: Config | None = None) -> BackendSelector:
    """
    Create a BackendSelector instance.

    Args:
        config: Configuration instance (uses defaults if None)

    Returns:
        BackendSelector instance
    """
    return BackendSelector(config)
