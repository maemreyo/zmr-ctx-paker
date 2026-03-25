"""Unit tests for MarkdownChunker."""

import tempfile
from pathlib import Path

import pytest

from ws_ctx_engine.chunker.markdown import MarkdownChunker
from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.config import Config


class TestMarkdownChunker:
    """Tests for MarkdownChunker."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    @pytest.fixture
    def md_config(self):
        config = Config()
        config.include_patterns = ['**/*.md', '**/*.markdown', '**/*.mdx']
        return config

    def test_markdown_no_headings(self, temp_repo, md_config):
        """Test markdown file with no headings returns single chunk."""
        code = "This is just plain text without any headings."
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 1
        assert chunks[0].content == code
        assert chunks[0].language == 'markdown'

    def test_markdown_single_heading(self, temp_repo, md_config):
        """Test markdown file with single heading."""
        code = "# Hello\n\nThis is content."
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 1
        assert chunks[0].symbols_defined == ["Hello"]

    def test_markdown_multiple_headings(self, temp_repo, md_config):
        """Test markdown file with multiple headings."""
        code = """# First Section

Content of first section.

## Second Section

Content of second section.

### Third Section

Content of third section.
"""
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 3
        symbols = [c.symbols_defined[0] for c in chunks]
        assert "First Section" in symbols
        assert "Second Section" in symbols
        assert "Third Section" in symbols

    def test_markdown_heading_at_start(self, temp_repo, md_config):
        """Test that heading at start of file is handled."""
        code = """# Title

First paragraph.

## Subtitle

Second paragraph.
"""
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 2

    def test_markdown_skip_empty_heading_range(self, temp_repo, md_config):
        """Test that empty heading ranges are skipped."""
        code = """# A

# B

Content after B.
"""
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) >= 1

    def test_markdown_file_extensions(self, temp_repo, md_config):
        """Test various markdown file extensions."""
        (temp_repo / "readme.md").write_text("# MD File\n\nContent")
        (temp_repo / "readme.markdown").write_text("# Markdown\n\nContent")
        (temp_repo / "readme.mdx").write_text("# MDX\n\nContent")

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 3

    def test_markdown_symbols_referenced_empty(self, temp_repo, md_config):
        """Test that symbols_referenced is always empty list for markdown."""
        code = "# Title\n\nSome content with `code`."
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        for chunk in chunks:
            assert chunk.symbols_referenced == []

    def test_markdown_includes_filename_as_fallback_symbol(self, temp_repo, md_config):
        """Test that filename is used as symbol when no headings."""
        (temp_repo / "my_readme.md").write_text("Just plain text without headings.")

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 1
        assert chunks[0].symbols_defined == ["my_readme"]

    def test_markdown_with_code_block(self, temp_repo, md_config):
        """Test markdown with code blocks."""
        code = """# Title

Some text.

```python
def hello():
    print("Hello")
```

More text.
"""
        (temp_repo / "readme.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 1
        assert "```python" in chunks[0].content
        assert "def hello():" in chunks[0].content

    def test_markdown_relative_path(self, temp_repo, md_config):
        """Test that relative path is correctly set."""
        (temp_repo / "docs" / "api.md").parent.mkdir()
        (temp_repo / "docs" / "api.md").write_text("# API Documentation\n\nAPI content.")

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert any("docs/api.md" in c.path for c in chunks)

    def test_markdown_read_error_handling(self, temp_repo, md_config, monkeypatch):
        """Test that read errors are handled gracefully."""
        def mock_read_text(*args, **kwargs):
            raise IOError("Simulated read error")

        (temp_repo / "readme.md").write_text("# Title\n\nContent")

        monkeypatch.setattr("pathlib.Path.read_text", mock_read_text)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 0

    def test_markdown_nonexistent_repo_path(self, temp_repo):
        """Test handling of nonexistent repository path."""
        chunker = MarkdownChunker()

        with pytest.raises(ValueError):
            chunker.parse("/nonexistent/path/12345")

    def test_markdown_file_not_directory(self, temp_repo):
        """Test handling when repo_path is a file, not directory."""
        (temp_repo / "readme.md").write_text("# Title")

        chunker = MarkdownChunker()

        with pytest.raises(ValueError):
            chunker.parse(str(temp_repo / "readme.md"))

    def test_markdown_custom_extensions(self, temp_repo):
        """Test that custom extensions work via config."""
        config = Config()
        config.include_patterns = ['**/*.txt']
        config.exclude_patterns = []

        (temp_repo / "readme.txt").write_text("# Not really markdown")

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=config)

        assert len(chunks) == 0

    def test_markdown_heading_only_files(self, temp_repo, md_config):
        """Test markdown that is only headings."""
        code = """# Title 1

## Title 2

### Title 3
"""
        (temp_repo / "headings.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 3

    def test_markdown_heading_with_special_characters(self, temp_repo, md_config):
        """Test heading with special characters."""
        code = """# Hello, World! (2024)

Content here.
"""
        (temp_repo / "special.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) == 1
        assert "Hello, World! (2024)" in chunks[0].symbols_defined

    def test_markdown_content_without_heading_still_extracted(self, temp_repo, md_config):
        """Test that content before first heading is captured."""
        code = """Intro text before any heading.

# First Heading

Content under first heading.
"""
        (temp_repo / "intro.md").write_text(code)

        chunker = MarkdownChunker()
        chunks = chunker.parse(str(temp_repo), config=md_config)

        assert len(chunks) >= 1
        symbols = []
        for chunk in chunks:
            symbols.extend(chunk.symbols_defined)
        assert "First Heading" in symbols
