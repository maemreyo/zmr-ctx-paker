"""Phase 2 tests: reference extraction quality and multi-symbol extraction."""

import tempfile
from pathlib import Path
from typing import Any

import pytest


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
# Task 18 — Fix noisy extract_references()
# Local variable names and parameter names must NOT appear in symbols_referenced.
# Cross-file call targets and type names MUST appear.
# ---------------------------------------------------------------------------


class TestReferenceExtractionQuality:
    """symbols_referenced must contain cross-file references only."""

    # --- Rust ---

    RUST_SIMPLE_FN = """\
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
"""

    RUST_CALLS_ANOTHER = """\
pub fn process(data: Vec<u8>) -> String {
    let result = format_output(data);
    helper::transform(result)
}
"""

    RUST_WITH_TYPES = """\
use std::collections::HashMap;

pub fn build_map() -> HashMap<String, Vec<u8>> {
    let mut m = HashMap::new();
    m
}
"""

    def test_rust_params_not_in_references(self, temp_repo):
        """Local params (a, b) must not appear in symbols_referenced."""
        chunker = _get_chunker()
        (temp_repo / "lib.rs").write_text(self.RUST_SIMPLE_FN)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert rs_chunks
        all_refs = [r for c in rs_chunks for r in c.symbols_referenced]

        assert "a" not in all_refs, f"'a' (param) must not be in refs: {all_refs}"
        assert "b" not in all_refs, f"'b' (param) must not be in refs: {all_refs}"

    def test_rust_cross_file_calls_in_references(self, temp_repo):
        """Called functions from other modules must appear in symbols_referenced."""
        chunker = _get_chunker()
        (temp_repo / "lib.rs").write_text(self.RUST_CALLS_ANOTHER)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert rs_chunks
        all_refs = [r for c in rs_chunks for r in c.symbols_referenced]

        assert "format_output" in all_refs or "helper" in all_refs, (
            f"Cross-file call targets must be in refs: {all_refs}"
        )

    def test_rust_local_var_not_in_references(self, temp_repo):
        """Local 'result' variable must not be in symbols_referenced."""
        chunker = _get_chunker()
        (temp_repo / "lib.rs").write_text(self.RUST_CALLS_ANOTHER)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert rs_chunks
        all_refs = [r for c in rs_chunks for r in c.symbols_referenced]

        assert "result" not in all_refs, f"'result' (local var) must not be in refs: {all_refs}"

    # --- Python (resolver path via monkeypatch of astchunk) ---

    PYTHON_SIMPLE_FN = """\
def add(a, b):
    return a + b
"""

    PYTHON_CALLS_ANOTHER = """\
def process(data):
    result = format_output(data)
    return helper.transform(result)
"""

    def test_python_params_not_in_references(self, temp_repo, monkeypatch):
        """Python resolver path: params (a, b) must not be in symbols_referenced."""
        chunker = _get_chunker()
        monkeypatch.setattr(chunker, "_try_astchunk", lambda *a, **kw: None)
        (temp_repo / "ops.py").write_text(self.PYTHON_SIMPLE_FN)
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        assert py_chunks
        all_refs = [r for c in py_chunks for r in c.symbols_referenced]

        assert "a" not in all_refs, f"'a' (param) must not be in refs: {all_refs}"
        assert "b" not in all_refs, f"'b' (param) must not be in refs: {all_refs}"

    def test_python_cross_file_calls_in_references(self, temp_repo, monkeypatch):
        """Python resolver path: called functions must appear in symbols_referenced."""
        chunker = _get_chunker()
        monkeypatch.setattr(chunker, "_try_astchunk", lambda *a, **kw: None)
        (temp_repo / "ops.py").write_text(self.PYTHON_CALLS_ANOTHER)
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        assert py_chunks
        all_refs = [r for c in py_chunks for r in c.symbols_referenced]

        assert "format_output" in all_refs or "helper" in all_refs, (
            f"Cross-file call targets must be in refs: {all_refs}"
        )

    def test_python_local_var_not_in_references(self, temp_repo, monkeypatch):
        """Python resolver path: local 'result' variable must not be in references."""
        chunker = _get_chunker()
        monkeypatch.setattr(chunker, "_try_astchunk", lambda *a, **kw: None)
        (temp_repo / "ops.py").write_text(self.PYTHON_CALLS_ANOTHER)
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        assert py_chunks
        all_refs = [r for c in py_chunks for r in c.symbols_referenced]

        assert "result" not in all_refs, f"'result' (local var) must not be in refs: {all_refs}"


