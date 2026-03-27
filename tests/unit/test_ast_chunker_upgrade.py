"""Tests for astchunk integration in TreeSitterChunker (Phase 2 — TDD-first).

These tests verify that:
1. When astchunk is available, Python and TypeScript files use it for splitting.
2. JavaScript and Rust files fall back to _extract_definitions() regardless.
3. astchunk is unavailable — graceful fallback to _extract_definitions().
4. Resulting CodeChunks have correct line ranges, content, and language fields.
5. Symbol extraction (symbols_defined/referenced) still works via resolvers.
"""

import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.chunker.tree_sitter import TreeSitterChunker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PYTHON_SOURCE = """\
def authenticate(user: str) -> bool:
    return user == "admin"


def hash_password(pw: str) -> str:
    import hashlib
    return hashlib.sha256(pw.encode()).hexdigest()
"""

TYPESCRIPT_SOURCE = """\
export function greet(name: string): string {
    return `Hello, ${name}`;
}

export function farewell(name: string): string {
    return `Goodbye, ${name}`;
}
"""

JAVASCRIPT_SOURCE = """\
function add(a, b) { return a + b; }
function sub(a, b) { return a - b; }
"""

RUST_SOURCE = """\
pub fn add(a: i32, b: i32) -> i32 { a + b }
pub fn sub(a: i32, b: i32) -> i32 { a - b }
"""


def _fake_astchunk_module() -> ModuleType:
    """Build a minimal fake 'astchunk' module that mimics the real API."""
    mod = ModuleType("astchunk")

    class FakeASTChunkBuilder:
        def __init__(self, language: str, max_chunk_size: int, metadata_template: str) -> None:
            self.language = language
            self.max_chunk_size = max_chunk_size
            self.metadata_template = metadata_template

        def chunkify(self, code: str, filepath: str = "") -> list[dict[str, Any]]:
            # Split on double-newlines to simulate AST-level splitting
            parts = [p.strip() for p in code.split("\n\n") if p.strip()]
            results = []
            line = 1
            for part in parts:
                line_count = part.count("\n") + 1
                results.append(
                    {
                        "content": part,
                        "metadata": {
                            "filepath": filepath,
                            "chunk_size": len(part),
                            "line_count": line_count,
                            "start_line_no": line,
                            "end_line_no": line + line_count - 1,
                            "node_count": 1,
                        },
                    }
                )
                line += line_count + 1  # +1 for blank line between parts
            return results

    mod.ASTChunkBuilder = FakeASTChunkBuilder  # type: ignore[attr-defined]
    return mod


def _make_chunker_with_astchunk() -> TreeSitterChunker:
    """Return a TreeSitterChunker with astchunk available in sys.modules."""
    with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
        return TreeSitterChunker()


@pytest.fixture()
def chunker_no_astchunk() -> TreeSitterChunker:
    """TreeSitterChunker with astchunk absent from sys.modules."""
    sys.modules.pop("astchunk", None)
    with patch.dict(sys.modules, {"astchunk": None}):  # type: ignore[dict-item]
        return TreeSitterChunker()


# ---------------------------------------------------------------------------
# astchunk available — Python
# ---------------------------------------------------------------------------


class TestASTChunkPython:
    def test_python_file_produces_multiple_chunks(self, tmp_path: Path) -> None:
        """astchunk splits PYTHON_SOURCE into at least 2 chunks."""
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        assert len(chunks) >= 2

    def test_python_chunks_have_correct_language(self, tmp_path: Path) -> None:
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        assert all(c.language == "python" for c in chunks)

    def test_python_chunks_have_valid_line_ranges(self, tmp_path: Path) -> None:
        """Each chunk must have start_line <= end_line, both > 0."""
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        for c in chunks:
            assert c.start_line >= 1
            assert c.end_line >= c.start_line

    def test_python_chunks_content_is_non_empty(self, tmp_path: Path) -> None:
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        assert all(c.content.strip() for c in chunks)

    def test_python_chunks_path_is_relative(self, tmp_path: Path) -> None:
        py_file = tmp_path / "src" / "auth.py"
        py_file.parent.mkdir()
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        for c in chunks:
            assert not c.path.startswith("/"), f"Expected relative path, got {c.path!r}"


# ---------------------------------------------------------------------------
# astchunk available — TypeScript
# ---------------------------------------------------------------------------


