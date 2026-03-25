"""
Unit tests for Retrieval Engine.

Tests specific examples and edge cases for hybrid retrieval.
"""

import pytest

from ws_ctx_engine.retrieval import RetrievalEngine
from ws_ctx_engine.vector_index import VectorIndex
from ws_ctx_engine.graph import RepoMapGraph


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


class TestExtractQueryTokens:
    """Tests for _extract_query_tokens helper."""

    def _engine(self):
        return RetrievalEngine(MockVectorIndex(), MockRepoMapGraph())

    def test_extracts_identifiers(self):
        engine = self._engine()
        tokens = engine._extract_query_tokens("PythonResolver extracts symbols")
        assert "pythonresolver" in tokens
        assert "extracts" in tokens
        assert "symbols" in tokens

    def test_removes_stop_words(self):
        engine = self._engine()
        tokens = engine._extract_query_tokens("how does the chunker work")
        assert "how" not in tokens
        assert "does" not in tokens
        assert "the" not in tokens
        assert "chunker" in tokens

    def test_removes_short_tokens(self):
        engine = self._engine()
        tokens = engine._extract_query_tokens("do it")
        assert not tokens  # all tokens too short or stop words

    def test_underscore_identifiers(self):
        engine = self._engine()
        tokens = engine._extract_query_tokens("_should_include_file logic")
        assert "_should_include_file" in tokens or "should_include_file" in tokens
        assert "logic" in tokens

    def test_empty_query(self):
        engine = self._engine()
        assert engine._extract_query_tokens("") == set()


class TestComputeSymbolScores:
    """Tests for _compute_symbol_scores."""

    def _engine(self):
        return RetrievalEngine(MockVectorIndex(), MockRepoMapGraph())

    def test_exact_symbol_match(self):
        engine = self._engine()
        file_symbols = {
            "chunker/python.py": ["PythonResolver", "extract_symbol_name"],
            "models/models.py": ["CodeChunk", "symbols_defined"],
        }
        scores = engine._compute_symbol_scores({"pythonresolver"}, file_symbols)
        assert "chunker/python.py" in scores
        assert "models/models.py" not in scores

    def test_no_match_returns_empty(self):
        engine = self._engine()
        file_symbols = {"src/utils.py": ["format_output"]}
        scores = engine._compute_symbol_scores({"chunker"}, file_symbols)
        assert scores == {}

    def test_multiple_matches_scores_higher(self):
        engine = self._engine()
        file_symbols = {
            "a.py": ["foo", "bar"],
            "b.py": ["foo"],
        }
        scores = engine._compute_symbol_scores({"foo", "bar"}, file_symbols)
        assert scores["a.py"] > scores["b.py"]

    def test_empty_inputs(self):
        engine = self._engine()
        assert engine._compute_symbol_scores(set(), {"a.py": ["foo"]}) == {}
        assert engine._compute_symbol_scores({"foo"}, {}) == {}


class TestComputePathScores:
    """Tests for _compute_path_scores."""

    def _engine(self):
        return RetrievalEngine(MockVectorIndex(), MockRepoMapGraph())

    def test_filename_keyword_match(self):
        engine = self._engine()
        files = {"chunker/python.py", "models/models.py", "graph/graph.py"}
        scores = engine._compute_path_scores({"python"}, files)
        assert "chunker/python.py" in scores
        assert "models/models.py" not in scores
        assert "graph/graph.py" not in scores

    def test_directory_keyword_match(self):
        engine = self._engine()
        files = {"chunker/base.py", "models/models.py"}
        scores = engine._compute_path_scores({"chunker"}, files)
        assert "chunker/base.py" in scores
        assert "models/models.py" not in scores

    def test_no_match_returns_empty(self):
        engine = self._engine()
        scores = engine._compute_path_scores({"authentication"}, {"src/utils.py"})
        assert scores == {}

    def test_scores_capped_at_one(self):
        engine = self._engine()
        files = {"resolvers/python.py"}
        # many tokens but only one matches
        scores = engine._compute_path_scores({"python", "resolver", "foo", "bar"}, files)
        for s in scores.values():
            assert 0.0 <= s <= 1.0