# ---------------------------------------------------------------------------
# Task 19 — Multi-symbol extraction for resolver path
# Class/struct/impl nodes must include method names in symbols_defined.
# ---------------------------------------------------------------------------


class TestMultiSymbolExtraction:
    """symbols_defined must include methods/functions defined inside a class/struct."""

    RUST_IMPL = """\
pub struct Calculator;

impl Calculator {
    pub fn add(&self, x: i32, y: i32) -> i32 { x + y }
    pub fn multiply(&self, x: i32, y: i32) -> i32 { x * y }
}
"""

    RUST_TRAIT = """\
pub trait Greeter {
    fn greet(&self) -> String;
    fn farewell(&self) -> String;
}
"""

    PYTHON_CLASS = """\
class Calculator:
    def add(self, x, y):
        return x + y

    def multiply(self, x, y):
        return x * y
"""

    TYPESCRIPT_CLASS = """\
export class Greeter {
    greet(): string { return 'hello'; }
    farewell(): string { return 'goodbye'; }
}
"""

    def test_rust_impl_includes_method_names(self, temp_repo):
        """impl Calculator chunk must have 'Calculator', 'add', 'multiply' in symbols_defined."""
        chunker = _get_chunker()
        (temp_repo / "calc.rs").write_text(self.RUST_IMPL)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        assert rs_chunks

        # Find the impl_item chunk (larger span — contains the method bodies).
        # Both struct_item and impl_item produce a 'Calculator' symbol; distinguish
        # by selecting the one with the widest line range.
        candidates = [c for c in rs_chunks if "Calculator" in c.symbols_defined]
        assert candidates, "No chunk with 'Calculator' found"
        impl_chunk = max(candidates, key=lambda c: c.end_line - c.start_line)

        assert "add" in impl_chunk.symbols_defined, (
            f"'add' must be in impl_chunk.symbols_defined: {impl_chunk.symbols_defined}"
        )
        assert "multiply" in impl_chunk.symbols_defined, (
            f"'multiply' must be in impl_chunk.symbols_defined: {impl_chunk.symbols_defined}"
        )

    def test_rust_trait_includes_method_signatures(self, temp_repo):
        """trait Greeter chunk must include 'greet' and 'farewell'."""
        chunker = _get_chunker()
        (temp_repo / "greeter.rs").write_text(self.RUST_TRAIT)
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith(".rs")]
        all_symbols = [s for c in rs_chunks for s in c.symbols_defined]

        assert "Greeter" in all_symbols, f"'Greeter' must be in symbols: {all_symbols}"
        assert "greet" in all_symbols, f"'greet' must be in symbols: {all_symbols}"
        assert "farewell" in all_symbols, f"'farewell' must be in symbols: {all_symbols}"

    def test_python_class_methods_via_resolver_path(self, temp_repo, monkeypatch):
        """Python class chunk (resolver fallback) must include method names."""
        chunker = _get_chunker()
        monkeypatch.setattr(chunker, "_try_astchunk", lambda *a, **kw: None)
        (temp_repo / "calc.py").write_text(self.PYTHON_CLASS)
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        all_symbols = [s for c in py_chunks for s in c.symbols_defined]

        assert "Calculator" in all_symbols, f"'Calculator' not found: {all_symbols}"
        assert "add" in all_symbols, f"'add' not found: {all_symbols}"
        assert "multiply" in all_symbols, f"'multiply' not found: {all_symbols}"

    def test_typescript_class_methods_via_resolver_path(self, temp_repo, monkeypatch):
        """TypeScript class chunk (resolver fallback) must include method names."""
        chunker = _get_chunker()
        monkeypatch.setattr(chunker, "_try_astchunk", lambda *a, **kw: None)
        (temp_repo / "greeter.ts").write_text(self.TYPESCRIPT_CLASS)
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith(".ts")]
        all_symbols = [s for c in ts_chunks for s in c.symbols_defined]

        assert "Greeter" in all_symbols, f"'Greeter' not found: {all_symbols}"
        assert "greet" in all_symbols or "farewell" in all_symbols, (
            f"Method names must be in symbols: {all_symbols}"
        )
