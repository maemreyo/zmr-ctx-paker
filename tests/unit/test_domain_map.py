"""Unit tests for DomainKeywordMap."""

import pytest

from ws_ctx_engine.domain_map import DomainKeywordMap
from ws_ctx_engine.models import CodeChunk


class TestDomainKeywordMap:
    """Tests for DomainKeywordMap."""

    def test_keyword_extraction_from_simple_path(self):
        """Test keyword extraction from a simple file path."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="chunker/tree_sitter.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map.build(chunks)

        assert "chunker" in domain_map.keywords
        assert "tree" in domain_map.keywords
        assert "sitter" in domain_map.keywords

    def test_noise_words_filtered(self):
        """Test that noise words are filtered out."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="src/main.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map.build(chunks)

        assert "py" not in domain_map.keywords
        assert "src" not in domain_map.keywords
        assert "main" not in domain_map.keywords

    def test_directories_for_keyword(self):
        """Test getting directories for a keyword."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="chunker/base.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            ),
            CodeChunk(
                path="chunker/resolvers/python.py",
                start_line=1,
                end_line=10,
                content="def bar(): pass",
                symbols_defined=["bar"],
                symbols_referenced=[],
                language="python",
            ),
        ]

        domain_map.build(chunks)

        dirs = domain_map.directories_for("chunker")
        assert "chunker" in dirs
        assert "chunker/resolvers" in dirs

    def test_keyword_matches_exact(self):
        """Test exact keyword matching."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="chunker/tree_sitter.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map.build(chunks)

        assert domain_map.keyword_matches("chunker") is True
        assert domain_map.keyword_matches("CHUNKER") is True  # case insensitive

    def test_keyword_matches_prefix(self):
        """Test prefix matching."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="chunker/tree_sitter.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map.build(chunks)

        # "chunking" has prefix "chunk" matching "chunker"
        assert domain_map.keyword_matches("chunking") is True
        # "chunker" itself should match
        assert domain_map.keyword_matches("chunker") is True

    def test_keyword_not_matches_unrelated(self):
        """Test that unrelated tokens don't match."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="chunker/tree_sitter.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map.build(chunks)

        assert domain_map.keyword_matches("xyz123") is False

    def test_save_and_load(self, tmp_path):
        """Test saving and loading domain map."""
        domain_map1 = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="chunker/base.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map1.build(chunks)

        save_path = tmp_path / "domain_map.pkl"
        domain_map1.save(str(save_path))

        domain_map2 = DomainKeywordMap.load(str(save_path))

        assert domain_map2.keywords == domain_map1.keywords

    def test_empty_chunks_list(self):
        """Test building with empty chunks list."""
        domain_map = DomainKeywordMap()
        domain_map.build([])

        assert len(domain_map.keywords) == 0

    def test_multiple_files_same_directory(self):
        """Test multiple files in same directory."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="graph/repo_map.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            ),
            CodeChunk(
                path="graph/dependency.py",
                start_line=1,
                end_line=10,
                content="def bar(): pass",
                symbols_defined=["bar"],
                symbols_referenced=[],
                language="python",
            ),
        ]

        domain_map.build(chunks)

        assert "graph" in domain_map.keywords
        dirs = domain_map.directories_for("graph")
        assert "graph" in dirs

    def test_keyword_extraction_from_directory_names(self):
        """Test that directory names become keywords."""
        domain_map = DomainKeywordMap()

        chunks = [
            CodeChunk(
                path="vector_index/faiss_index.py",
                start_line=1,
                end_line=10,
                content="def foo(): pass",
                symbols_defined=["foo"],
                symbols_referenced=[],
                language="python",
            )
        ]

        domain_map.build(chunks)

        assert "vector" in domain_map.keywords
        assert "faiss" in domain_map.keywords
        assert "index" not in domain_map.keywords  # noise word


class TestRetrievalEngineQueryClassification:
    """Tests for RetrievalEngine query classification."""

    def test_classify_symbol_query(self):
        """Test that PascalCase queries are classified as symbol."""
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        vector_idx = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(vector_idx, graph)

        tokens = {"TreeSitterChunker", "parses"}
        assert engine._classify_query("TreeSitterChunker parses", tokens) == "symbol"

    def test_classify_snake_case_query(self):
        """Test that snake_case tokens are classified as symbol."""
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        vector_idx = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(vector_idx, graph)

        tokens = {"my_function"}
        assert engine._classify_query("my_function implementation", tokens) == "symbol"

    def test_classify_path_dominant(self):
        """Test that domain keyword queries are classified as path-dominant."""
        from ws_ctx_engine.retrieval.retrieval import DomainKeywordMap, RetrievalEngine

        vector_idx = MockVectorIndex()
        graph = MockRepoMapGraph()

        domain_map = DomainKeywordMap()
        domain_map._keyword_to_dirs = {"chunker": {"chunker"}}

        engine = RetrievalEngine(vector_idx, graph, domain_map=domain_map)

        tokens = {"chunking", "logic", "flow"}
        assert engine._classify_query("chunking logic flow", tokens) == "path-dominant"

    def test_effective_weights_symbol(self):
        """Test effective weights for symbol queries."""
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        vector_idx = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(
            vector_idx, graph, symbol_boost=0.3, path_boost=0.2, domain_boost=0.4
        )

        eff_symbol, eff_path, eff_domain = engine._effective_weights("symbol")

        assert eff_symbol == pytest.approx(0.3 * 1.5)  # 0.45
        assert eff_path == pytest.approx(0.2 * 0.5)  # 0.10
        assert eff_domain == pytest.approx(0.4 * 0.3)  # 0.12

    def test_effective_weights_path_dominant(self):
        """Test effective weights for path-dominant queries."""
        from ws_ctx_engine.retrieval.retrieval import RetrievalEngine

        vector_idx = MockVectorIndex()
        graph = MockRepoMapGraph()
        engine = RetrievalEngine(
            vector_idx, graph, symbol_boost=0.3, path_boost=0.2, domain_boost=0.4
        )

        eff_symbol, eff_path, eff_domain = engine._effective_weights("path-dominant")

        assert eff_symbol == pytest.approx(0.3 * 0.5)  # 0.15
        assert eff_path == pytest.approx(0.2 * 1.5)  # 0.30
        assert eff_domain == pytest.approx(0.4 * 0.5)  # 0.20

    def test_compute_domain_scores(self):
        """Test domain score computation."""
        from ws_ctx_engine.retrieval.retrieval import DomainKeywordMap, RetrievalEngine

        vector_idx = MockVectorIndex()
        graph = MockRepoMapGraph()

        domain_map = DomainKeywordMap()
        domain_map._keyword_to_dirs = {"chunker": {"chunker"}}

        engine = RetrievalEngine(vector_idx, graph, domain_map=domain_map)

        tokens = {"chunking"}
        all_files = {"chunker/base.py", "vector_index/vector.py"}

        scores = engine._compute_domain_scores(tokens, all_files)

        assert scores["chunker/base.py"] == 1.0
        assert "vector_index/vector.py" not in scores  # not in matched dirs


class MockVectorIndex:
    """Mock VectorIndex for testing."""

    def __init__(self):
        pass

    def get_file_symbols(self):
        return {}


class MockRepoMapGraph:
    """Mock RepoMapGraph for testing."""

    def __init__(self):
        pass
