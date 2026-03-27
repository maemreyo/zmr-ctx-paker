"""Tests for SymbolIndex — resolves symbol names and module paths to node IDs.

TDD: all tests written BEFORE implementation (RED phase).
"""

import pytest

from ws_ctx_engine.graph.builder import Edge, Node
from ws_ctx_engine.models.models import CodeChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file_node(path: str, language: str = "python") -> Node:
    return Node(id=path, kind="file", name=path.rsplit("/", 1)[-1], file=path, language=language)


def _make_sym_node(file_path: str, symbol: str, kind: str = "function") -> Node:
    node_id = f"{file_path}#{symbol}"
    return Node(id=node_id, kind=kind, name=symbol, file=file_path, language="python")


def _make_chunk(
    path: str,
    symbols_defined: list[str] | None = None,
    symbols_referenced: list[str] | None = None,
    language: str = "python",
) -> CodeChunk:
    return CodeChunk(
        path=path,
        start_line=1,
        end_line=10,
        content="# code",
        symbols_defined=symbols_defined or [],
        symbols_referenced=symbols_referenced or [],
        language=language,
    )


# ---------------------------------------------------------------------------
# SymbolIndex import
# ---------------------------------------------------------------------------


class TestSymbolIndexImport:
    def test_import(self) -> None:
        from ws_ctx_engine.graph.symbol_index import SymbolIndex  # noqa: F401


# ---------------------------------------------------------------------------
# resolve_symbol
# ---------------------------------------------------------------------------


class TestResolveSymbol:
    def test_resolve_symbol_single_match(self) -> None:
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("src/auth.py")
        sym_node = _make_sym_node("src/auth.py", "authenticate")
        index = SymbolIndex.build([file_node, sym_node], [])

        result = index.resolve_symbol("authenticate")
        assert result == ["src/auth.py#authenticate"]

    def test_resolve_symbol_multiple_definitions(self) -> None:
        """Same symbol name in two files returns both IDs."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        sym_a = _make_sym_node("src/auth.py", "validate")
        sym_b = _make_sym_node("src/utils.py", "validate")
        index = SymbolIndex.build(
            [_make_file_node("src/auth.py"), sym_a, _make_file_node("src/utils.py"), sym_b],
            [],
        )

        result = index.resolve_symbol("validate")
        assert set(result) == {"src/auth.py#validate", "src/utils.py#validate"}

    def test_resolve_symbol_not_found(self) -> None:
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        index = SymbolIndex.build([_make_file_node("src/auth.py")], [])
        result = index.resolve_symbol("nonexistent_function")
        assert result == []

    def test_resolve_symbol_empty_index(self) -> None:
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        index = SymbolIndex.build([], [])
        assert index.resolve_symbol("foo") == []


# ---------------------------------------------------------------------------
# resolve_module
# ---------------------------------------------------------------------------


class TestResolveModule:
    def test_resolve_module_exact_dotted_name(self) -> None:
        """Full dotted path like 'ws_ctx_engine.chunker.tree_sitter' matches exactly."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("src/ws_ctx_engine/chunker/tree_sitter.py")
        index = SymbolIndex.build([file_node], [])

        result = index.resolve_module("ws_ctx_engine.chunker.tree_sitter")
        assert result == "src/ws_ctx_engine/chunker/tree_sitter.py"

    def test_resolve_module_short_name_stem(self) -> None:
        """Just filename stem 'tree_sitter' resolves to the file node."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("src/ws_ctx_engine/chunker/tree_sitter.py")
        index = SymbolIndex.build([file_node], [])

        result = index.resolve_module("tree_sitter")
        assert result == "src/ws_ctx_engine/chunker/tree_sitter.py"

    def test_resolve_module_partial_dotted_name(self) -> None:
        """Partial dotted path 'chunker.tree_sitter' also resolves."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("src/ws_ctx_engine/chunker/tree_sitter.py")
        index = SymbolIndex.build([file_node], [])

        result = index.resolve_module("chunker.tree_sitter")
        assert result == "src/ws_ctx_engine/chunker/tree_sitter.py"

    def test_resolve_module_not_found(self) -> None:
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        index = SymbolIndex.build([_make_file_node("src/auth.py")], [])
        result = index.resolve_module("completely.nonexistent.module")
        assert result is None

    def test_resolve_module_longest_match_wins(self) -> None:
        """When two file names could match, the longest/most-specific match wins."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_a = _make_file_node("src/ws_ctx_engine/graph/builder.py")
        file_b = _make_file_node("src/ws_ctx_engine/graph/graph_builder.py")
        index = SymbolIndex.build([file_a, file_b], [])

        # 'graph.builder' should match 'graph/builder.py' (more specific path segment match)
        result = index.resolve_module("graph.builder")
        assert result == "src/ws_ctx_engine/graph/builder.py"

    def test_resolve_module_no_src_prefix_required(self) -> None:
        """Path without src/ prefix also resolves correctly."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("ws_ctx_engine/chunker/tree_sitter.py")
        index = SymbolIndex.build([file_node], [])

        result = index.resolve_module("ws_ctx_engine.chunker.tree_sitter")
        assert result == "ws_ctx_engine/chunker/tree_sitter.py"


# ---------------------------------------------------------------------------
# build() method
# ---------------------------------------------------------------------------


class TestSymbolIndexBuild:
    def test_build_from_empty(self) -> None:
        """No nodes → both internal maps are empty."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        index = SymbolIndex.build([], [])
        assert index.resolve_symbol("anything") == []
        assert index.resolve_module("anything") is None

    def test_build_ignores_file_nodes_in_name_index(self) -> None:
        """File nodes must NOT appear in the symbol name-to-ids mapping."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("src/auth.py")
        index = SymbolIndex.build([file_node], [])

        # The filename without extension should be a module path, not a symbol
        # so resolve_symbol("auth") returns [] (no symbol named 'auth')
        result = index.resolve_symbol("auth.py")
        assert result == []

    def test_build_multiple_chunks_same_file(self) -> None:
        """Multiple chunks from same file produce same file node, symbols deduplicated."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = _make_file_node("src/auth.py")
        sym_a = _make_sym_node("src/auth.py", "login")
        sym_b = _make_sym_node("src/auth.py", "logout")
        index = SymbolIndex.build([file_node, sym_a, sym_b], [])

        assert index.resolve_symbol("login") == ["src/auth.py#login"]
        assert index.resolve_symbol("logout") == ["src/auth.py#logout"]

    def test_build_non_python_file_node_registered_as_module(self) -> None:
        """Non-Python files (e.g. .ts) are still registered in the module map by stem."""
        from ws_ctx_engine.graph.symbol_index import SymbolIndex

        file_node = Node(
            id="src/utils.ts",
            kind="file",
            name="utils.ts",
            file="src/utils.ts",
            language="typescript",
        )
        index = SymbolIndex.build([file_node], [])

        result = index.resolve_module("utils")
        assert result == "src/utils.ts"
