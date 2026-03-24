"""
Unit tests for Retrieval Engine.

Tests specific examples and edge cases for hybrid retrieval.
"""

import pytest

from context_packer.retrieval import RetrievalEngine
from context_packer.vector_index import VectorIndex
from context_packer.graph import RepoMapGraph


# Mock implementations for testing
class MockVectorIndex(VectorIndex):
    """Mock VectorIndex for testing."""
    
    def __init__(self):
        self.search_results = {}
    
    def build(self, chunks):
        pass
    
    def search(self, query, top_k=10):
        return list(self.search_results.items())[:top_k]
    
    def save(self, path):
        pass
    
    @classmethod
    def load(cls, path):
        return cls()
    
    def set_search_results(self, results):
        """Set mock search results."""
        self.search_results = results


class MockRepoMapGraph(RepoMapGraph):
    """Mock RepoMapGraph for testing."""
    
    def __init__(self):
        self.pagerank_scores = {}
    
    def build(self, chunks):
        pass
    
    def pagerank(self, changed_files=None):
        return self.pagerank_scores.copy()
    
    def save(self, path):
        pass
    
    @classmethod
    def load(cls, path):
        return cls()
    
    def set_pagerank_scores(self, scores):
        """Set mock PageRank scores."""
        self.pagerank_scores = scores


