"""Phase 1 regression tests: JS routing, Java/C# support, enrichment consistency, chunk size."""

import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _get_chunker():
    try:
        from ws_ctx_engine.chunker import TreeSitterChunker

        return TreeSitterChunker()
    except ImportError:
        pytest.skip("TreeSitter not available")


# ---------------------------------------------------------------------------
# Task 14 — JavaScript should be routed through astchunk
# ---------------------------------------------------------------------------

JAVASCRIPT_CLASS = """\
export class Greeter {
    constructor(name) {
        this.name = name;
    }

    greet() {
        return `Hello, ${this.name}!`;
    }

    farewell() {
        return `Goodbye, ${this.name}!`;
    }
}

export function standalone() {
    return 42;
}
"""


class TestJavaScriptAstchunkRouting:
    """JS files must go through astchunk when available (same as Python/TypeScript)."""

    def test_javascript_chunks_have_enrichment_header(self, temp_repo):
        """If astchunk is used for JS, the enrichment header must be present."""
        pytest.importorskip("astchunk", reason="astchunk not installed")
        chunker = _get_chunker()
        (temp_repo / "greeter.js").write_text(JAVASCRIPT_CLASS)
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith(".js")]
        assert js_chunks, "No JS chunks produced"
        for c in js_chunks:
            assert c.content.startswith("# File:"), (
                f"JS chunk missing enrichment header (astchunk path not used).\n"
                f"Content start: {c.content[:80]!r}"
            )

    def test_javascript_symbols_extracted(self, temp_repo):
        """JS chunks should have symbols_defined populated."""
        pytest.importorskip("astchunk", reason="astchunk not installed")
        chunker = _get_chunker()
        (temp_repo / "greeter.js").write_text(JAVASCRIPT_CLASS)
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith(".js")]
        assert js_chunks, "No JS chunks produced"
        all_symbols = [s for c in js_chunks for s in c.symbols_defined]
        assert any(s in ("Greeter", "standalone", "greet", "farewell") for s in all_symbols), (
            f"Expected Greeter/standalone/greet/farewell in symbols, got: {all_symbols}"
        )


# ---------------------------------------------------------------------------
# Task 15 — Java / C# support
# ---------------------------------------------------------------------------

JAVA_CLASS = """\
package com.example;

public class HelloWorld {
    private String name;

    public HelloWorld(String name) {
        this.name = name;
    }

    public String greet() {
        return "Hello, " + this.name + "!";
    }

    public static void main(String[] args) {
        HelloWorld hw = new HelloWorld("World");
        System.out.println(hw.greet());
    }
}
"""

CSHARP_CLASS = """\
using System;

namespace Example {
    public class Greeter {
        private string name;

        public Greeter(string name) {
            this.name = name;
        }

        public string Greet() {
            return $"Hello, {name}!";
        }
    }
}
"""


class TestJavaCsharpSupport:
    """Java (.java) and C# (.cs) files must be parsed — not silently dropped."""

    def test_java_file_produces_chunks(self, temp_repo):
        """A .java file must produce at least one chunk."""
        pytest.importorskip("astchunk", reason="astchunk not installed — Java uses astchunk only")
        chunker = _get_chunker()
        (temp_repo / "HelloWorld.java").write_text(JAVA_CLASS)
        chunks = chunker.parse(str(temp_repo))

        java_chunks = [c for c in chunks if c.path.endswith(".java")]
        assert java_chunks, (
            "No chunks produced for .java file. Java must be supported via astchunk."
        )

    def test_java_chunks_have_enrichment_header(self, temp_repo):
        """Java chunks must have the enrichment header (astchunk path)."""
        pytest.importorskip("astchunk", reason="astchunk not installed")
        chunker = _get_chunker()
        (temp_repo / "HelloWorld.java").write_text(JAVA_CLASS)
        chunks = chunker.parse(str(temp_repo))

        java_chunks = [c for c in chunks if c.path.endswith(".java")]
        assert java_chunks, "No Java chunks"
        for c in java_chunks:
            assert c.content.startswith("# File:"), (
                f"Java chunk missing enrichment header: {c.content[:80]!r}"
            )

    def test_csharp_file_produces_chunks(self, temp_repo):
        """A .cs file must produce at least one chunk."""
        pytest.importorskip("astchunk", reason="astchunk not installed — C# uses astchunk only")
        chunker = _get_chunker()
        (temp_repo / "Greeter.cs").write_text(CSHARP_CLASS)
        chunks = chunker.parse(str(temp_repo))

        cs_chunks = [c for c in chunks if c.path.endswith(".cs")]
        assert cs_chunks, (
            "No chunks produced for .cs file. C# must be supported via astchunk."
        )


# ---------------------------------------------------------------------------
# Task 16 — enrich_chunk applied uniformly on ALL code paths
# ---------------------------------------------------------------------------