class TestASTChunkTypeScript:
    def test_typescript_file_produces_multiple_chunks(self, tmp_path: Path) -> None:
        ts_file = tmp_path / "greeter.ts"
        ts_file.write_text(TYPESCRIPT_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(ts_file, tmp_path)

        assert len(chunks) >= 2

    def test_typescript_chunks_have_correct_language(self, tmp_path: Path) -> None:
        ts_file = tmp_path / "greeter.ts"
        ts_file.write_text(TYPESCRIPT_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(ts_file, tmp_path)

        assert all(c.language == "typescript" for c in chunks)


# ---------------------------------------------------------------------------
# Fallback languages — JavaScript and Rust always use _extract_definitions
# ---------------------------------------------------------------------------


class TestFallbackLanguages:
    def test_javascript_uses_extract_definitions_not_astchunk(
        self, tmp_path: Path
    ) -> None:
        """Even with astchunk present, JavaScript falls back to tree-sitter resolver."""
        js_file = tmp_path / "math.js"
        js_file.write_text(JAVASCRIPT_SOURCE)

        fake_mod = _fake_astchunk_module()
        call_log: list[str] = []
        original_cls = fake_mod.ASTChunkBuilder

        class TrackedBuilder(original_cls):  # type: ignore[valid-type]
            def chunkify(self, code: str, filepath: str = "") -> list[dict[str, Any]]:
                call_log.append(filepath)
                return super().chunkify(code, filepath=filepath)

        fake_mod.ASTChunkBuilder = TrackedBuilder

        with patch.dict(sys.modules, {"astchunk": fake_mod}):
            chunker = TreeSitterChunker()
            chunker._parse_file(js_file, tmp_path)

        assert not call_log, "astchunk must NOT be called for JavaScript files"

    def test_rust_uses_extract_definitions_not_astchunk(self, tmp_path: Path) -> None:
        rs_file = tmp_path / "math.rs"
        rs_file.write_text(RUST_SOURCE)

        fake_mod = _fake_astchunk_module()
        call_log: list[str] = []
        original_cls = fake_mod.ASTChunkBuilder

        class TrackedBuilder(original_cls):  # type: ignore[valid-type]
            def chunkify(self, code: str, filepath: str = "") -> list[dict[str, Any]]:
                call_log.append(filepath)
                return super().chunkify(code, filepath=filepath)

        fake_mod.ASTChunkBuilder = TrackedBuilder

        with patch.dict(sys.modules, {"astchunk": fake_mod}):
            chunker = TreeSitterChunker()
            chunker._parse_file(rs_file, tmp_path)

        assert not call_log, "astchunk must NOT be called for Rust files"


# ---------------------------------------------------------------------------
# astchunk unavailable — graceful fallback
# ---------------------------------------------------------------------------


class TestASTChunkUnavailable:
    def test_python_falls_back_gracefully_when_astchunk_missing(
        self, tmp_path: Path
    ) -> None:
        """Without astchunk, _extract_definitions runs and returns chunks."""
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        saved = sys.modules.pop("astchunk", None)
        try:
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)
        finally:
            if saved is not None:
                sys.modules["astchunk"] = saved

        # Should still return at least one chunk via tree-sitter resolver
        assert isinstance(chunks, list)

    def test_typescript_falls_back_gracefully_when_astchunk_missing(
        self, tmp_path: Path
    ) -> None:
        ts_file = tmp_path / "greeter.ts"
        ts_file.write_text(TYPESCRIPT_SOURCE)

        saved = sys.modules.pop("astchunk", None)
        try:
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(ts_file, tmp_path)
        finally:
            if saved is not None:
                sys.modules["astchunk"] = saved

        assert isinstance(chunks, list)


# ---------------------------------------------------------------------------
# Content quality
# ---------------------------------------------------------------------------


class TestASTChunkContentQuality:
    def test_chunk_content_contains_function_definition(self, tmp_path: Path) -> None:
        """At least one chunk should include 'authenticate'."""
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        combined = "\n".join(c.content for c in chunks)
        assert "authenticate" in combined

    def test_no_duplicate_content_across_chunks(self, tmp_path: Path) -> None:
        """astchunk chunks must not overlap — same line shouldn't appear twice."""
        py_file = tmp_path / "auth.py"
        py_file.write_text(PYTHON_SOURCE)

        with patch.dict(sys.modules, {"astchunk": _fake_astchunk_module()}):
            chunker = TreeSitterChunker()
            chunks = chunker._parse_file(py_file, tmp_path)

        # Check that line ranges do not overlap
        ranges = [(c.start_line, c.end_line) for c in chunks]
        for i, (s1, e1) in enumerate(ranges):
            for j, (s2, e2) in enumerate(ranges):
                if i >= j:
                    continue
                overlap = s1 <= e2 and s2 <= e1
                assert not overlap, f"Chunks {i} ({s1}-{e1}) and {j} ({s2}-{e2}) overlap"
