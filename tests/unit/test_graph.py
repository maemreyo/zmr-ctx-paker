"""
Unit tests for RepoMap Graph implementations.

Tests specific examples and edge cases for graph construction and PageRank computation.
"""

import os
import tempfile
import pytest

from ws_ctx_engine.graph import (
    create_graph,
    load_graph,
    IGraphRepoMap,
    NetworkXRepoMap,
)
from ws_ctx_engine.models import CodeChunk


@pytest.fixture
def sample_chunks():
    """Create sample code chunks for testing."""
    return [
        CodeChunk(
            path="src/main.py",
            start_line=1,
            end_line=10,
            content="def main():\n    helper()\n",
            symbols_defined=["main"],
            symbols_referenced=["helper"],
            language="python"
        ),
        CodeChunk(
            path="src/helper.py",
            start_line=1,
            end_line=5,
            content="def helper():\n    pass\n",
            symbols_defined=["helper"],
            symbols_referenced=[],
            language="python"
        ),
        CodeChunk(
            path="src/utils.py",
            start_line=1,
            end_line=8,
            content="def util():\n    helper()\n",
            symbols_defined=["util"],
            symbols_referenced=["helper"],
            language="python"
        ),
    ]


@pytest.fixture
def sample_chunks_with_cycle():
    """Create sample code chunks with circular dependencies."""
    return [
        CodeChunk(
            path="src/a.py",
            start_line=1,
            end_line=5,
            content="def a():\n    b()\n",
            symbols_defined=["a"],
            symbols_referenced=["b"],
            language="python"
        ),
        CodeChunk(
            path="src/b.py",
            start_line=1,
            end_line=5,
            content="def b():\n    c()\n",
            symbols_defined=["b"],
            symbols_referenced=["c"],
            language="python"
        ),
        CodeChunk(
            path="src/c.py",
            start_line=1,
            end_line=5,
            content="def c():\n    a()\n",
            symbols_defined=["c"],
            symbols_referenced=["a"],
            language="python"
        ),
    ]


class TestNetworkXRepoMap:
    """Tests for NetworkX backend."""
    
    def test_build_graph_from_chunks(self, sample_chunks):
        """Test building graph from symbol references."""
        networkx = pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap()
        graph.build(sample_chunks)
        
        # Should have 3 nodes
        assert graph.graph.number_of_nodes() == 3
        
        # Should have edges: main.py -> helper.py, utils.py -> helper.py
        assert graph.graph.has_edge("src/main.py", "src/helper.py")
        assert graph.graph.has_edge("src/utils.py", "src/helper.py")
    
    def test_pagerank_scores_sum_to_one(self, sample_chunks):
        """Test that PageRank scores sum to 1.0."""
        pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap()
        graph.build(sample_chunks)
        
        scores = graph.pagerank()
        
        # Scores should sum to 1.0 (within tolerance)
        total = sum(scores.values())
        assert abs(total - 1.0) < 0.001
    
    def test_changed_files_receive_boosted_scores(self, sample_chunks):
        """Test that changed files receive boosted scores."""
        pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap(boost_factor=2.0)
        graph.build(sample_chunks)
        
        # Compute scores without boosting
        scores_before = graph.pagerank()
        
        # Compute scores with boosting for main.py
        scores_after = graph.pagerank(changed_files=["src/main.py"])
        
        # main.py should have higher score after boosting
        assert scores_after["src/main.py"] > scores_before["src/main.py"]
        
        # Scores should still sum to 1.0
        total = sum(scores_after.values())
        assert abs(total - 1.0) < 0.001
    
    def test_save_and_load(self, sample_chunks):
        """Test saving and loading graph."""
        pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap()
        graph.build(sample_chunks)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            temp_path = f.name
        
        try:
            graph.save(temp_path)
            
            # Load graph
            loaded_graph = NetworkXRepoMap.load(temp_path)
            
            # Should have same number of nodes
            assert loaded_graph.graph.number_of_nodes() == graph.graph.number_of_nodes()
            
            # Should produce same PageRank scores
            scores_original = graph.pagerank()
            scores_loaded = loaded_graph.pagerank()
            
            for file in scores_original:
                assert abs(scores_original[file] - scores_loaded[file]) < 0.001
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_build_with_empty_chunks_raises_error(self):
        """Test that building with empty chunks raises ValueError."""
        pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap()
        
        with pytest.raises(ValueError, match="Cannot build graph from empty chunks list"):
            graph.build([])
    
    def test_pagerank_before_build_raises_error(self):
        """Test that calling pagerank before build raises ValueError."""
        pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap()
        
        with pytest.raises(ValueError, match="Graph has not been built yet"):
            graph.pagerank()
    
    def test_graph_with_circular_dependencies(self, sample_chunks_with_cycle):
        """Test that graph handles circular dependencies correctly."""
        pytest.importorskip("networkx")
        
        graph = NetworkXRepoMap()
        graph.build(sample_chunks_with_cycle)
        
        # Should have 3 nodes
        assert graph.graph.number_of_nodes() == 3
        
        # Should have edges forming a cycle
        assert graph.graph.has_edge("src/a.py", "src/b.py")
        assert graph.graph.has_edge("src/b.py", "src/c.py")
        assert graph.graph.has_edge("src/c.py", "src/a.py")
        
        # PageRank should still work
        scores = graph.pagerank()
        total = sum(scores.values())
        assert abs(total - 1.0) < 0.001


