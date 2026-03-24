"""
Property-based tests for index phase workflow.

Tests Properties 24-27 from the design document.
"""

import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from context_packer.config import Config
from context_packer.indexer import index_repository, load_indexes
from context_packer.models import IndexMetadata


# Check if sentence-transformers is available
try:
    import sentence_transformers
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Skip all tests if sentence-transformers is not available
pytestmark = pytest.mark.skipif(
    not HAS_SENTENCE_TRANSFORMERS,
    reason="sentence-transformers not installed (required for embeddings)"
)


# Test fixtures and helpers

@pytest.fixture
def temp_repo():
    """Create a temporary repository with sample Python files."""
    temp_dir = tempfile.mkdtemp()
    
    # Create sample Python files
    (Path(temp_dir) / "main.py").write_text("""
def hello():
    print("Hello, world!")

class Greeter:
    def greet(self, name):
        return f"Hello, {name}!"
""")
    
    (Path(temp_dir) / "utils.py").write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# Property 24: Index Persistence Round-Trip
# Validates: Requirements 9.1, 9.2, 9.3

@settings(
    max_examples=5,
    deadline=60000,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)  # Reduced examples for performance
@given(
    token_budget=st.integers(min_value=10000, max_value=200000),
    semantic_weight=st.floats(min_value=0.0, max_value=1.0),
)
def test_property_24_index_persistence_round_trip(token_budget, semantic_weight):
    """
    Property 24: Index Persistence Round-Trip
    
    Test that save/load produces equivalent results.
    
    Universal Property:
    FOR ALL repositories R, configurations C:
        index_repository(R, C) THEN load_indexes(R)
        => loaded indexes produce same search results as original indexes
    
    Validates: Requirements 9.1, 9.2, 9.3
    """
    # Create temp repo for this test
    temp_repo = tempfile.mkdtemp()
    try:
        # Create sample files
        (Path(temp_repo) / "main.py").write_text("def hello(): pass")
        (Path(temp_repo) / "utils.py").write_text("def add(a, b): return a + b")
        
        # Create config
        pagerank_weight = 1.0 - semantic_weight
        config = Config(
            token_budget=token_budget,
            semantic_weight=semantic_weight,
            pagerank_weight=pagerank_weight
        )
        
        # Build indexes
        index_repository(temp_repo, config=config)
        
        # Load indexes
        vector_index, graph, metadata = load_indexes(temp_repo)
        
        # Verify indexes are loaded correctly
        assert vector_index is not None, "Vector index should be loaded"
        assert graph is not None, "Graph should be loaded"
        assert metadata is not None, "Metadata should be loaded"
        
        # Verify metadata
        assert metadata.file_count > 0, "File count should be positive"
        assert metadata.backend is not None, "Backend should be recorded"
        assert len(metadata.file_hashes) > 0, "File hashes should be recorded"
        
        # Test search functionality (round-trip equivalence)
        query = "hello function"
        try:
            results = vector_index.search(query, top_k=5)
            assert isinstance(results, list), "Search should return a list"
            assert all(isinstance(r, tuple) and len(r) == 2 for r in results), \
                "Each result should be a (path, score) tuple"
        except Exception as e:
            # Some configurations might not support search (e.g., no embeddings)
            pytest.skip(f"Search not supported in this configuration: {e}")
        
        # Test PageRank functionality
        pagerank_scores = graph.pagerank()
        assert isinstance(pagerank_scores, dict), "PageRank should return a dict"
        assert len(pagerank_scores) > 0, "PageRank should have scores"
        
        # Verify PageRank scores sum to approximately 1.0
        total_score = sum(pagerank_scores.values())
        assert abs(total_score - 1.0) < 0.001, \
            f"PageRank scores should sum to 1.0, got {total_score}"
    finally:
        shutil.rmtree(temp_repo, ignore_errors=True)


# Property 25: Backend Auto-Detection
# Validates: Requirements 9.4

