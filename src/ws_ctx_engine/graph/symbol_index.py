"""
SymbolIndex — resolves raw symbol names and module paths to canonical node IDs.

Used by ``chunks_to_full_graph()`` to emit CALLS and IMPORTS edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.models import CodeChunk
    from .builder import Node


@dataclass(frozen=True)
class SymbolIndex:
    """Resolves raw symbol names and module paths to canonical node IDs.

    Attributes:
        _name_to_ids: Mapping from short symbol name to list of node IDs.
            Only non-file nodes are included.
        _module_to_file: Mapping from dotted module name (and all shorter suffixes)
            to the canonical file node ID.
    """

    _name_to_ids: dict[str, list[str]] = field(default_factory=dict)
    _module_to_file: dict[str, str] = field(default_factory=dict)

    def resolve_symbol(self, name: str) -> list[str]:
        """Return node IDs for all symbols with this short name.

        Args:
            name: Short symbol name, e.g. ``"authenticate"``.

        Returns:
            List of node IDs; empty list if not found.
        """
        return list(self._name_to_ids.get(name, []))

    def resolve_module(self, module_name: str) -> str | None:
        """Return file node ID for a dotted module name.

        Tries longest match first (most specific wins).  For example,
        ``"ws_ctx_engine.chunker.tree_sitter"`` is preferred over
        ``"chunker.tree_sitter"`` or ``"tree_sitter"``.

        Args:
            module_name: Dotted module path, e.g. ``"ws_ctx_engine.chunker"``.

        Returns:
            File node ID string, or ``None`` if not found.
        """
        # Try progressively shorter suffix matches; longest match already
        # checked first because we iterate through suffix counts descending.
        parts = module_name.split(".")
        for length in range(len(parts), 0, -1):
            candidate = ".".join(parts[-length:])
            if candidate in self._module_to_file:
                return self._module_to_file[candidate]
        return None

    @classmethod
    def build(cls, nodes: "list[Node]", chunks: "list[CodeChunk]") -> "SymbolIndex":
        """Build index from existing graph nodes and (optionally) chunk paths.

        Build logic:
        - ``_name_to_ids``: for each non-file node, map ``node.name -> [node.id]``
          (append when multiple definitions exist).
        - ``_module_to_file``: for each file node, derive all reachable dotted module
          names from the path.  Example for ``src/ws_ctx_engine/chunker/tree_sitter.py``:
            - ``"ws_ctx_engine.chunker.tree_sitter"``
            - ``"chunker.tree_sitter"``
            - ``"tree_sitter"``
          Strips a leading ``src/`` component if present; strips the ``.py``
          (or other) suffix; replaces ``/`` with ``.``.

        Args:
            nodes: All nodes produced by ``chunks_to_graph()``.
            chunks: Original chunk list (reserved for future richer indexing).

        Returns:
            A new immutable ``SymbolIndex`` instance.
        """
        name_to_ids: dict[str, list[str]] = {}
        module_to_file: dict[str, str] = {}

        # Iterative processing — no recursion allowed per project rules.
        stack = list(nodes)
        while stack:
            node = stack.pop()
            if node.kind == "file":
                _register_file_node(node.id, module_to_file)
            else:
                if node.name not in name_to_ids:
                    name_to_ids[node.name] = []
                if node.id not in name_to_ids[node.name]:
                    name_to_ids[node.name].append(node.id)

        return cls(_name_to_ids=name_to_ids, _module_to_file=module_to_file)


def _register_file_node(file_id: str, module_to_file: dict[str, str]) -> None:
    """Register all dotted module name suffixes for *file_id* into *module_to_file*.

    For ``src/ws_ctx_engine/chunker/tree_sitter.py`` this inserts:
      ``"ws_ctx_engine.chunker.tree_sitter"`` → file_id
      ``"chunker.tree_sitter"``               → file_id
      ``"tree_sitter"``                        → file_id

    Strips a leading ``src/`` component if present.  Strips the file suffix.
    Uses iterative loop — no recursion.
    """
    path = Path(file_id)

    # Strip file suffix (e.g. ".py", ".ts")
    stem_parts = list(path.parts)

    # Reconstruct without the suffix for the last component
    if stem_parts:
        last = Path(stem_parts[-1]).stem
        stem_parts[-1] = last

    # Strip leading "src" component if present
    if stem_parts and stem_parts[0] == "src":
        stem_parts = stem_parts[1:]

    if not stem_parts:
        return

    # Build all suffix-based dotted names and register all of them.
    # Longer names (more specific) are added first; on collision the first
    # registration wins, so the longest will already be present.
    for start in range(len(stem_parts)):
        dotted = ".".join(stem_parts[start:])
        if dotted and dotted not in module_to_file:
            module_to_file[dotted] = file_id
