"""
Graph bridge: convert ``list[CodeChunk]`` → ``(list[Node], list[Edge])``.

Implements Integration Point 0 from the Graph RAG Roadmap.  Produces
``CONTAINS`` edges only (file CONTAINS symbol).  ``CALLS`` and ``IMPORTS``
edges require AST call-site walks (Phase 2 of the roadmap).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .node_id import normalize_node_id

if TYPE_CHECKING:
    from ..models.models import CodeChunk

# NOTE: SymbolIndex is imported lazily inside chunks_to_full_graph() to avoid
# circular imports at module load time.


@dataclass(frozen=True)
class Node:
    """A graph node representing a file or named symbol."""

    id: str       # canonical ID, e.g. "src/auth.py" or "src/auth.py#authenticate"
    kind: str     # "file" | "function" | "class" | "method"
    name: str     # human-readable short name
    file: str     # file path (repo-relative)
    language: str


@dataclass(frozen=True)
class Edge:
    """A directed edge between two nodes."""

    src: str       # source node ID
    relation: str  # "CONTAINS" | "CALLS" | "IMPORTS" | "INHERITS"
    dst: str       # destination node ID


def _infer_symbol_kind(symbol: str) -> str:
    """Heuristically classify a symbol as 'class', 'function', or 'method'.

    Uses naming-convention heuristics as a first approximation:
    - PascalCase → 'class'
    - everything else → 'function'

    A future version may use richer AST metadata when available.
    """
    if symbol and symbol[0].isupper():
        return "class"
    return "function"


def chunks_to_graph(chunks: "list[CodeChunk]") -> "tuple[list[Node], list[Edge]]":
    """Convert chunker output into graph-ready ``(nodes, edges)`` tuples.

    For each chunk:
    - Ensures a ``file`` node exists for the chunk's file path.
    - Creates a ``symbol`` node for each entry in ``chunk.symbols_defined``.
    - Emits a ``CONTAINS`` edge from the file node to each symbol node.

    Duplicate file nodes are deduplicated.

    Args:
        chunks: Output from ``TreeSitterChunker.parse()`` or equivalent.

    Returns:
        ``(nodes, edges)`` — both lists may be empty for empty input.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_ids: set[str] = set()

    def _add_node(node: Node) -> None:
        if node.id not in seen_ids:
            seen_ids.add(node.id)
            nodes.append(node)

    for chunk in chunks:
        file_id = normalize_node_id(chunk.path)
        file_node = Node(
            id=file_id,
            kind="file",
            name=Path(chunk.path).name,
            file=file_id,  # normalized to match the canonical ID
            language=chunk.language,
        )
        _add_node(file_node)

        for symbol in chunk.symbols_defined:
            sym_id = normalize_node_id(chunk.path, symbol)
            kind = _infer_symbol_kind(symbol)
            sym_node = Node(
                id=sym_id,
                kind=kind,
                name=symbol,
                file=chunk.path,
                language=chunk.language,
            )
            _add_node(sym_node)
            edges.append(Edge(src=file_id, relation="CONTAINS", dst=sym_id))

    return nodes, edges


def chunks_to_full_graph(
    chunks: "list[CodeChunk]",
) -> "tuple[list[Node], list[Edge]]":
    """Like ``chunks_to_graph()`` but also emits CALLS and IMPORTS edges.

    Algorithm:
    1. Run ``chunks_to_graph(chunks)`` to get nodes + CONTAINS edges.
    2. Build a ``SymbolIndex`` over those nodes.
    3. For each chunk, for each name in ``chunk.symbols_referenced``:
       - Try ``index.resolve_symbol(name)`` → emit ``CALLS`` edges.
       - Try ``index.resolve_module(name)`` → emit ``IMPORTS`` edge (skip self-loops).
    4. Deduplicate all edges by ``(src, relation, dst)``.
    5. Return ``(nodes, deduped_edges)``.

    Args:
        chunks: Output from ``TreeSitterChunker.parse()`` or equivalent.

    Returns:
        ``(nodes, edges)`` where edges include CONTAINS, CALLS, and IMPORTS.
    """
    from .symbol_index import SymbolIndex

    nodes, edges = chunks_to_graph(chunks)
    index = SymbolIndex.build(nodes, chunks)

    seen_edges: set[tuple[str, str, str]] = {(e.src, e.relation, e.dst) for e in edges}
    extra_edges: list[Edge] = []

    for chunk in chunks:
        file_id = normalize_node_id(chunk.path)

        for ref_name in chunk.symbols_referenced:
            # ── CALLS edges ──────────────────────────────────────────────
            resolved_ids = index.resolve_symbol(ref_name)
            for sym_id in resolved_ids:
                key = (file_id, "CALLS", sym_id)
                if key not in seen_edges:
                    seen_edges.add(key)
                    extra_edges.append(Edge(src=file_id, relation="CALLS", dst=sym_id))

            # ── IMPORTS edges ────────────────────────────────────────────
            resolved_file = index.resolve_module(ref_name)
            if resolved_file is not None and resolved_file != file_id:
                key = (file_id, "IMPORTS", resolved_file)
                if key not in seen_edges:
                    seen_edges.add(key)
                    extra_edges.append(
                        Edge(src=file_id, relation="IMPORTS", dst=resolved_file)
                    )

    return nodes, edges + extra_edges
