"""Unit tests for AST chunker."""

import pytest

from ws_ctx_engine.chunker import ASTChunker
from ws_ctx_engine.models import CodeChunk


class TestASTChunker:
    """Unit tests for ASTChunker abstract base class."""

    def test_astchunker_is_abstract(self):
        """Test that ASTChunker cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ASTChunker()

    def test_astchunker_requires_parse_implementation(self):
        """Test that subclasses must implement parse() method."""

        class IncompleteChunker(ASTChunker):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteChunker()

    def test_astchunker_subclass_with_parse(self):
        """Test that subclass with parse() implementation can be instantiated."""

        class ConcreteChunker(ASTChunker):
            def parse(self, repo_path: str):
                return []

        chunker = ConcreteChunker()
        assert isinstance(chunker, ASTChunker)
        assert chunker.parse("/some/path") == []

    def test_astchunker_parse_signature(self):
        """Test that parse() method has correct signature."""

        class TestChunker(ASTChunker):
            def parse(self, repo_path: str):
                return [
                    CodeChunk(
                        path="test.py",
                        start_line=1,
                        end_line=5,
                        content="def test():\n    pass",
                        symbols_defined=["test"],
                        symbols_referenced=[],
                        language="python",
                    )
                ]

        chunker = TestChunker()
        result = chunker.parse("/repo")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], CodeChunk)
        assert result[0].path == "test.py"
