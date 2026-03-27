"""
GraphStoreProtocol — structural typing contract for all graph store backends.

Any class that satisfies these method signatures is a valid GraphStore,
regardless of inheritance.  Use ``isinstance(obj, GraphStoreProtocol)`` to
check at runtime (the Protocol is ``runtime_checkable``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .builder import Edge, Node


@runtime_checkable
class GraphStoreProtocol(Protocol):
    """Structural interface for a graph-store backend."""

    @property
    def is_healthy(self) -> bool:
        """True when the underlying store is operational."""
        ...

    def clear(self) -> None:
        """Remove ALL nodes and edges (full wipe for re-indexing)."""
        ...

    def bulk_upsert(self, nodes: "list[Node]", edges: "list[Edge]") -> None:
        """Insert or update *nodes* and *edges* in the store."""
        ...

    def delete_file_scope(self, file_id: str) -> None:
        """Remove all nodes whose ``file == file_id`` and all adjacent edges."""
        ...

    def contains_of(self, file_id: str) -> list[dict]:
        """Return all symbols directly contained in *file_id* (CONTAINS edges)."""
        ...

    def callers_of(self, fn_name: str, depth: int = 2) -> list[dict]:
        """Return files that call the function named *fn_name*.

        *depth* is reserved for future multi-hop traversal; currently
        implementations perform a single-hop query regardless.
        """
        ...

    def impact_of(self, file_path: str) -> list[str]:
        """Return file IDs that import *file_path* (IMPORTS edges)."""
        ...

    def stats(self) -> dict:
        """Return node/edge counts, health status, schema version, and query metrics."""
        ...

    def find_path(self, from_fn: str, to_fn: str, max_depth: int = 5) -> list[str]:
        """BFS to find call path from from_fn to to_fn via CALLS edges."""
        ...
