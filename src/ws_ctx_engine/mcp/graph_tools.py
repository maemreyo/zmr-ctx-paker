"""
Graph tool handlers for the MCP server.

Pure functions — no side effects, no global state. Each handler:
1. Validates required arguments (returns INVALID_ARGUMENT on failure)
2. Checks store health (returns GRAPH_UNAVAILABLE if store is None or unhealthy)
3. Calls the appropriate GraphStore method
4. Returns a structured dict result
"""

from __future__ import annotations

from typing import Any

_GRAPH_UNAVAILABLE_MSG = (
    "Graph store is not available. Run 'wsctx index <repo>' with pycozo installed "
    "to enable graph features (pip install ws-ctx-engine[graph-store])."
)


def _check_store(store: Any) -> dict[str, Any] | None:
    """Return GRAPH_UNAVAILABLE error dict if store is unusable, else None."""
    if store is None or not getattr(store, "is_healthy", False):
        return {"error": "GRAPH_UNAVAILABLE", "message": _GRAPH_UNAVAILABLE_MSG}
    return None


def handle_find_callers(store: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Find all callers of a given function name."""
    fn_name = args.get("fn_name", "").strip()
    if not fn_name:
        return {
            "error": "INVALID_ARGUMENT",
            "message": "fn_name is required and must not be empty.",
        }
    err = _check_store(store)
    if err:
        return err
    try:
        rows = store.callers_of(fn_name)
        return {"callers": rows}
    except Exception as exc:
        return {"error": "STORE_ERROR", "message": str(exc), "callers": []}


def handle_impact_analysis(store: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Return files that import/depend on a given file."""
    file_path = args.get("file_path", "").strip()
    if not file_path:
        return {
            "error": "INVALID_ARGUMENT",
            "message": "file_path is required and must not be empty.",
        }
    err = _check_store(store)
    if err:
        return err
    try:
        importers = store.impact_of(file_path)
        return {"importers": importers}
    except Exception as exc:
        return {"error": "STORE_ERROR", "message": str(exc), "importers": []}


def handle_graph_search(store: Any, args: dict[str, Any]) -> dict[str, Any]:
    """List all symbols defined in a given file."""
    file_id = args.get("file_id", "").strip()
    if not file_id:
        return {
            "error": "INVALID_ARGUMENT",
            "message": "file_id is required and must not be empty.",
        }
    err = _check_store(store)
    if err:
        return err
    try:
        rows = store.contains_of(file_id)
        return {"symbols": rows}
    except Exception as exc:
        return {"error": "STORE_ERROR", "message": str(exc), "symbols": []}


def handle_call_chain(store: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Trace call path between two functions via BFS."""
    from_fn = args.get("from_fn", "").strip()
    to_fn = args.get("to_fn", "").strip()
    if not from_fn or not to_fn:
        return {"error": "INVALID_ARGUMENT", "message": "Both from_fn and to_fn are required."}
    err = _check_store(store)
    if err:
        return err
    max_depth = min(int(args.get("max_depth", 5)), 10)
    try:
        path = store.find_path(from_fn, to_fn, max_depth=max_depth)
        if not path:
            return {
                "path": [],
                "depth": 0,
                "message": f"No call path found from '{from_fn}' to '{to_fn}' within {max_depth} hops.",
            }
        return {"path": path, "depth": len(path) - 1}
    except Exception as exc:
        return {"error": "STORE_ERROR", "message": str(exc), "path": []}
