"""
Canonical node ID construction for the graph store.

All node IDs must flow through ``normalize_node_id()`` — never construct raw
f-string IDs elsewhere.  Normalisation rules:

1. Resolve to repo-relative path (strips absolute prefix and ``./``).
2. Forward slashes only (cross-platform).
3. Symbol sanitisation: non-alphanumeric characters → underscore.
"""

import re
import subprocess
from pathlib import Path


def _get_repo_root() -> str | None:
    """Return the repo root from git, or None if not in a git repo.

    Called only for absolute paths, which are uncommon in the normal pipeline
    (``_parse_file`` already produces repo-relative paths).
    """
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            timeout=5,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def normalize_node_id(filepath: str, symbol: str | None = None) -> str:
    """Return a canonical, portable node ID for *filepath* and optional *symbol*.

    Examples::

        normalize_node_id("./src/auth.py")            → "src/auth.py"
        normalize_node_id("src/auth.py", "authenticate") → "src/auth.py#authenticate"
        normalize_node_id("src/auth.py", "<lambda>")   → "src/auth.py#_lambda_"
        normalize_node_id("src\\utils.py")             → "src/utils.py"
    """
    path = Path(filepath)

    # Attempt to make path repo-relative (strip absolute repo root prefix).
    if path.is_absolute():
        repo_root = _get_repo_root()
        if repo_root is not None:
            try:
                path = path.relative_to(repo_root)
            except ValueError:
                pass  # Path outside repo — keep as-is.
    else:
        # Strip leading "./" from relative paths.
        parts = path.parts
        if parts and parts[0] == ".":
            path = Path(*parts[1:]) if len(parts) > 1 else Path(".")

    rel = str(path).replace("\\", "/")

    if not symbol:
        return rel

    safe_symbol = re.sub(r"[^a-zA-Z0-9_]", "_", symbol)
    return f"{rel}#{safe_symbol}"
