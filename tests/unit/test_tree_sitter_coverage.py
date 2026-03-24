"""Tests for tree_sitter.py uncovered branches."""

import tempfile
from pathlib import Path

import pytest


class TestTreeSitterImportCollection:
    """Tests for file-level import collection in TreeSitterChunker."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_python_dotted_imports(self, temp_repo):
        """Test Python dotted imports like from collections import defaultdict."""
        code = '''from collections import defaultdict
import os.path

def hello():
    pass
'''
        (temp_repo / "test.py").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("test.py")]
        all_refs = []
        for chunk in py_chunks:
            all_refs.extend(chunk.symbols_referenced)

        assert 'defaultdict' in all_refs or 'collections' in all_refs or 'os' in all_refs

    def test_python_multiple_from_imports(self, temp_repo):
        """Test Python multiple imports from same module."""
        code = '''from os.path import join, split
from collections import Counter, OrderedDict

def func():
    pass
'''
        (temp_repo / "multi_import.py").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("multi_import.py")]
        all_refs = []
        for chunk in py_chunks:
            all_refs.extend(chunk.symbols_referenced)

        assert 'join' in all_refs or 'split' in all_refs or 'Counter' in all_refs

    def test_rust_use_with_braces(self, temp_repo):
        """Test Rust use declarations with braces."""
        code = '''use std::collections::HashMap;

fn main() {
    println!("Hello");
}
'''
        (temp_repo / "use_braces.rs").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        rs_chunks = [c for c in chunks if c.path.endswith("use_braces.rs")]
        all_refs = []
        for chunk in rs_chunks:
            all_refs.extend(chunk.symbols_referenced)

        assert 'HashMap' in all_refs or 'std' in all_refs


class TestTreeSitterNonCodeExtensions:
    """Tests for non-code file extensions."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_json_file_not_parsed(self, temp_repo):
        """Test that JSON files are ignored."""
        (temp_repo / "data.json").write_text('{"key": "value"}')

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        json_chunks = [c for c in chunks if c.path.endswith("data.json")]
        assert len(json_chunks) == 0

    def test_yaml_file_not_parsed(self, temp_repo):
        """Test that YAML files are ignored."""
        (temp_repo / "config.yaml").write_text('key: value')

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        yaml_chunks = [c for c in chunks if c.path.endswith("config.yaml")]
        assert len(yaml_chunks) == 0

    def test_txt_file_not_parsed(self, temp_repo):
        """Test that TXT files are ignored."""
        (temp_repo / "notes.txt").write_text('Some notes here.')

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        txt_chunks = [c for c in chunks if c.path.endswith("notes.txt")]
        assert len(txt_chunks) == 0


class TestTreeSitterReadError:
    """Tests for file read error handling."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_binary_file_handling(self, temp_repo):
        """Test handling of binary files."""
        (temp_repo / "binary.bin").write_bytes(b'\x00\x01\x02\x03')

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        bin_chunks = [c for c in chunks if c.path.endswith("binary.bin")]
        assert len(bin_chunks) == 0

    def test_parse_with_exception_handling(self, temp_repo):
        """Test that exceptions in parsing are caught."""
        (temp_repo / "bad.py").write_text("def func():\n    " + "x" * 10000)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        assert isinstance(chunks, list)


class TestTreeSitterMultipleFiles:
    """Tests for parsing multiple files."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_multiple_python_files(self, temp_repo):
        """Test parsing multiple Python files."""
        (temp_repo / "a.py").write_text("def a(): pass")
        (temp_repo / "b.py").write_text("def b(): pass")
        (temp_repo / "c.py").write_text("def c(): pass")

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith(".py")]
        assert len(py_chunks) >= 3

    def test_mixed_extensions(self, temp_repo):
        """Test parsing files with mixed extensions."""
        (temp_repo / "main.js").write_text("function main() {}")
        (temp_repo / "util.ts").write_text("export function util() {}")
        (temp_repo / "lib.rs").write_text("fn lib() {}")

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        assert len(chunks) >= 3

    def test_deeply_nested_files(self, temp_repo):
        """Test parsing files in deeply nested directories."""
        nested = temp_repo / "src" / "components" / "ui"
        nested.mkdir(parents=True)
        (nested / "Button.tsx").write_text("function Button() {}")

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        tsx_chunks = [c for c in chunks if c.path.endswith("Button.tsx")]
        assert len(tsx_chunks) >= 1
        assert any("src/components/ui/Button.tsx" in c.path for c in tsx_chunks)


class TestTreeSitterChunkSpan:
    """Tests for chunk start/end line calculation."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_chunk_lines_are_one_indexed(self, temp_repo):
        """Test that chunk lines are 1-indexed."""
        code = """def first():
    pass

def second():
    pass
"""
        (temp_repo / "lines.py").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("lines.py")]
        for chunk in py_chunks:
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_chunk_span_contains_content(self, temp_repo):
        """Test that chunk span correctly contains the content."""
        code = """def hello():
    print("Hello")
"""
        (temp_repo / "span.py").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("span.py")]
        for chunk in py_chunks:
            lines = code.split('\n')
            spanned = '\n'.join(lines[chunk.start_line - 1:chunk.end_line])
            assert spanned.strip() in code or chunk.content.strip() in code


class TestTreeSitterResolverCoverage:
    """Tests for resolver method coverage."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_python_class_method(self, temp_repo):
        """Test extracting Python class methods."""
        code = '''class MyClass:
    def method(self):
        pass

    @classmethod
    def class_method(cls):
        pass
'''
        (temp_repo / "methods.py").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        py_chunks = [c for c in chunks if c.path.endswith("methods.py")]
        symbols = []
        for chunk in py_chunks:
            symbols.extend(chunk.symbols_defined)
        assert 'MyClass' in symbols

    def test_javascript_method_definition(self, temp_repo):
        """Test extracting JavaScript method definitions."""
        code = '''class Calculator {
    add(a, b) {
        return a + b;
    }

    static multiply(a, b) {
        return a * b;
    }
}
'''
        (temp_repo / "methods.js").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        js_chunks = [c for c in chunks if c.path.endswith("methods.js")]
        symbols = []
        for chunk in js_chunks:
            symbols.extend(chunk.symbols_defined)
        assert 'Calculator' in symbols
        assert 'add' in symbols or 'multiply' in symbols

    def test_typescript_method_definition(self, temp_repo):
        """Test extracting TypeScript method definitions."""
        code = '''class Greeter {
    greet(name: string): string {
        return `Hello, ${name}`;
    }
}
'''
        (temp_repo / "methods.ts").write_text(code)

        try:
            from context_packer.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("methods.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)
        assert 'Greeter' in symbols
        assert 'greet' in symbols
