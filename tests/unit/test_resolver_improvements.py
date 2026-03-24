"""Integration tests for resolver improvements."""

import tempfile
from pathlib import Path

import pytest


class TestPythonDecoratorExtraction:
    """Tests for Python decorated function/class extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_decorated_function(self, temp_repo):
        """Test that decorated functions are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
@decorator
def decorated_func():
    pass

@classmethod
class DecoratedClass:
    pass
'''
        (temp_repo / "decorated.py").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("decorated.py")]
        symbol_names = []
        for chunk in py_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'decorated_func' in symbol_names, \
            f"decorated_func should be extracted, got: {symbol_names}"
        assert 'DecoratedClass' in symbol_names, \
            f"DecoratedClass should be extracted, got: {symbol_names}"

    def test_extract_decorated_async_function(self, temp_repo):
        """Test that decorated async functions are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
@asyncDecorator
async def async_decorated():
    await something()
'''
        (temp_repo / "async_decorated.py").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("async_decorated.py")]
        symbol_names = []
        for chunk in py_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'async_decorated' in symbol_names, \
            f"async_decorated should be extracted, got: {symbol_names}"


class TestJavaScriptExportExtraction:
    """Tests for JavaScript export statement extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_export_function(self, temp_repo):
        """Test that exported functions are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
export function exportedFunc() {
    return 1;
}

export class ExportedClass {
    constructor() {}
}
'''
        (temp_repo / "exports.js").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("exports.js")]
        symbol_names = []
        for chunk in js_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'exportedFunc' in symbol_names, \
            f"exportedFunc should be extracted, got: {symbol_names}"
        assert 'ExportedClass' in symbol_names, \
            f"ExportedClass should be extracted, got: {symbol_names}"

    def test_extract_default_export(self, temp_repo):
        """Test that default exported functions are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
export default function defaultFunc() {
    return 42;
}
'''
        (temp_repo / "default_export.js").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("default_export.js")]
        symbol_names = []
        for chunk in js_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'defaultFunc' in symbol_names, \
            f"defaultFunc should be extracted, got: {symbol_names}"


class TestTypeScriptInterfaceExtraction:
    """Tests for TypeScript interface/type extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_typescript_interface(self, temp_repo):
        """Test that TypeScript interfaces are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
interface User {
    name: string;
    age: number;
}

type ID = string | number;

enum Status {
    Active,
    Inactive
}
'''
        (temp_repo / "types.ts").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("types.ts")]
        symbol_names = []
        for chunk in ts_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'User' in symbol_names, \
            f"User interface should be extracted, got: {symbol_names}"
        assert 'ID' in symbol_names, \
            f"ID type alias should be extracted, got: {symbol_names}"
        assert 'Status' in symbol_names, \
            f"Status enum should be extracted, got: {symbol_names}"

    def test_extract_export_interface(self, temp_repo):
        """Test that exported TypeScript interfaces are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
export interface ExportedInterface {
    id: number;
}
'''
        (temp_repo / "exported_types.ts").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("exported_types.ts")]
        symbol_names = []
        for chunk in ts_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'ExportedInterface' in symbol_names, \
            f"ExportedInterface should be extracted, got: {symbol_names}"


class TestRustImplAndTraitExtraction:
    """Tests for Rust impl/trait extraction."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_extract_rust_impl_block(self, temp_repo):
        """Test that impl blocks are extracted with correct type name."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
struct Foo {
    value: i32,
}

impl Foo {
    pub fn new() -> Self {
        Foo { value: 0 }
    }
}
'''
        (temp_repo / "impl_test.rs").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("impl_test.rs")]
        symbol_names = []
        for chunk in rs_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'Foo' in symbol_names, \
            f"Foo struct should be extracted, got: {symbol_names}"
        assert 'new' in symbol_names, \
            f"new method should be extracted, got: {symbol_names}"

    def test_extract_rust_generic_impl(self, temp_repo):
        """Test that generic impl blocks are extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
impl<T> Vec<T> {
    pub fn new() -> Vec<T> {
        Vec
    }
}
'''
        (temp_repo / "generic_impl.rs").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("generic_impl.rs")]
        symbol_names = []
        for chunk in rs_chunks:
            symbol_names.extend(chunk.symbols_defined)

        assert 'new' in symbol_names, \
            f"new method should be extracted, got: {symbol_names}"


class TestGlobalChunkDeduplication:
    """Tests for global chunk deduplication across entire parse."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_no_duplicate_chunks_across_files(self, temp_repo):
        """Test that there are no duplicate chunks across multiple files."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        (temp_repo / "file1.py").write_text('def foo(): pass')
        (temp_repo / "file2.py").write_text('def foo(): pass')

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        seen = set()
        for chunk in chunks:
            key = (chunk.path, chunk.start_line, chunk.end_line, chunk.content[:50])
            assert key not in seen, f"Duplicate chunk: {chunk.path}"
            seen.add(key)


class TestRustScopedUseDeclarations:
    """Tests for Rust scoped use declarations (e.g., std::collections::HashMap)."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_rust_use_scoped_identifiers(self, temp_repo):
        """Test that scoped use declarations are properly extracted."""
        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        code = '''
use std::collections::{HashMap, HashSet};
use std::io::Read;

fn read_file() {
    let mut file = std::fs::File::open("test").unwrap();
    let mut contents = String::new();
    file.read_to_string(&mut contents).unwrap();
}
'''
        (temp_repo / "scoped_use.rs").write_text(code)
        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("scoped_use.rs")]
        all_refs = []
        for chunk in rs_chunks:
            all_refs.extend(chunk.symbols_referenced)

        assert 'HashMap' in all_refs or 'HashSet' in all_refs or 'Read' in all_refs, \
            f"Scoped imports should be extracted, got: {all_refs}"
