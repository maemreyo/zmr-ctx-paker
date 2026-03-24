"""Unit tests for base chunker module."""

import tempfile
from pathlib import Path

import pytest

from context_packer.chunker.base import _should_include_file, _match_pattern, ASTChunker
from context_packer.models import CodeChunk


class TestShouldIncludeFile:
    """Tests for _should_include_file function."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / "main.py").write_text("print('hello')")
            (repo_path / "test_main.py").write_text("print('test')")
            (repo_path / "main.js").write_text("console.log('hello')")
            (repo_path / "node_modules").mkdir()
            (repo_path / "node_modules" / "dep.js").write_text("module.exports = {}")
            (repo_path / "__pycache__").mkdir()
            (repo_path / "__pycache__" / "main.pyc").write_text("")
            yield repo_path

    def test_include_python_files(self, temp_repo):
        include = ["**/*.py"]
        exclude = []
        file_path = temp_repo / "main.py"

        result = _should_include_file(file_path, temp_repo, include, exclude)
        assert result is True

    def test_exclude_node_modules(self, temp_repo):
        include = ["**/*.py"]
        exclude = ["node_modules/**"]
        file_path = temp_repo / "node_modules" / "dep.js"

        result = _should_include_file(file_path, temp_repo, include, exclude)
        assert result is False

    def test_exclude_pycache(self, temp_repo):
        include = ["**/*.py"]
        exclude = ["__pycache__/**"]
        file_path = temp_repo / "__pycache__" / "main.pyc"

        result = _should_include_file(file_path, temp_repo, include, exclude)
        assert result is False

    def test_double_star_pattern(self, temp_repo):
        include = ["**/*.py"]
        exclude = []
        file_path = temp_repo / "main.py"

        result = _should_include_file(file_path, temp_repo, include, exclude)
        assert result is True

    def test_no_match_returns_false(self, temp_repo):
        include = ["**/*.go"]
        exclude = []
        file_path = temp_repo / "main.py"

        result = _should_include_file(file_path, temp_repo, include, exclude)
        assert result is False

    def test_exclude_takes_precedence(self, temp_repo):
        include = ["**/*.py"]
        exclude = ["**/test_*.py"]
        file_path = temp_repo / "test_main.py"

        result = _should_include_file(file_path, temp_repo, include, exclude)
        assert result is False


class TestMatchPattern:
    """Tests for _match_pattern function."""

    def test_simple_filename_match(self):
        path = "main.py"
        parts = ["main.py"]
        pattern = "main.py"
        assert _match_pattern(path, parts, pattern) is True

    def test_glob_star_match(self):
        path = "src/main.py"
        parts = ["src", "main.py"]
        pattern = "*.py"
        assert _match_pattern(path, parts, pattern) is True

    def test_double_star_prefix_match(self):
        path = "src/deep/nested/main.py"
        parts = ["src", "deep", "nested", "main.py"]
        pattern = "**/main.py"
        assert _match_pattern(path, parts, pattern) is True

    def test_double_star_replacement(self):
        path = "src/main.py"
        parts = ["src", "main.py"]
        pattern = "**/main.py"
        assert _match_pattern(path, parts, pattern) is True

    def test_no_match(self):
        path = "main.py"
        parts = ["main.py"]
        pattern = "*.js"
        assert _match_pattern(path, parts, pattern) is False


class TestASTChunkerAbstract:
    """Tests for ASTChunker abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError, match="abstract class"):
            ASTChunker()

    def test_subclass_must_implement_parse(self):
        class Incomplete(ASTChunker):
            pass

        with pytest.raises(TypeError, match="abstract class"):
            Incomplete()

    def test_complete_subclass(self):
        class Complete(ASTChunker):
            def parse(self, repo_path: str, config=None):
                return []

        chunker = Complete()
        assert isinstance(chunker, ASTChunker)
        result = chunker.parse("/some/path")
        assert result == []


class TestCodeChunkModel:
    """Tests for CodeChunk model usage in chunkers."""

    def test_code_chunk_token_count(self):
        import tiktoken
        chunk = CodeChunk(
            path="test.py",
            start_line=1,
            end_line=5,
            content="def hello():\n    print('Hello')\n    return True\n",
            symbols_defined=["hello"],
            symbols_referenced=["print"],
            language="python"
        )

        enc = tiktoken.get_encoding("cl100k_base")
        count = chunk.token_count(enc)
        assert isinstance(count, int)
        assert count > 0
