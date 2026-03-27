from .builder import Edge, Node, chunks_to_full_graph, chunks_to_graph
from .context_assembler import AssemblyResult, ContextAssembler
from .graph import (
    IGraphRepoMap,
    NetworkXRepoMap,
    RepoMapGraph,
    create_graph,
    load_graph,
)
from .node_id import normalize_node_id
from .signal_router import GraphIntent, classify_graph_intent, needs_graph
from .store_protocol import GraphStoreProtocol
from .symbol_index import SymbolIndex
from .validation import ValidationResult, validate_graph

# GraphStore is optional — pycozo may not be installed.
try:
    from .cozo_store import GraphStore

    _graphstore_exports: list[str] = ["GraphStore"]
except ImportError as _e:
    import logging as _logging
    _logging.getLogger(__name__).debug("GraphStore unavailable (pycozo not installed): %s", _e)
    _graphstore_exports = []

__all__ = [
    "RepoMapGraph",
    "IGraphRepoMap",
    "NetworkXRepoMap",
    "create_graph",
    "load_graph",
    # Graph bridge
    "Node",
    "Edge",
    "chunks_to_graph",
    "chunks_to_full_graph",
    "normalize_node_id",
    "ValidationResult",
    "validate_graph",
    # Phase 2 additions
    "SymbolIndex",
    "GraphStoreProtocol",
    # Phase 3 additions
    "GraphIntent",
    "classify_graph_intent",
    "needs_graph",
    "AssemblyResult",
    "ContextAssembler",
    *_graphstore_exports,
]