class TestIsTestFile:
    """Tests for _is_test_file."""

    def _engine(self):
        return RetrievalEngine(MockVectorIndex(), MockRepoMapGraph())

    def test_test_directory(self):
        engine = self._engine()
        assert engine._is_test_file("tests/unit/test_chunker.py")
        assert engine._is_test_file("test/helpers.py")

    def test_test_prefix(self):
        engine = self._engine()
        assert engine._is_test_file("src/test_utils.py")

    def test_test_suffix(self):
        engine = self._engine()
        assert engine._is_test_file("src/auth_test.py")

    def test_spec_suffix(self):
        engine = self._engine()
        assert engine._is_test_file("src/auth.spec.ts")

    def test_implementation_file(self):
        engine = self._engine()
        assert not engine._is_test_file("src/chunker/base.py")
        assert not engine._is_test_file("models/models.py")


class TestSymbolBoostIntegration:
    """Integration tests: symbol boost changes ranking in retrieve()."""

    def test_symbol_match_boosts_ranking(self):
        """File defining a queried symbol should rank higher."""

        class SymbolAwareIndex(MockVectorIndex):
            def get_file_symbols(self):
                return {
                    "resolvers/python.py": ["PythonResolver", "extract_symbol_name"],
                    "models/models.py": ["CodeChunk", "IndexMetadata"],
                }

        vector_index = SymbolAwareIndex()
        graph = MockRepoMapGraph()

        # Both files have equal semantic score
        vector_index.set_search_results({
            "resolvers/python.py": 0.6,
            "models/models.py": 0.6,
        })
        graph.set_pagerank_scores({
            "resolvers/python.py": 0.5,
            "models/models.py": 0.5,
        })

        engine = RetrievalEngine(
            vector_index, graph,
            semantic_weight=0.6, pagerank_weight=0.4,
            symbol_boost=0.5, path_boost=0.0, test_penalty=0.0,
        )

        results = engine.retrieve(query="PythonResolver extracts symbols", top_k=10)
        ranked_files = [f for f, _ in results]

        assert ranked_files[0] == "resolvers/python.py"

    def test_test_file_penalty_lowers_ranking(self):
        """Test files should rank lower than implementation files."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()

        vector_index.set_search_results({
            "tests/unit/test_chunker.py": 0.9,
            "chunker/base.py": 0.7,
        })
        graph.set_pagerank_scores({
            "tests/unit/test_chunker.py": 0.5,
            "chunker/base.py": 0.5,
        })

        engine = RetrievalEngine(
            vector_index, graph,
            semantic_weight=0.6, pagerank_weight=0.4,
            symbol_boost=0.0, path_boost=0.0, test_penalty=0.8,
        )

        results = engine.retrieve(query="chunker base logic", top_k=10)
        ranked_files = [f for f, _ in results]

        assert ranked_files[0] == "chunker/base.py"

    def test_path_boost_helps_implementation_file(self):
        """File with matching path keyword should rank higher."""
        vector_index = MockVectorIndex()
        graph = MockRepoMapGraph()

        # Same scores for both
        vector_index.set_search_results({
            "chunker/base.py": 0.6,
            "vector_index/vector_index.py": 0.6,
        })
        graph.set_pagerank_scores({
            "chunker/base.py": 0.5,
            "vector_index/vector_index.py": 0.5,
        })

        engine = RetrievalEngine(
            vector_index, graph,
            semantic_weight=0.6, pagerank_weight=0.4,
            symbol_boost=0.0, path_boost=0.5, test_penalty=0.0,
        )

        results = engine.retrieve(query="chunking logic flow", top_k=10)
        ranked_files = [f for f, _ in results]

        assert ranked_files[0] == "chunker/base.py"

    def test_final_scores_in_zero_one_range(self):
        """All returned scores must be in [0, 1] even with boosts applied."""

        class SymbolAwareIndex(MockVectorIndex):
            def get_file_symbols(self):
                return {
                    "a.py": ["foo", "bar"],
                    "b.py": ["baz"],
                }

        vector_index = SymbolAwareIndex()
        graph = MockRepoMapGraph()

        vector_index.set_search_results({"a.py": 0.9, "b.py": 0.3})
        graph.set_pagerank_scores({"a.py": 0.4, "b.py": 0.8})

        engine = RetrievalEngine(
            vector_index, graph,
            symbol_boost=0.5, path_boost=0.3, test_penalty=0.4,
        )

        results = engine.retrieve(query="foo bar search", top_k=10)
        for _, score in results:
            assert 0.0 <= score <= 1.0