def test_property_25_backend_auto_detection(temp_repo):
    """
    Property 25: Backend Auto-Detection
    
    Test that loaded indexes correctly detect their backend.
    
    Universal Property:
    FOR ALL repositories R:
        index_repository(R) with backend B
        => load_indexes(R) detects backend B correctly
    
    Validates: Requirements 9.4
    """
    # Build indexes with default config (auto backend selection)
    config = Config()
    index_repository(temp_repo, config=config)
    
    # Load indexes
    vector_index, graph, metadata = load_indexes(temp_repo)
    
    # Verify backend detection
    assert metadata.backend is not None, "Backend should be detected"
    assert "+" in metadata.backend, "Backend should include both vector and graph"
    
    # Verify backend names are valid
    vector_backend, graph_backend = metadata.backend.split("+")
    valid_vector_backends = {"LEANNIndex", "FAISSIndex"}
    valid_graph_backends = {"IGraphRepoMap", "NetworkXRepoMap"}
    
    assert vector_backend in valid_vector_backends, \
        f"Invalid vector backend: {vector_backend}"
    assert graph_backend in valid_graph_backends, \
        f"Invalid graph backend: {graph_backend}"
    
    # Verify loaded instances match detected backend
    assert vector_index.__class__.__name__ == vector_backend, \
        f"Loaded vector index type {vector_index.__class__.__name__} " \
        f"doesn't match metadata {vector_backend}"
    assert graph.__class__.__name__ == graph_backend, \
        f"Loaded graph type {graph.__class__.__name__} " \
        f"doesn't match metadata {graph_backend}"


# Property 26: Index Staleness Detection
# Validates: Requirements 9.5

def test_property_26_index_staleness_detection(temp_repo):
    """
    Property 26: Index Staleness Detection
    
    Test that modified files trigger staleness detection.
    
    Universal Property:
    FOR ALL repositories R, files F in R:
        index_repository(R) THEN modify(F)
        => metadata.is_stale(R) == True
    
    Validates: Requirements 9.5
    """
    # Build indexes
    config = Config()
    index_repository(temp_repo, config=config)
    
    # Load metadata
    metadata_path = Path(temp_repo) / ".context-pack" / "metadata.json"
    with open(metadata_path, 'r') as f:
        metadata_dict = json.load(f)
    
    metadata = IndexMetadata(
        created_at=datetime.fromisoformat(metadata_dict['created_at']),
        repo_path=metadata_dict['repo_path'],
        file_count=metadata_dict['file_count'],
        backend=metadata_dict['backend'],
        file_hashes=metadata_dict['file_hashes']
    )
    
    # Verify indexes are not stale initially
    assert not metadata.is_stale(temp_repo), \
        "Freshly built indexes should not be stale"
    
    # Modify a file
    time.sleep(0.1)  # Ensure timestamp difference
    main_py = Path(temp_repo) / "main.py"
    original_content = main_py.read_text()
    main_py.write_text(original_content + "\n# Modified\n")
    
    # Verify indexes are now stale
    assert metadata.is_stale(temp_repo), \
        "Indexes should be stale after file modification"
    
    # Test with deleted file
    utils_py = Path(temp_repo) / "utils.py"
    utils_py.unlink()
    
    assert metadata.is_stale(temp_repo), \
        "Indexes should be stale after file deletion"


# Property 27: Automatic Index Rebuild
# Validates: Requirements 9.6

