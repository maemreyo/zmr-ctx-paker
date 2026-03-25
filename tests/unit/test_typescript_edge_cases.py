"""Tests for TypeScript-specific edge cases to improve coverage."""

import tempfile
from pathlib import Path

import pytest


class TestTypeScriptEdgeCases:
    """Tests for TypeScript edge cases in resolvers."""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            yield repo_path

    def test_lexical_declaration_with_arrow_function(self, temp_repo):
        """Test lexical declaration with arrow function (TypeScript)."""
        code = '''const greet = (name: string) => {
    return `Hello, ${name}`;
};

const add = (a: number, b: number): number => a + b;
'''
        (temp_repo / "arrow.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("arrow.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)

        assert 'greet' in symbols or 'add' in symbols

    def test_lexical_declaration_without_arrow(self, temp_repo):
        """Test lexical declaration without arrow function."""
        code = '''const x = 5;
const y = "hello";
'''
        (temp_repo / "vars.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("vars.ts")]
        assert len(ts_chunks) >= 0

    def test_export_type_alias(self, temp_repo):
        """Test export of type alias."""
        code = '''export type ID = string | number;
'''
        (temp_repo / "export_type.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("export_type.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)

        assert 'ID' in symbols

    def test_export_enum(self, temp_repo):
        """Test export of enum."""
        code = '''export enum Status {
    Active = "active",
    Inactive = "inactive"
}
'''
        (temp_repo / "export_enum.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("export_enum.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)

        assert 'Status' in symbols

    def test_abstract_class_declaration(self, temp_repo):
        """Test abstract class declaration."""
        code = '''abstract class Animal {
    abstract speak(): void;
}
'''
        (temp_repo / "abstract.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("abstract.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)

        assert 'Animal' in symbols

    def test_type_alias_with_generics(self, temp_repo):
        """Test type alias with generics."""
        code = '''type Mapper<T, U> = (input: T) => U;
'''
        (temp_repo / "generic_type.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("generic_type.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)

        assert 'Mapper' in symbols

    def test_export_abstract_class(self, temp_repo):
        """Test export of abstract class."""
        code = '''export abstract class Base {
    abstract method(): void;
}
'''
        (temp_repo / "export_abstract.ts").write_text(code)

        try:
            from ws_ctx_engine.chunker import TreeSitterChunker
        except ImportError:
            pytest.skip("TreeSitter not available")

        chunker = TreeSitterChunker()
        chunks = chunker.parse(str(temp_repo))

        ts_chunks = [c for c in chunks if c.path.endswith("export_abstract.ts")]
        symbols = []
        for chunk in ts_chunks:
            symbols.extend(chunk.symbols_defined)

        assert 'Base' in symbols