class TestEnrichmentConsistency:
    """Every chunk from every code path must have the # File: / # Type: / # Lines: header."""

    def test_rust_chunks_have_enrichment_header(self, temp_repo):
        """Rust uses the tree-sitter resolver path and must also be enriched."""
        chunker = _get_chunker()
        (temp_repo / "lib.rs").write_text(
            "pub fn hello() -> &'static str {\n    \"hello\"\n}\n"
        )
        chunks = chunker.parse(str(temp_repo))
        rust_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert rust_chunks, "No Rust chunks produced"
        for c in rust_chunks:
            assert c.content.startswith("# File:"), (
                f"Rust chunk missing enrichment header.\nContent: {c.content[:120]!r}"
            )

    def test_python_chunks_have_enrichment_header(self, temp_repo):
        """Python uses the astchunk path and must have the header (regression guard)."""
        pytest.importorskip("astchunk", reason="astchunk not installed")
        chunker = _get_chunker()
        (temp_repo / "main.py").write_text("def hello():\n    return 'hi'\n")
        chunks = chunker.parse(str(temp_repo))
        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        assert py_chunks, "No Python chunks"
        for c in py_chunks:
            assert c.content.startswith("# File:"), (
                f"Python chunk missing enrichment header: {c.content[:80]!r}"
            )

    def test_typescript_resolver_fallback_enriched(self, temp_repo, monkeypatch):
        """When astchunk is unavailable for TypeScript, resolver-path chunks must be enriched."""
        chunker = _get_chunker()
        # Simulate astchunk being absent by making _try_astchunk return None
        monkeypatch.setattr(chunker, "_try_astchunk", lambda *a, **kw: None)
        (temp_repo / "mod.ts").write_text("export function greet(): string { return 'hi'; }\n")
        chunks = chunker.parse(str(temp_repo))
        ts_chunks = [c for c in chunks if c.path.endswith(".ts")]
        assert ts_chunks, "No TS chunks produced"
        for c in ts_chunks:
            assert c.content.startswith("# File:"), (
                f"TS resolver-path chunk missing enrichment header: {c.content[:80]!r}"
            )

    def test_all_paths_produce_consistent_header_format(self, temp_repo):
        """Verify header lines for all available languages use the same format."""
        chunker = _get_chunker()
        (temp_repo / "lib.rs").write_text("pub fn f() {}\n")
        chunks = chunker.parse(str(temp_repo))
        for c in chunks:
            lines = c.content.splitlines()
            assert lines[0].startswith("# File: "), f"Line 0 wrong: {lines[0]!r}"
            assert lines[1].startswith("# Type: "), f"Line 1 wrong: {lines[1]!r}"
            assert lines[2].startswith("# Lines: "), f"Line 2 wrong: {lines[2]!r}"


# ---------------------------------------------------------------------------
# Task 17 — Chunk size enforcement on tree-sitter resolver path
# ---------------------------------------------------------------------------

_ASTCHUNK_MAX_CHUNK_SIZE = 1500  # mirrors the constant in tree_sitter.py


def _nonws_len(text: str) -> int:
    """Count non-whitespace characters."""
    return sum(1 for ch in text if not ch.isspace())


class TestChunkSizeLimit:
    """Tree-sitter resolver path must not produce chunks exceeding the size limit."""

    def _build_large_rust_file(self) -> str:
        """Build a Rust file with one very large function (>1500 non-ws chars)."""
        body_lines = "\n".join(f"    let var_{i}: i32 = {i};" for i in range(120))
        return f"pub fn large_function() {{\n{body_lines}\n}}\n"

    def test_large_rust_function_is_split_or_bounded(self, temp_repo):
        """A Rust function >1500 non-ws chars should be split into smaller chunks."""
        chunker = _get_chunker()
        source = self._build_large_rust_file()
        (temp_repo / "big.rs").write_text(source)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert rs_chunks, "No Rust chunks produced"

        # Strip enrichment header before measuring
        for c in rs_chunks:
            raw = c.content
            if raw.startswith("# File:"):
                # Skip 4 header lines (3 header + blank line)
                raw = "\n".join(raw.splitlines()[4:])
            size = _nonws_len(raw)
            assert size <= _ASTCHUNK_MAX_CHUNK_SIZE * 1.1, (
                f"Chunk exceeds size limit: {size} non-ws chars "
                f"(limit {_ASTCHUNK_MAX_CHUNK_SIZE})\n"
                f"Path: {c.path} lines {c.start_line}-{c.end_line}"
            )

    def test_small_rust_function_not_split(self, temp_repo):
        """A small Rust function must not be split (no false positives)."""
        chunker = _get_chunker()
        source = "pub fn add(a: i32, b: i32) -> i32 { a + b }\n"
        (temp_repo / "small.rs").write_text(source)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert len(rs_chunks) == 1, (
            f"Small function should be exactly 1 chunk, got {len(rs_chunks)}"
        )

    def test_python_large_function_size_limit(self, temp_repo):
        """Python astchunk path is already limited — verify it still holds after changes."""
        pytest.importorskip("astchunk", reason="astchunk not installed")
        chunker = _get_chunker()
        body = "\n".join(f"    x_{i} = {i}" for i in range(100))
        source = f"def big_fn():\n{body}\n"
        (temp_repo / "big.py").write_text(source)
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        for c in py_chunks:
            raw = c.content
            if raw.startswith("# File:"):
                raw = "\n".join(raw.splitlines()[4:])
            size = _nonws_len(raw)
            assert size <= _ASTCHUNK_MAX_CHUNK_SIZE * 1.1, (
                f"Python chunk exceeds size limit: {size} non-ws chars"
            )
