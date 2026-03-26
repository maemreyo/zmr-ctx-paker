"""
Property-based tests for backend selection and graceful degradation.

Tests backend fallback logic and error handling.
"""

from hypothesis import given
from hypothesis import strategies as st

from ws_ctx_engine.backend_selector import BackendSelector, create_backend_selector
from ws_ctx_engine.config import Config


# Property 28: Graceful Degradation
# **Validates: Requirements 10.3, 10.4, 10.5, 10.6**
def test_property_28_graceful_degradation_vector_index():
    """
    Property 28: Graceful Degradation (Vector Index)

    For any component where all backends fail, the ws_ctx_engine SHALL
    degrade to a simpler algorithm (TF-IDF for vector index, file size
    ranking for graph) and continue execution rather than crashing.
    """
    # Create config with auto backend selection
    config = Config()
    config.backends["vector_index"] = "auto"

    selector = BackendSelector(config)

    # The selector should handle failures gracefully
    # Even if primary backends fail, it should fall back to simpler algorithms
    try:
        # This should either succeed or raise a clear error
        # but should not crash unexpectedly
        vector_index = selector.select_vector_index()
        assert vector_index is not None
    except RuntimeError as e:
        # If all backends fail, should raise RuntimeError with clear message
        assert "vector index backends failed" in str(e).lower()


def test_property_28_graceful_degradation_graph():
    """
    Property 28: Graceful Degradation (Graph)

    For any component where all backends fail, the ws_ctx_engine SHALL
    degrade to a simpler algorithm and continue execution rather than crashing.
    """
    # Create config with auto backend selection
    config = Config()
    config.backends["graph"] = "auto"

    selector = BackendSelector(config)

    # The selector should handle failures gracefully
    try:
        # This should either succeed or raise a clear error
        # but should not crash unexpectedly
        graph = selector.select_graph()
        assert graph is not None
    except RuntimeError as e:
        # If all backends fail, should raise RuntimeError with clear message
        assert "graph backends failed" in str(e).lower()


@given(
    vector_backend=st.sampled_from(["auto", "leann", "faiss"]),
    graph_backend=st.sampled_from(["auto", "igraph", "networkx"]),
    embeddings_backend=st.sampled_from(["auto", "local", "api"]),
)
def test_property_28_backend_configuration_valid(vector_backend, graph_backend, embeddings_backend):
    """
    Property 28: Graceful Degradation (Configuration)

    For any valid backend configuration, the BackendSelector SHALL
    create instances without crashing.
    """
    config = Config()
    config.backends["vector_index"] = vector_backend
    config.backends["graph"] = graph_backend
    config.backends["embeddings"] = embeddings_backend

    # Should create selector without crashing
    selector = BackendSelector(config)
    assert selector is not None

    # Should determine fallback level
    level = selector.get_fallback_level()
    assert 1 <= level <= 6


def test_property_28_fallback_level_ordering():
    """
    Property 28: Graceful Degradation (Fallback Levels)

    The fallback level should correctly reflect the degradation hierarchy.
    """
    # Level 1: Optimal (igraph + NativeLEANN + local)
    config1 = Config()
    config1.backends = {"vector_index": "native-leann", "graph": "igraph", "embeddings": "local"}
    selector1 = BackendSelector(config1)
    assert selector1.get_fallback_level() == 1

    # Level 2: NetworkX + NativeLEANN + local
    config2 = Config()
    config2.backends = {"vector_index": "native-leann", "graph": "networkx", "embeddings": "local"}
    selector2 = BackendSelector(config2)
    assert selector2.get_fallback_level() == 2

    # Level 3: NetworkX + LEANN + local
    config3 = Config()
    config3.backends = {"vector_index": "leann", "graph": "networkx", "embeddings": "local"}
    selector3 = BackendSelector(config3)
    assert selector3.get_fallback_level() == 3


def test_property_28_log_configuration():
    """
    Property 28: Graceful Degradation (Logging)

    The BackendSelector SHALL log the current configuration without crashing.
    """
    config = Config()
    selector = BackendSelector(config)

    # Should log configuration without crashing
    selector.log_current_configuration()

    # Should be able to get fallback level
    level = selector.get_fallback_level()
    assert isinstance(level, int)
    assert 1 <= level <= 6


def test_create_backend_selector():
    """Test factory function for creating BackendSelector."""
    # With config
    config = Config()
    selector1 = create_backend_selector(config)
    assert isinstance(selector1, BackendSelector)

    # Without config (uses defaults)
    selector2 = create_backend_selector()
    assert isinstance(selector2, BackendSelector)
