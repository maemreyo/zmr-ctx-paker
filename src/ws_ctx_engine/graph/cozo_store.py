"""
GraphStore — CozoDB-backed graph store for ws-ctx-engine.

Storage backends:
  "mem"            — in-memory (fast, non-persistent; ideal for tests)
  "rocksdb:<path>" — persistent RocksDB storage
  "sqlite:<path>"  — persistent SQLite storage

If pycozo is not installed or the DB fails to initialise, the store degrades
gracefully: ``is_healthy`` returns ``False`` and all operations are no-ops /
return empty results.  The caller must never need to handle exceptions from
this module.
"""

from __future__ import annotations

import logging
import time
from collections import deque as _deque
from typing import TYPE_CHECKING, Any

from .metrics import GraphMetrics

if TYPE_CHECKING:
    from .builder import Edge, Node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema (mirrors phase0_cozo_validation.py exactly)
# ---------------------------------------------------------------------------

_DDL_NODES = (
    ":create nodes { id: String => kind: String, name: String, file: String, language: String }"
)
_DDL_EDGES = ":create edges { src: String, relation: String, dst: String => }"

_SCHEMA_VERSION = "1"


def _create_client(storage: str) -> Any:
    """Create and return a pycozo Client.  Raises on any error."""
    from pycozo.client import Client

    if storage == "mem":
        client = Client("mem", "", {})
    elif storage.startswith("rocksdb:"):
        path = storage[len("rocksdb:") :]
        client = Client("rocksdb", path, {})
    elif storage.startswith("sqlite:"):
        path = storage[len("sqlite:") :]
        client = Client("sqlite", path, {})
    else:
        # Unknown storage string — try passing through as-is.
        client = Client(storage, "", {})
    return client


