"""Tests for ws_ctx_engine.chunker.enrichment (Phase 2 — written BEFORE implementation)."""

import pytest

from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.chunker.enrichment import enrich_chunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    path: str = "src/auth.py",
    content: str = "def authenticate(user): pass",
    language: str = "python",
    start_line: int = 1,
    end_line: int = 1,
    symbols_defined: list[str] | None = None,
    symbols_referenced: list[str] | None = None,
) -> CodeChunk:
    return CodeChunk(
        path=path,
        content=content,
        language=language,
        start_line=start_line,
        end_line=end_line,
        symbols_defined=symbols_defined or [],
        symbols_referenced=symbols_referenced or [],
    )


# ---------------------------------------------------------------------------
# Prefix structure
# ---------------------------------------------------------------------------


class TestEnrichChunkPrefix:
    def test_prefix_contains_file_path(self) -> None:
        chunk = _make_chunk(path="src/utils/auth.py")
        enriched = enrich_chunk(chunk)
        assert "src/utils/auth.py" in enriched.content

    def test_prefix_contains_language(self) -> None:
        chunk = _make_chunk(language="python")
        enriched = enrich_chunk(chunk)
        assert "python" in enriched.content

    def test_prefix_contains_line_range(self) -> None:
        chunk = _make_chunk(start_line=10, end_line=25)
        enriched = enrich_chunk(chunk)
        assert "10" in enriched.content
        assert "25" in enriched.content

    def test_prefix_format_file_line(self) -> None:
        """Prefix must start with '# File: <path>'."""
        chunk = _make_chunk(path="src/auth.py")
        enriched = enrich_chunk(chunk)
        lines = enriched.content.splitlines()
        assert lines[0] == "# File: src/auth.py"

    def test_prefix_format_lines_line(self) -> None:
        """Third line of prefix must be '# Lines: <start>-<end>'."""
        chunk = _make_chunk(start_line=5, end_line=20)
        enriched = enrich_chunk(chunk)
        lines = enriched.content.splitlines()
        assert any(line == "# Lines: 5-20" for line in lines[:5])

    def test_original_content_preserved_after_prefix(self) -> None:
        """The original code must appear after the prefix lines."""
        original = "def foo(): pass"
        chunk = _make_chunk(content=original)
        enriched = enrich_chunk(chunk)
        assert enriched.content.endswith(original)

    def test_prefix_separated_by_blank_line(self) -> None:
        """A blank line separates the header block from the code body."""
        chunk = _make_chunk(content="x = 1")
        enriched = enrich_chunk(chunk)
        # There must be at least one blank line between the last # comment and code
        lines = enriched.content.splitlines()
        # Find last '#' line index
        last_header = max(i for i, ln in enumerate(lines) if ln.startswith("#"))
        assert lines[last_header + 1] == "", "Expected blank line after prefix header"


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestEnrichChunkImmutability:
    def test_returns_new_chunk_not_same_object(self) -> None:
        chunk = _make_chunk()
        enriched = enrich_chunk(chunk)
        assert enriched is not chunk

    def test_original_chunk_content_unchanged(self) -> None:
        original_content = "def bar(): return 42"
        chunk = _make_chunk(content=original_content)
        enrich_chunk(chunk)
        assert chunk.content == original_content

    def test_metadata_fields_preserved(self) -> None:
        """path, language, start_line, end_line, symbols_defined/referenced unchanged."""
        chunk = _make_chunk(
            path="src/core.py",
            language="python",
            start_line=7,
            end_line=15,
            symbols_defined=["my_func"],
            symbols_referenced=["os", "sys"],
        )
        enriched = enrich_chunk(chunk)
        assert enriched.path == "src/core.py"
        assert enriched.language == "python"
        assert enriched.start_line == 7
        assert enriched.end_line == 15
        assert enriched.symbols_defined == ["my_func"]
        assert enriched.symbols_referenced == ["os", "sys"]


# ---------------------------------------------------------------------------
# Language variants
# ---------------------------------------------------------------------------


class TestEnrichChunkLanguages:
    @pytest.mark.parametrize(
        "language",
        ["python", "typescript", "javascript", "rust"],
    )
    def test_works_for_all_supported_languages(self, language: str) -> None:
        chunk = _make_chunk(language=language)
        enriched = enrich_chunk(chunk)
        assert language in enriched.content

    def test_typescript_file_uses_ts_extension_path(self) -> None:
        chunk = _make_chunk(path="src/index.ts", language="typescript")
        enriched = enrich_chunk(chunk)
        assert "src/index.ts" in enriched.content


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEnrichChunkEdgeCases:
    def test_empty_content_still_adds_prefix(self) -> None:
        chunk = _make_chunk(content="")
        enriched = enrich_chunk(chunk)
        # Prefix lines must be present even for empty content
        assert "# File:" in enriched.content

    def test_multiline_content_preserved(self) -> None:
        code = "def a():\n    return 1\n\ndef b():\n    return 2"
        chunk = _make_chunk(content=code, start_line=1, end_line=5)
        enriched = enrich_chunk(chunk)
        assert code in enriched.content

    def test_content_with_existing_comments_not_confused(self) -> None:
        code = "# existing comment\ndef f(): pass"
        chunk = _make_chunk(content=code)
        enriched = enrich_chunk(chunk)
        assert "# existing comment" in enriched.content