class TestIGraphRepoMap:
    """Tests for igraph backend."""
    
    def test_build_graph_from_chunks(self, sample_chunks):
        """Test building graph from symbol references."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap()
        graph.build(sample_chunks)
        
        # Should have 3 nodes
        assert graph.graph.vcount() == 3
        
        # Should have edges: main.py -> helper.py, utils.py -> helper.py
        main_vertex = graph.file_to_vertex["src/main.py"]
        helper_vertex = graph.file_to_vertex["src/helper.py"]
        utils_vertex = graph.file_to_vertex["src/utils.py"]
        
        assert graph.graph.get_eid(main_vertex, helper_vertex, error=False) != -1
        assert graph.graph.get_eid(utils_vertex, helper_vertex, error=False) != -1
    
    def test_pagerank_scores_sum_to_one(self, sample_chunks):
        """Test that PageRank scores sum to 1.0."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap()
        graph.build(sample_chunks)
        
        scores = graph.pagerank()
        
        # Scores should sum to 1.0 (within tolerance)
        total = sum(scores.values())
        assert abs(total - 1.0) < 0.001
    
    def test_changed_files_receive_boosted_scores(self, sample_chunks):
        """Test that changed files receive boosted scores."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap(boost_factor=2.0)
        graph.build(sample_chunks)
        
        # Compute scores without boosting
        scores_before = graph.pagerank()
        
        # Compute scores with boosting for main.py
        scores_after = graph.pagerank(changed_files=["src/main.py"])
        
        # main.py should have higher score after boosting
        assert scores_after["src/main.py"] > scores_before["src/main.py"]
        
        # Scores should still sum to 1.0
        total = sum(scores_after.values())
        assert abs(total - 1.0) < 0.001
    
    def test_save_and_load(self, sample_chunks):
        """Test saving and loading graph."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap()
        graph.build(sample_chunks)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            temp_path = f.name
        
        try:
            graph.save(temp_path)
            
            # Load graph
            loaded_graph = IGraphRepoMap.load(temp_path)
            
            # Should have same number of nodes
            assert loaded_graph.graph.vcount() == graph.graph.vcount()
            
            # Should produce same PageRank scores
            scores_original = graph.pagerank()
            scores_loaded = loaded_graph.pagerank()
            
            for file in scores_original:
                assert abs(scores_original[file] - scores_loaded[file]) < 0.001
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_build_with_empty_chunks_raises_error(self):
        """Test that building with empty chunks raises ValueError."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap()
        
        with pytest.raises(ValueError, match="Cannot build graph from empty chunks list"):
            graph.build([])
    
    def test_pagerank_before_build_raises_error(self):
        """Test that calling pagerank before build raises ValueError."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap()
        
        with pytest.raises(ValueError, match="Graph has not been built yet"):
            graph.pagerank()
    
    def test_graph_with_circular_dependencies(self, sample_chunks_with_cycle):
        """Test that graph handles circular dependencies correctly."""
        pytest.importorskip("igraph")
        
        graph = IGraphRepoMap()
        graph.build(sample_chunks_with_cycle)
        
        # Should have 3 nodes
        assert graph.graph.vcount() == 3
        
        # Should have edges forming a cycle
        a_vertex = graph.file_to_vertex["src/a.py"]
        b_vertex = graph.file_to_vertex["src/b.py"]
        c_vertex = graph.file_to_vertex["src/c.py"]
        
        assert graph.graph.get_eid(a_vertex, b_vertex, error=False) != -1
        assert graph.graph.get_eid(b_vertex, c_vertex, error=False) != -1
        assert graph.graph.get_eid(c_vertex, a_vertex, error=False) != -1
        
        # PageRank should still work
        scores = graph.pagerank()
        total = sum(scores.values())
        assert abs(total - 1.0) < 0.001


class TestBackendSelection:
    """Tests for backend selection and fallback logic."""
    
    def test_create_graph_auto_prefers_igraph(self, sample_chunks):
        """Test that auto mode prefers igraph if available."""
        try:
            import igraph
            igraph_available = True
        except ImportError:
            igraph_available = False
        
        graph = create_graph(backend="auto")
        
        if igraph_available:
            assert isinstance(graph, IGraphRepoMap)
        else:
            assert isinstance(graph, NetworkXRepoMap)
    
    def test_create_graph_explicit_networkx(self):
        """Test creating graph with explicit NetworkX backend."""
        pytest.importorskip("networkx")
        
        graph = create_graph(backend="networkx")
        assert isinstance(graph, NetworkXRepoMap)
    
    def test_create_graph_explicit_igraph(self):
        """Test creating graph with explicit igraph backend."""
        pytest.importorskip("igraph")
        
        graph = create_graph(backend="igraph")
        assert isinstance(graph, IGraphRepoMap)
    
    def test_create_graph_invalid_backend_raises_error(self):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Invalid backend"):
            create_graph(backend="invalid")
    
    def test_load_graph_detects_backend(self, sample_chunks):
        """Test that load_graph detects backend automatically."""
        pytest.importorskip("networkx")
        
        # Create and save NetworkX graph
        graph = NetworkXRepoMap()
        graph.build(sample_chunks)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as f:
            temp_path = f.name
        
        try:
            graph.save(temp_path)
            
            # Load should detect NetworkX backend
            loaded_graph = load_graph(temp_path)
            assert isinstance(loaded_graph, NetworkXRepoMap)
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