class GraphStore:
    """CozoDB-backed graph store.

    Instantiate with a *storage* string:
      - ``"mem"``           — in-memory (tests / ephemeral usage)
      - ``"rocksdb:<path>"`` — persistent RocksDB
      - ``"sqlite:<path>"``  — persistent SQLite

    All public methods are safe to call even when the store is not healthy;
    they return empty results without raising.
    """

    __slots__ = ("_db", "_healthy", "_metrics", "_schema_version")

    def __init__(self, storage: str = "mem") -> None:
        self._db: Any = None
        self._healthy: bool = False
        self._metrics: GraphMetrics = GraphMetrics()
        self._schema_version: str = "unknown"
        try:
            self._db = _create_client(storage)
            self._healthy = True
        except Exception as exc:
            logger.warning("GraphStore init failed (store will be unhealthy): %s", exc)
            return

        # Create relations idempotently — `:create` raises if already exists,
        # so catch per-statement and continue; the data is already there.
        for ddl in (_DDL_NODES, _DDL_EDGES):
            try:
                self._db.run(ddl)
            except Exception:
                pass  # relation already exists — that's fine

        # Schema version bookkeeping
        try:
            self._db.run(":create meta { key: String => value: String }")
            self._db.run(
                "?[key, value] <- [[$key, $value]] :put meta {key => value}",
                {"key": "schema_version", "value": _SCHEMA_VERSION},
            )
            self._schema_version = _SCHEMA_VERSION
        except Exception:
            # meta relation already exists — read stored version
            try:
                rows = self._db.run('?[value] := *meta{key: "schema_version", value}')
                stored = rows["value"].iloc[0] if len(rows) > 0 else "unknown"
                self._schema_version = stored
                if stored != _SCHEMA_VERSION:
                    logger.warning(
                        "Graph store schema version mismatch (stored=%s, expected=%s). "
                        "Consider re-indexing with 'wsctx index'.",
                        stored,
                        _SCHEMA_VERSION,
                    )
            except Exception:
                self._schema_version = "unknown"

    # ------------------------------------------------------------------
    # Protocol properties / methods
    # ------------------------------------------------------------------

    @property
    def is_healthy(self) -> bool:
        """True when the underlying CozoDB connection is operational."""
        return self._healthy

    def clear(self) -> None:
        """Remove ALL nodes and edges (full wipe for re-indexing).

        Used before a full rebuild so stale data from renamed/deleted symbols
        does not persist.  No-op when store is unhealthy.
        """
        if not self._healthy:
            return
        self._query("?[id, kind, name, file, language] := *nodes{id, kind, name, file, language} :rm nodes {id}")
        self._query("?[src, relation, dst] := *edges{src, relation, dst} :rm edges {src, relation, dst}")

    @property
    def schema_version(self) -> str:
        """Return the schema version string stored in the meta relation."""
        return self._schema_version

    def stats(self) -> dict:
        """Return node/edge counts, health status, schema version, and query metrics."""
        if not self._healthy:
            return {
                "node_count": 0,
                "edge_count": 0,
                "healthy": False,
                "schema_version": self._schema_version,
                "metrics": self._metrics.snapshot(),
            }
        node_rows = self._query("?[count(id)] := *nodes{id}")
        edge_rows = self._query("?[count(src)] := *edges{src}")
        node_count = node_rows[0]["count(id)"] if node_rows else 0
        edge_count = edge_rows[0]["count(src)"] if edge_rows else 0
        return {
            "node_count": int(node_count),
            "edge_count": int(edge_count),
            "healthy": self._healthy,
            "schema_version": self._schema_version,
            "metrics": self._metrics.snapshot(),
        }

    def bulk_upsert(self, nodes: list[Node], edges: list[Edge]) -> None:
        """Insert or update *nodes* and *edges* in the store.

        Uses ``$rows`` parameter binding (same pattern as phase0 script).
        No-op when store is unhealthy or input lists are empty.
        """
        if not self._healthy:
            return
        if nodes:
            rows_n = [[n.id, n.kind, n.name, n.file, n.language] for n in nodes]
            self._query(
                "?[id, kind, name, file, language] <- $rows "
                ":put nodes { id => kind, name, file, language }",
                {"rows": rows_n},
            )
        if edges:
            rows_e = [[e.src, e.relation, e.dst] for e in edges]
            self._query(
                "?[src, relation, dst] <- $rows :put edges { src, relation, dst }",
                {"rows": rows_e},
            )

    def delete_file_scope(self, file_id: str) -> None:
        """Remove all nodes whose ``file == file_id`` and all adjacent edges.

        Two-step process (iterative, no recursion):
        1. Collect node IDs belonging to *file_id* (including the file node itself).
        2. Delete all edges where ``src == file_id`` OR ``dst`` is one of those
           node IDs.
        3. Delete the collected nodes.
        """
        if not self._healthy:
            return

        # Step 1: collect affected node IDs
        affected = self._query(
            "?[id] := *nodes{ id, file: $file }",
            {"file": file_id},
        )
        node_ids: list[str] = [row["id"] for row in affected if "id" in row]

        if not node_ids:
            return

        # Step 2: delete edges involving the file or its nodes
        # Delete edges where src == file_id
        self._query(
            "?[src, relation, dst] := *edges{ src: $file, relation, dst } "
            ":rm edges { src, relation, dst }",
            {"file": file_id},
        )

        # Delete inbound edges to any node belonging to this file (single join query,
        # not one query per node — avoids O(n) round-trips for large files).
        self._query(
            "?[src, relation, dst] := "
            "*edges{ src, relation, dst }, "
            "*nodes{ id: dst, file: $file } "
            ":rm edges { src, relation, dst }",
            {"file": file_id},
        )

        # Step 3: delete the nodes themselves
        self._query(
            "?[id, kind, name, file, language] := *nodes{ id, kind, name, file: $file, language } "
            ":rm nodes { id }",
            {"file": file_id},
        )

    def contains_of(self, file_id: str) -> list[dict]:
        """Return all symbols directly contained in *file_id* (via CONTAINS edges).

        Returns:
            List of dicts with keys ``sym`` and ``kind``.
        """
        rows = self._query(
            "?[sym, kind] := "
            '*edges{ src: $file, relation: "CONTAINS", dst: sym }, '
            "*nodes{ id: sym, kind }",
            {"file": file_id},
        )
        return rows

    def callers_of(self, fn_name: str, depth: int = 2) -> list[dict]:
        """Return files that call the function named *fn_name*.

        The *depth* parameter is reserved for future multi-hop traversal;
        currently performs a single-hop query only.

        Returns:
            List of dicts with key ``caller_file``.
        """
        rows = self._query(
            "?[caller_file] := "
            '*edges{ src: caller_file, relation: "CALLS", dst: sym }, '
            "*nodes{ id: sym, name: $fn }",
            {"fn": fn_name},
        )
        return rows

    def impact_of(self, file_path: str) -> list[str]:
        """Return file IDs that import *file_path* (IMPORTS edges).

        Returns:
            List of importer file-path strings.
        """
        rows = self._query(
            '?[importer] := *edges{ src: importer, relation: "IMPORTS", dst: $file }',
            {"file": file_path},
        )
        return [row["importer"] for row in rows if "importer" in row]

    def find_path(self, from_fn: str, to_fn: str, max_depth: int = 5) -> list[str]:
        """BFS to find call path from from_fn to to_fn via CALLS edges.

        CALLS edges are stored as ``file_id → symbol_id`` (file-granularity).
        The BFS traversal is therefore:
          function name → containing file(s) via CONTAINS edges (reversed)
                       → CALLS edges from that file → callee symbol names
                       → repeat for each callee name

        Returns a list of function names forming the path, or [] if none found.
        Handles cycles and max_depth limit safely.
        """
        if not self._healthy:
            return []
        if from_fn == to_fn:
            return [from_fn]

        visited: set[str] = {from_fn}
        queue: _deque[tuple[str, list[str]]] = _deque([(from_fn, [from_fn])])

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            # Find file nodes that CONTAIN a symbol named `current`
            container_rows = self._query(
                "?[file_id] := "
                "*nodes{id: sym_id, name: $name, kind}, kind != 'file', "
                "*edges{src: file_id, relation: 'CONTAINS', dst: sym_id}",
                {"name": current},
            )
            seen_files: set[str] = set()
            for crow in container_rows:
                file_id = crow.get("file_id", "")
                if not file_id or file_id in seen_files:
                    continue
                seen_files.add(file_id)
                # All symbols called by this file
                callee_rows = self._query(
                    "?[callee_name] := "
                    "*edges{src: $file, relation: 'CALLS', dst: callee_id}, "
                    "*nodes{id: callee_id, name: callee_name}",
                    {"file": file_id},
                )
                for row in callee_rows:
                    callee_name = row.get("callee_name", "")
                    if not callee_name or callee_name == current:
                        continue
                    if callee_name == to_fn:
                        return path + [callee_name]
                    if callee_name not in visited:
                        visited.add(callee_name)
                        queue.append((callee_name, path + [callee_name]))
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _query(self, datalog: str, params: dict[str, Any] | None = None) -> list[dict]:
        """Run *datalog* and return results as a list of row dicts.

        Records latency and error state in the metrics collector.
        Returns ``[]`` when the store is unhealthy.  On any exception,
        logs and returns ``[]`` (store stays healthy for transient errors).
        """
        if not self._healthy or self._db is None:
            return []
        start = time.perf_counter()
        error = False
        try:
            df = self._db.run(datalog, params or {})
            if df is None or len(df) == 0:
                return []
            return list(df.to_dict(orient="records"))
        except Exception as exc:
            error = True
            logger.debug("GraphStore query error: %s | script: %.80s", exc, datalog)
            return []
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            self._metrics.record(latency_ms, error=error)
            logger.debug(
                "graph.query latency_ms=%.2f error=%s script=%.60s",
                latency_ms,
                error,
                datalog,
            )
