"""Phase 3 tests: graph bridge — node_id normalization, chunks_to_graph, validation."""

import re
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(path: str, symbols: list[str], language: str = "python"):
    """Create a minimal CodeChunk for testing."""
    from ws_ctx_engine.models.models import CodeChunk

    return CodeChunk(
        path=path,
        start_line=1,
        end_line=10,
        content="# code",
        symbols_defined=symbols,
        symbols_referenced=[],
        language=language,
    )


# ---------------------------------------------------------------------------
# Task 7 — node_id normalization
# ---------------------------------------------------------------------------


class TestNodeIdNormalization:
    """normalize_node_id must produce canonical, stable, portable IDs."""

    def test_import(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id  # noqa: F401

    def test_file_only_returns_relative_path(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        result = normalize_node_id("src/auth.py")
        assert result == "src/auth.py"

    def test_forward_slashes_on_all_platforms(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        result = normalize_node_id("src\\utils\\helpers.py")
        assert "\\" not in result
        assert "/" in result

    def test_dotslash_stripped(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        result = normalize_node_id("./src/auth.py")
        assert not result.startswith("./")
        assert result.startswith("src/")

    def test_symbol_appended_with_hash(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        result = normalize_node_id("src/auth.py", "authenticate")
        assert result == "src/auth.py#authenticate"

    def test_symbol_sanitized(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        result = normalize_node_id("src/auth.py", "<lambda>")
        assert "#" in result
        # Symbol part must be alphanumeric + underscore only
        _, sym_part = result.split("#", 1)
        assert re.match(r"^[a-zA-Z0-9_]+$", sym_part), (
            f"Symbol part not sanitized: {sym_part!r}"
        )

    def test_dunder_method_sanitized(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        result = normalize_node_id("src/models.py", "__init__")
        assert "#" in result
        _, sym = result.split("#", 1)
        assert re.match(r"^[a-zA-Z0-9_]+$", sym)

    def test_same_inputs_produce_same_id(self):
        from ws_ctx_engine.graph.node_id import normalize_node_id

        a = normalize_node_id("src/auth.py", "foo")
        b = normalize_node_id("src/auth.py", "foo")
        assert a == b


# ---------------------------------------------------------------------------
# Task 8 — chunks_to_graph
# ---------------------------------------------------------------------------


class TestChunksToGraph:
    """chunks_to_graph must produce the correct nodes and CONTAINS edges."""

    def test_import(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph  # noqa: F401

    def test_empty_input_returns_empty(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        nodes, edges = chunks_to_graph([])
        assert nodes == []
        assert edges == []

    def test_single_chunk_produces_file_node(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [_make_chunk("src/auth.py", ["authenticate"])]
        nodes, edges = chunks_to_graph(chunks)

        file_ids = [n.id for n in nodes if n.kind == "file"]
        assert any("src/auth.py" in f for f in file_ids), f"No file node: {file_ids}"

    def test_single_chunk_produces_symbol_node(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [_make_chunk("src/auth.py", ["authenticate"])]
        nodes, edges = chunks_to_graph(chunks)

        sym_ids = [n.id for n in nodes if n.kind != "file"]
        assert any("authenticate" in s for s in sym_ids), f"No symbol node: {sym_ids}"

    def test_contains_edge_created(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [_make_chunk("src/auth.py", ["authenticate"])]
        nodes, edges = chunks_to_graph(chunks)

        contains_edges = [e for e in edges if e.relation == "CONTAINS"]
        assert contains_edges, "No CONTAINS edge found"
        # Edge should connect file node to symbol node
        file_ids = {n.id for n in nodes if n.kind == "file"}
        assert any(e.src in file_ids for e in contains_edges), (
            "CONTAINS edge src is not a file node"
        )

    def test_multiple_symbols_produce_multiple_edges(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [_make_chunk("src/calc.py", ["Calculator", "add", "multiply"])]
        nodes, edges = chunks_to_graph(chunks)

        contains_edges = [e for e in edges if e.relation == "CONTAINS"]
        assert len(contains_edges) >= 3, (
            f"Expected >=3 CONTAINS edges, got {len(contains_edges)}"
        )

    def test_class_symbol_gets_class_kind(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [_make_chunk("src/models.py", ["UserModel"])]
        nodes, edges = chunks_to_graph(chunks)

        sym_nodes = [n for n in nodes if n.kind == "class"]
        assert sym_nodes, "PascalCase symbol should be 'class' kind"
        assert any("UserModel" in n.id for n in sym_nodes)

    def test_function_symbol_gets_function_kind(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [_make_chunk("src/utils.py", ["process_data"])]
        nodes, edges = chunks_to_graph(chunks)

        func_nodes = [n for n in nodes if n.kind == "function"]
        assert func_nodes, "snake_case symbol should be 'function' kind"

    def test_deduplication_across_chunks(self):
        """Same file should produce exactly one file node even with multiple chunks."""
        from ws_ctx_engine.graph.builder import chunks_to_graph

        chunks = [
            _make_chunk("src/auth.py", ["login"]),
            _make_chunk("src/auth.py", ["logout"]),
        ]
        nodes, edges = chunks_to_graph(chunks)

        file_nodes = [n for n in nodes if n.kind == "file" and "auth.py" in n.id]
        assert len(file_nodes) == 1, (
            f"Expected 1 file node for auth.py, got {len(file_nodes)}: {[n.id for n in file_nodes]}"
        )


# ---------------------------------------------------------------------------
# Task 9 — graph validation
# ---------------------------------------------------------------------------


class TestGraphValidation:
    """validate_graph must catch structural errors before ingestion."""

    def test_import(self):
        from ws_ctx_engine.graph.validation import validate_graph  # noqa: F401

    def test_valid_graph_passes(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph
        from ws_ctx_engine.graph.validation import validate_graph

        chunks = [_make_chunk("src/auth.py", ["authenticate"])]
        nodes, edges = chunks_to_graph(chunks)
        result = validate_graph(nodes, edges)

        assert result.is_valid, f"Valid graph rejected: {result.errors}"

    def test_empty_graph_is_valid(self):
        from ws_ctx_engine.graph.validation import validate_graph

        result = validate_graph([], [])
        assert result.is_valid

    def test_duplicate_node_ids_detected(self):
        from ws_ctx_engine.graph.builder import Node
        from ws_ctx_engine.graph.validation import validate_graph

        node1 = Node(id="src/auth.py", kind="file", name="auth.py", file="src/auth.py", language="python")
        node2 = Node(id="src/auth.py", kind="file", name="auth.py", file="src/auth.py", language="python")
        result = validate_graph([node1, node2], [])

        assert not result.is_valid
        assert any("Duplicate" in e for e in result.errors)

    def test_dangling_edge_src_detected(self):
        from ws_ctx_engine.graph.builder import Edge, Node
        from ws_ctx_engine.graph.validation import validate_graph

        node = Node(id="src/auth.py#authenticate", kind="function", name="authenticate",
                    file="src/auth.py", language="python")
        bad_edge = Edge(src="src/missing.py", relation="CONTAINS", dst="src/auth.py#authenticate")
        result = validate_graph([node], [bad_edge])

        assert not result.is_valid
        assert any("src" in e.lower() or "missing" in e.lower() for e in result.errors)

    def test_dangling_edge_dst_detected(self):
        from ws_ctx_engine.graph.builder import Edge, Node
        from ws_ctx_engine.graph.validation import validate_graph

        node = Node(id="src/auth.py", kind="file", name="auth.py",
                    file="src/auth.py", language="python")
        bad_edge = Edge(src="src/auth.py", relation="CONTAINS", dst="src/auth.py#ghost")
        result = validate_graph([node], [bad_edge])

        assert not result.is_valid
        assert any("ghost" in e.lower() or "dst" in e.lower() for e in result.errors)

    def test_orphan_symbol_produces_warning(self):
        from ws_ctx_engine.graph.builder import Node
        from ws_ctx_engine.graph.validation import validate_graph

        orphan = Node(id="src/auth.py#authenticate", kind="function",
                      name="authenticate", file="src/auth.py", language="python")
        result = validate_graph([orphan], [])

        # Orphan is a warning, not an error — graph should still be valid
        assert result.is_valid
        assert result.warnings  # must warn about the orphan

    def test_valid_nodes_no_warnings(self):
        from ws_ctx_engine.graph.builder import chunks_to_graph
        from ws_ctx_engine.graph.validation import validate_graph

        chunks = [_make_chunk("src/auth.py", ["authenticate"])]
        nodes, edges = chunks_to_graph(chunks)
        result = validate_graph(nodes, edges)

        assert not result.errors
        assert not result.warnings


# ---------------------------------------------------------------------------
# Task 10 — extract_edges on TreeSitterChunker
# ---------------------------------------------------------------------------


class TestExtractEdges:
    """TreeSitterChunker.extract_edges must return CONTAINS Edge tuples."""

    def test_extract_edges_method_exists(self):
        from ws_ctx_engine.chunker import TreeSitterChunker

        chunker = TreeSitterChunker()
        assert hasattr(chunker, "extract_edges")

    def test_extract_edges_returns_edges(self):
        from ws_ctx_engine.chunker import TreeSitterChunker

        chunker = TreeSitterChunker()
        code = "def foo(): pass\ndef bar(): pass\n"
        edges = chunker.extract_edges(code, "python", "src/utils.py")

        assert edges, "extract_edges must return edges"
        for e in edges:
            assert e.relation == "CONTAINS", f"Expected CONTAINS edge, got {e.relation}"

    def test_extract_edges_src_is_filepath(self):
        from ws_ctx_engine.chunker import TreeSitterChunker

        chunker = TreeSitterChunker()
        code = "pub fn hello() {}\n"
        edges = chunker.extract_edges(code, "rust", "src/lib.rs")

        assert edges
        assert all("lib.rs" in e.src for e in edges)

    def test_extract_edges_dst_contains_symbol(self):
        from ws_ctx_engine.chunker import TreeSitterChunker

        chunker = TreeSitterChunker()
        code = "def authenticate(user, pwd): pass\n"
        edges = chunker.extract_edges(code, "python", "src/auth.py")

        dst_names = [e.dst for e in edges]
        assert any("authenticate" in d for d in dst_names), (
            f"Expected 'authenticate' in edges DSTs: {dst_names}"
        )

    def test_extract_edges_empty_code_returns_empty(self):
        from ws_ctx_engine.chunker import TreeSitterChunker

        chunker = TreeSitterChunker()
        edges = chunker.extract_edges("", "python", "src/empty.py")
        assert edges == []

    def test_end_to_end_chunker_to_graph(self):
        """Full pipeline: parse file → extract edges → validate graph."""
        from ws_ctx_engine.chunker import TreeSitterChunker
        from ws_ctx_engine.graph.builder import chunks_to_graph
        from ws_ctx_engine.graph.validation import validate_graph

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "auth.py").write_text(
                "def login(user, pwd):\n    return True\n\n"
                "def logout(user):\n    return True\n"
            )
            (repo / "utils.py").write_text(
                "def hash_password(pwd):\n    return pwd\n"
            )

            chunker = TreeSitterChunker()
            chunks = chunker.parse(str(repo))
            assert chunks, "No chunks produced"

            nodes, edges = chunks_to_graph(chunks)
            result = validate_graph(nodes, edges)

            assert result.is_valid, f"Graph is invalid: {result.errors}"
            symbol_ids = {n.id for n in nodes if n.kind != "file"}
            assert any("login" in s for s in symbol_ids), (
                f"'login' not found in symbols: {symbol_ids}"
            )


# ---------------------------------------------------------------------------
# Sub-phase 2a — chunks_to_full_graph (CALLS + IMPORTS edges)
# ---------------------------------------------------------------------------


def _make_chunk_with_refs(
    path: str,
    symbols_defined: list[str],
    symbols_referenced: list[str],
    language: str = "python",
) -> "object":
    from ws_ctx_engine.models.models import CodeChunk

    return CodeChunk(
        path=path,
        start_line=1,
        end_line=20,
        content="# code",
        symbols_defined=symbols_defined,
        symbols_referenced=symbols_referenced,
        language=language,
    )


class TestChunksToFullGraph:
    """chunks_to_full_graph must emit CONTAINS + CALLS + IMPORTS edges."""

    def test_import(self) -> None:
        from ws_ctx_engine.graph.builder import chunks_to_full_graph  # noqa: F401

    def test_chunks_to_full_graph_contains_all_contains_edges(self) -> None:
        """CONTAINS edges from chunks_to_graph() must all be present."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        chunks = [_make_chunk_with_refs("src/auth.py", ["login", "logout"], [])]
        nodes, edges = chunks_to_full_graph(chunks)

        contains_edges = [e for e in edges if e.relation == "CONTAINS"]
        assert len(contains_edges) == 2, f"Expected 2 CONTAINS edges, got {len(contains_edges)}"

    def test_chunks_to_full_graph_emits_calls_edge(self) -> None:
        """A chunk with symbols_referenced matching a defined symbol → CALLS edge."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        # src/main.py references 'login' which is defined in src/auth.py
        chunks = [
            _make_chunk_with_refs("src/auth.py", ["login"], []),
            _make_chunk_with_refs("src/main.py", [], ["login"]),
        ]
        nodes, edges = chunks_to_full_graph(chunks)

        calls_edges = [e for e in edges if e.relation == "CALLS"]
        assert calls_edges, "Expected at least one CALLS edge"
        # The CALLS edge must go FROM the file that references TO the defined symbol
        assert any(
            "main.py" in e.src and "login" in e.dst for e in calls_edges
        ), f"No CALLS edge from main.py to login: {[(e.src, e.dst) for e in calls_edges]}"

    def test_chunks_to_full_graph_emits_imports_edge(self) -> None:
        """A chunk with an import name matching a file → IMPORTS edge."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        # src/main.py references module 'auth' which matches src/auth.py
        chunks = [
            _make_chunk_with_refs("src/auth.py", ["login"], []),
            _make_chunk_with_refs("src/main.py", [], ["auth"]),
        ]
        nodes, edges = chunks_to_full_graph(chunks)

        imports_edges = [e for e in edges if e.relation == "IMPORTS"]
        assert imports_edges, "Expected at least one IMPORTS edge"
        assert any(
            "main.py" in e.src and "auth.py" in e.dst for e in imports_edges
        ), f"No IMPORTS from main.py → auth.py: {[(e.src, e.dst) for e in imports_edges]}"

    def test_chunks_to_full_graph_no_self_imports(self) -> None:
        """A file must not have an IMPORTS edge pointing to itself."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        chunks = [_make_chunk_with_refs("src/auth.py", ["login"], ["auth"])]
        nodes, edges = chunks_to_full_graph(chunks)

        for e in edges:
            if e.relation == "IMPORTS":
                assert e.src != e.dst, f"Self-import detected: {e}"

    def test_chunks_to_full_graph_deduplicates_edges(self) -> None:
        """No two edges share the same (src, relation, dst) triple."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        # Two chunks in main.py both reference 'login'
        chunks = [
            _make_chunk_with_refs("src/auth.py", ["login"], []),
            _make_chunk_with_refs("src/main.py", [], ["login"]),
            _make_chunk_with_refs("src/main.py", [], ["login"]),  # duplicate chunk
        ]
        nodes, edges = chunks_to_full_graph(chunks)

        edge_keys = [(e.src, e.relation, e.dst) for e in edges]
        assert len(edge_keys) == len(set(edge_keys)), "Duplicate edges found"

    def test_chunks_to_full_graph_skips_unresolvable(self) -> None:
        """References that resolve to nothing produce no CALLS or IMPORTS edges."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        chunks = [
            _make_chunk_with_refs("src/main.py", [], ["completely_unknown_symbol_xyz"])
        ]
        nodes, edges = chunks_to_full_graph(chunks)

        non_contains = [e for e in edges if e.relation != "CONTAINS"]
        assert non_contains == [], f"Unexpected edges for unknown symbol: {non_contains}"

    def test_chunks_to_full_graph_empty_input(self) -> None:
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        nodes, edges = chunks_to_full_graph([])
        assert nodes == []
        assert edges == []

    def test_chunks_to_full_graph_no_calls_to_file_nodes(self) -> None:
        """CALLS edges must point to symbol nodes, not file nodes."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph

        chunks = [
            _make_chunk_with_refs("src/auth.py", ["login"], []),
            _make_chunk_with_refs("src/main.py", [], ["login"]),
        ]
        nodes, edges = chunks_to_full_graph(chunks)

        file_ids = {n.id for n in nodes if n.kind == "file"}
        for e in edges:
            if e.relation == "CALLS":
                assert e.dst not in file_ids, f"CALLS edge points to file node: {e}"


# ---------------------------------------------------------------------------
# Sub-phase 2a — validate_graph extended warnings (CALLS/IMPORTS)
# ---------------------------------------------------------------------------


class TestValidationCallsImportsWarnings:
    """validate_graph must warn about CALLS→file and IMPORTS→non-file targets."""

    def test_validation_warns_calls_edge_to_file_node(self) -> None:
        from ws_ctx_engine.graph.builder import Edge, Node
        from ws_ctx_engine.graph.validation import validate_graph

        file_a = Node(id="src/a.py", kind="file", name="a.py", file="src/a.py", language="python")
        file_b = Node(id="src/b.py", kind="file", name="b.py", file="src/b.py", language="python")
        # CALLS edge from a file to another file (likely resolution error)
        bad_edge = Edge(src="src/a.py", relation="CALLS", dst="src/b.py")

        result = validate_graph([file_a, file_b], [bad_edge])
        assert result.is_valid  # warning only — should not block ingestion
        assert any("CALLS" in w or "file" in w.lower() for w in result.warnings), (
            f"Expected warning about CALLS→file, got: {result.warnings}"
        )

    def test_validation_warns_imports_edge_to_non_file_node(self) -> None:
        from ws_ctx_engine.graph.builder import Edge, Node
        from ws_ctx_engine.graph.validation import validate_graph

        file_node = Node(
            id="src/a.py", kind="file", name="a.py", file="src/a.py", language="python"
        )
        sym_node = Node(
            id="src/a.py#login",
            kind="function",
            name="login",
            file="src/a.py",
            language="python",
        )
        # IMPORTS edge pointing to a symbol node (should point to a file)
        bad_edge = Edge(src="src/a.py", relation="IMPORTS", dst="src/a.py#login")

        result = validate_graph([file_node, sym_node], [bad_edge])
        assert result.is_valid  # warning only
        assert any("IMPORTS" in w or "file" in w.lower() for w in result.warnings), (
            f"Expected warning about IMPORTS→non-file, got: {result.warnings}"
        )

    def test_validation_accepts_valid_calls_edge(self) -> None:
        from ws_ctx_engine.graph.builder import Edge, Node
        from ws_ctx_engine.graph.validation import validate_graph

        file_node = Node(
            id="src/a.py", kind="file", name="a.py", file="src/a.py", language="python"
        )
        sym_node = Node(
            id="src/b.py#do_thing",
            kind="function",
            name="do_thing",
            file="src/b.py",
            language="python",
        )
        file_b = Node(
            id="src/b.py", kind="file", name="b.py", file="src/b.py", language="python"
        )
        good_edge = Edge(src="src/a.py", relation="CALLS", dst="src/b.py#do_thing")

        result = validate_graph([file_node, sym_node, file_b], [good_edge])
        assert result.is_valid
        # No warning about this edge (it's a valid CALLS target)
        calls_file_warnings = [
            w for w in result.warnings if "CALLS" in w and "src/a.py" in w
        ]
        assert not calls_file_warnings, f"Unexpected warning: {calls_file_warnings}"

    def test_validation_accepts_valid_imports_edge(self) -> None:
        from ws_ctx_engine.graph.builder import Edge, Node
        from ws_ctx_engine.graph.validation import validate_graph

        file_a = Node(
            id="src/a.py", kind="file", name="a.py", file="src/a.py", language="python"
        )
        file_b = Node(
            id="src/b.py", kind="file", name="b.py", file="src/b.py", language="python"
        )
        good_edge = Edge(src="src/a.py", relation="IMPORTS", dst="src/b.py")

        result = validate_graph([file_a, file_b], [good_edge])
        assert result.is_valid
        imports_non_file_warnings = [
            w for w in result.warnings if "IMPORTS" in w
        ]
        assert not imports_non_file_warnings, f"Unexpected warning: {imports_non_file_warnings}"