class TestRetrievalEngine:
    """Tests for RetrievalEngine class."""
    
    def test_initialization_with_default_weights(self):
        """Test initialization with default weights."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        engine = RetrievalEngine(
            vector_index=vector_index,
            graph=graph
        )
        
        assert engine.semantic_weight == 0.6
        assert engine.pagerank_weight == 0.4
        assert engine.vector_index is vector_index
        assert engine.graph is graph
    
    def test_initialization_with_custom_weights(self):
        """Test initialization with custom weights."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        engine = RetrievalEngine(
            vector_index=vector_index,
            graph=graph,
            semantic_weight=0.7,
            pagerank_weight=0.3
        )
        
        assert engine.semantic_weight == 0.7
        assert engine.pagerank_weight == 0.3
    
    def test_initialization_with_invalid_weights(self):
        """Test that invalid weights raise ValueError."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        # Weights don't sum to 1.0
        with pytest.raises(ValueError, match="must sum to 1.0"):
            RetrievalEngine(
                vector_index=vector_index,
                graph=graph,
                semantic_weight=0.5,
                pagerank_weight=0.6
            )
        
        # Negative weight
        with pytest.raises(ValueError, match="must be in"):
            RetrievalEngine(
                vector_index=vector_index,
                graph=graph,
                semantic_weight=-0.1,
                pagerank_weight=1.1
            )
        
        # Weight > 1.0
        with pytest.raises(ValueError, match="must be in"):
            RetrievalEngine(
                vector_index=vector_index,
                graph=graph,
                semantic_weight=1.5,
                pagerank_weight=-0.5
            )
    
    def test_normalize_scores_to_zero_one_range(self):
        """Test normalizing scores to [0, 1] range."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(vector_index, graph)
        
        # Test with various score ranges
        scores = {
            "a.py": 0.5,
            "b.py": 1.0,
            "c.py": 0.0,
            "d.py": 0.75
        }
        
        normalized = engine._normalize(scores)
        
        # Check all values are in [0, 1]
        for file, score in normalized.items():
            assert 0.0 <= score <= 1.0
        
        # Check min is 0.0 and max is 1.0
        values = list(normalized.values())
        assert min(values) == 0.0
        assert max(values) == 1.0
        
        # Check specific values
        assert normalized["c.py"] == 0.0  # min
        assert normalized["b.py"] == 1.0  # max
        assert normalized["a.py"] == 0.5  # middle
        assert normalized["d.py"] == 0.75
    
    def test_normalize_empty_scores(self):
        """Test normalizing empty scores dict."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(vector_index, graph)
        
        normalized = engine._normalize({})
        
        assert normalized == {}
    
    def test_normalize_single_score(self):
        """Test normalizing single score."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(vector_index, graph)
        
        scores = {"a.py": 0.5}
        normalized = engine._normalize(scores)
        
        # Single score should normalize to 1.0
        assert normalized["a.py"] == 1.0
    
    def test_normalize_equal_scores(self):
        """Test normalizing all equal scores."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(vector_index, graph)
        
        scores = {
            "a.py": 0.5,
            "b.py": 0.5,
            "c.py": 0.5
        }
        
        normalized = engine._normalize(scores)
        
        # All equal scores should normalize to 1.0
        for file, score in normalized.items():
            assert score == 1.0
    
    def test_merge_scores_with_correct_weights(self):
        """Test merging scores with correct weights."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(
            vector_index,
            graph,
            semantic_weight=0.6,
            pagerank_weight=0.4
        )
        
        semantic_scores = {
            "a.py": 1.0,
            "b.py": 0.5
        }
        
        pagerank_scores = {
            "a.py": 0.5,
            "c.py": 1.0
        }
        
        merged = engine._merge_scores(semantic_scores, pagerank_scores)
        
        # a.py: 0.6 * 1.0 + 0.4 * 0.5 = 0.8
        assert abs(merged["a.py"] - 0.8) < 1e-9
        
        # b.py: 0.6 * 0.5 + 0.4 * 0.0 = 0.3
        assert abs(merged["b.py"] - 0.3) < 1e-9
        
        # c.py: 0.6 * 0.0 + 0.4 * 1.0 = 0.4
        assert abs(merged["c.py"] - 0.4) < 1e-9
    
    def test_merge_scores_with_equal_weights(self):
        """Test merging scores with equal weights."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(
            vector_index,
            graph,
            semantic_weight=0.5,
            pagerank_weight=0.5
        )
        
        semantic_scores = {"a.py": 1.0}
        pagerank_scores = {"a.py": 0.0}
        
        merged = engine._merge_scores(semantic_scores, pagerank_scores)
        
        # a.py: 0.5 * 1.0 + 0.5 * 0.0 = 0.5
        assert abs(merged["a.py"] - 0.5) < 1e-9
    
    def test_handling_missing_semantic_scores(self):
        """Test handling files with missing semantic scores."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        # Set only PageRank scores
        graph.set_pagerank_scores({
            "a.py": 0.5,
            "b.py": 0.3,
            "c.py": 0.2
        })
        
        engine = RetrievalEngine(
            vector_index,
            graph,
            semantic_weight=0.6,
            pagerank_weight=0.4
        )
        
        # Retrieve without query (no semantic scores)
        results = engine.retrieve(query=None, top_k=10)
        
        # Should still return results based on PageRank only
        assert len(results) == 3
        
        # Results should be sorted by PageRank score
        assert results[0][0] == "a.py"
        assert results[1][0] == "b.py"
        assert results[2][0] == "c.py"
    
    def test_handling_missing_pagerank_scores(self):
        """Test handling files with missing PageRank scores."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        # Set only semantic scores
        vector_index.set_search_results({
            "a.py": 0.9,
            "b.py": 0.7,
            "c.py": 0.5
        })
        
        engine = RetrievalEngine(
            vector_index,
            graph,
            semantic_weight=0.6,
            pagerank_weight=0.4
        )
        
        # Retrieve with query (no PageRank scores)
        results = engine.retrieve(query="test", top_k=10)
        
        # Should still return results based on semantic scores only
        assert len(results) == 3
        
        # Results should be sorted by semantic score
        assert results[0][0] == "a.py"
        assert results[1][0] == "b.py"
        assert results[2][0] == "c.py"
    
    def test_retrieve_returns_sorted_results(self):
        """Test that retrieve returns results sorted by score descending."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        # Set mock data
        vector_index.set_search_results({
            "a.py": 0.5,
            "b.py": 0.8,
            "c.py": 0.3
        })
        
        graph.set_pagerank_scores({
            "a.py": 0.7,
            "b.py": 0.2,
            "c.py": 0.9
        })
        
        engine = RetrievalEngine(
            vector_index,
            graph,
            semantic_weight=0.6,
            pagerank_weight=0.4
        )
        
        results = engine.retrieve(query="test", top_k=10)
        
        # Verify results are sorted descending
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_retrieve_respects_top_k(self):
        """Test that retrieve respects top_k parameter."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        # Set mock data with 5 files
        vector_index.set_search_results({
            f"file_{i}.py": 0.5 + i * 0.1
            for i in range(5)
        })
        
        graph.set_pagerank_scores({
            f"file_{i}.py": 0.2
            for i in range(5)
        })
        
        engine = RetrievalEngine(vector_index, graph)
        
        # Request only top 3
        results = engine.retrieve(query="test", top_k=3)
        
        assert len(results) == 3
    
    def test_retrieve_with_changed_files(self):
        """Test retrieve with changed files for PageRank boosting."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        # Set mock data
        vector_index.set_search_results({
            "a.py": 0.5,
            "b.py": 0.5
        })
        
        graph.set_pagerank_scores({
            "a.py": 0.3,
            "b.py": 0.7  # Higher PageRank (simulating boost)
        })
        
        engine = RetrievalEngine(
            vector_index,
            graph,
            semantic_weight=0.5,
            pagerank_weight=0.5
        )
        
        results = engine.retrieve(
            query="test",
            changed_files=["b.py"],
            top_k=10
        )
        
        # b.py should rank higher due to PageRank boost
        assert results[0][0] == "b.py"
        assert results[1][0] == "a.py"
    
    def test_retrieve_output_format(self):
        """Test that retrieve returns correct output format."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()
        
        vector_index.set_search_results({"a.py": 0.5})
        graph.set_pagerank_scores({"a.py": 0.5})
        
        engine = RetrievalEngine(vector_index, graph)
        results = engine.retrieve(query="test", top_k=10)
        
        # Should be list of tuples
        assert isinstance(results, list)
        assert len(results) == 1
        
        file_path, score = results[0]
        assert isinstance(file_path, str)
        assert isinstance(score, float)
        assert file_path == "a.py"
        assert 0.0 <= score <= 1.0