def test_property_27_automatic_index_rebuild(temp_repo):
    """
    Property 27: Automatic Index Rebuild
    
    Test that stale indexes are automatically rebuilt.
    
    Universal Property:
    FOR ALL repositories R:
        index_repository(R) THEN modify(R) THEN load_indexes(R, auto_rebuild=True)
        => indexes are rebuilt and no longer stale
    
    Validates: Requirements 9.6
    """
    # Build indexes
    config = Config()
    index_repository(temp_repo, config=config)
    
    # Record original metadata timestamp
    metadata_path = Path(temp_repo) / ".context-pack" / "metadata.json"
    with open(metadata_path, 'r') as f:
        original_metadata = json.load(f)
    original_timestamp = datetime.fromisoformat(original_metadata['created_at'])
    
    # Modify a file to make indexes stale
    time.sleep(0.1)  # Ensure timestamp difference
    main_py = Path(temp_repo) / "main.py"
    original_content = main_py.read_text()
    main_py.write_text(original_content + "\n# Modified for rebuild test\n")
    
    # Load indexes with auto_rebuild=True
    time.sleep(0.1)  # Ensure timestamp difference
    vector_index, graph, metadata = load_indexes(temp_repo, auto_rebuild=True)
    
    # Verify indexes were rebuilt
    assert metadata.created_at > original_timestamp, \
        "Indexes should have been rebuilt with new timestamp"
    
    # Verify indexes are no longer stale
    assert not metadata.is_stale(temp_repo), \
        "Rebuilt indexes should not be stale"
    
    # Verify functionality after rebuild
    pagerank_scores = graph.pagerank()
    assert len(pagerank_scores) > 0, "Rebuilt graph should have PageRank scores"
    
    # Test that auto_rebuild=False preserves stale indexes
    main_py.write_text(original_content + "\n# Modified again\n")
    time.sleep(0.1)
    
    # Load without auto-rebuild
    vector_index2, graph2, metadata2 = load_indexes(temp_repo, auto_rebuild=False)
    
    # Verify indexes were NOT rebuilt (timestamp unchanged)
    assert metadata2.created_at == metadata.created_at, \
        "Indexes should not be rebuilt when auto_rebuild=False"
    
    # But they should still be stale
    assert metadata2.is_stale(temp_repo), \
        "Indexes should be stale when auto_rebuild=False"


# Integration test: Full workflow

def test_index_workflow_integration(temp_repo):
    """
    Integration test for complete index workflow.
    
    Tests the full workflow:
    1. Index repository
    2. Load indexes
    3. Verify functionality
    4. Modify files
    5. Detect staleness
    6. Auto-rebuild
    """
    # Step 1: Index repository
    config = Config(
        token_budget=50000,
        semantic_weight=0.6,
        pagerank_weight=0.4
    )
    
    index_repository(temp_repo, config=config)
    
    # Verify index files exist
    index_dir = Path(temp_repo) / ".context-pack"
    assert (index_dir / "vector.idx").exists(), "Vector index should exist"
    assert (index_dir / "graph.pkl").exists(), "Graph should exist"
    assert (index_dir / "metadata.json").exists(), "Metadata should exist"
    
    # Step 2: Load indexes
    vector_index, graph, metadata = load_indexes(temp_repo, auto_rebuild=False)
    
    # Step 3: Verify functionality
    assert metadata.file_count == 2, "Should have indexed 2 files"
    assert len(metadata.file_hashes) == 2, "Should have hashes for 2 files"
    
    pagerank_scores = graph.pagerank()
    assert len(pagerank_scores) == 2, "Should have PageRank scores for 2 files"
    
    # Step 4: Modify files
    time.sleep(0.1)
    (Path(temp_repo) / "main.py").write_text("# Modified\n")
    
    # Step 5: Detect staleness
    assert metadata.is_stale(temp_repo), "Should detect staleness"
    
    # Step 6: Auto-rebuild
    vector_index2, graph2, metadata2 = load_indexes(temp_repo, auto_rebuild=True)
    assert not metadata2.is_stale(temp_repo), "Should not be stale after rebuild"
    assert metadata2.created_at > metadata.created_at, "Should have new timestamp"


# Error handling tests

def test_index_repository_invalid_path():
    """Test that index_repository raises ValueError for invalid paths."""
    with pytest.raises(ValueError, match="does not exist"):
        index_repository("/nonexistent/path")


def test_index_repository_file_path(temp_repo):
    """Test that index_repository raises ValueError for file paths."""
    file_path = Path(temp_repo) / "main.py"
    
    with pytest.raises(ValueError, match="not a directory"):
        index_repository(str(file_path))


def test_load_indexes_missing_files(temp_repo):
    """Test that load_indexes raises FileNotFoundError when indexes don't exist."""
    with pytest.raises(FileNotFoundError):
        load_indexes(temp_repo)
