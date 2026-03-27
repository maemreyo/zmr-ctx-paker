"""
Graph pre-flight validation.

Run ``validate_graph(nodes, edges)`` between ``chunks_to_graph()`` and any
graph store insertion.  Hard errors block ingestion; warnings are logged but
do not prevent insertion.
"""

from dataclasses import dataclass, field

from .builder import Edge, Node


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a graph pre-flight check."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def validate_graph(nodes: list[Node], edges: list[Edge]) -> ValidationResult:
    """Check graph consistency before ingestion into a graph store.

    Hard errors (``is_valid = False``):
    - Duplicate node IDs.
    - Edge endpoints that reference non-existent node IDs.

    Warnings (``is_valid`` stays ``True``):
    - Non-file nodes with no incoming ``CONTAINS`` edge (orphan symbols).

    Args:
        nodes: List of nodes to validate.
        edges: List of edges to validate.

    Returns:
        ``ValidationResult`` with ``is_valid``, ``errors``, and ``warnings``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # ── Duplicate node ID check ──────────────────────────────────────────
    node_ids: set[str] = set()
    for node in nodes:
        if node.id in node_ids:
            errors.append(f"Duplicate node ID: {node.id}")
        node_ids.add(node.id)

    # ── Dangling edge endpoint check ────────────────────────────────────
    for edge in edges:
        if edge.src not in node_ids:
            errors.append(f"Edge src not found: {edge.src} (relation={edge.relation})")
        if edge.dst not in node_ids:
            errors.append(f"Edge dst not found: {edge.dst} (relation={edge.relation})")

    # ── Orphan symbol warning ────────────────────────────────────────────
    has_parent: set[str] = {e.dst for e in edges if e.relation == "CONTAINS"}
    for node in nodes:
        if node.kind != "file" and node.id not in has_parent:
            warnings.append(f"Orphan symbol: {node.id} (kind={node.kind})")

    # ── CALLS / IMPORTS semantic warnings ────────────────────────────────
    # Build a lookup of node kind per ID (only check nodes we know about).
    node_kind: dict[str, str] = {n.id: n.kind for n in nodes}
    for edge in edges:
        if edge.relation == "CALLS":
            dst_kind = node_kind.get(edge.dst)
            if dst_kind == "file":
                warnings.append(
                    f"CALLS edge dst is a file node (likely resolution error): "
                    f"{edge.src} -> {edge.dst}"
                )
        elif edge.relation == "IMPORTS":
            dst_kind = node_kind.get(edge.dst)
            if dst_kind is not None and dst_kind != "file":
                warnings.append(
                    f"IMPORTS edge dst is not a file node (likely resolution error): "
                    f"{edge.src} -> {edge.dst} (kind={dst_kind})"
                )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
