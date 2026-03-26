import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import CodeChunk

logger = logging.getLogger("ws_ctx_engine")

# M7: Optional Rust accelerated hot-paths (PyO3 extension).
# Only walk_files is in Rust — hashlib and len()//4 are fast enough in Python.
# Tries ws_ctx_engine._rust first (namespace install), then top-level _rust
# (maturin develop install).
try:
    try:
        from ws_ctx_engine._rust import walk_files as _rust_walk_files  # type: ignore[import-not-found]
    except ImportError:
        from _rust import walk_files as _rust_walk_files  # type: ignore[import-not-found]

    RUST_AVAILABLE = True
    logger.debug("Rust extension loaded — using accelerated file walker")
except ImportError:
    RUST_AVAILABLE = False
    _rust_walk_files = None

# Extensions with actual AST parsers available in this engine.
# Files matching these extensions will be parsed with full AST support.
# Any other extension will produce a [WARNING] during indexing.
INDEXED_EXTENSIONS = frozenset(
    {
        ".py",  # Python — tree-sitter + regex fallback
        ".js",  # JavaScript — tree-sitter + regex fallback
        ".ts",  # TypeScript — tree-sitter + regex fallback
        ".jsx",  # JSX — tree-sitter JavaScript
        ".tsx",  # TSX — tree-sitter TypeScript
        ".rs",  # Rust — tree-sitter + regex fallback
    }
)


class ASTChunker(ABC):
    @abstractmethod
    def parse(self, repo_path: str, config: Any = None) -> list[CodeChunk]:
        pass


def collect_gitignore_patterns(root: Path) -> list[str]:
    """
    Recursively discover all .gitignore files under *root* and collect patterns,
    prefixing sub-directory patterns with their relative directory path so that
    the resulting spec replicates Git's scoping rules.
    """
    all_patterns: list[str] = []
    for gitignore_path in sorted(root.rglob(".gitignore")):
        try:
            relative_dir = gitignore_path.parent.relative_to(root)
        except ValueError:
            continue
        try:
            lines = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if str(relative_dir) != ".":
                # Scope the pattern to its subdirectory
                all_patterns.append(f"{relative_dir}/{line}")
            else:
                all_patterns.append(line)
    return all_patterns


def build_ignore_spec(patterns: list[str]) -> Any:
    """
    Build a GitIgnoreSpec that replicates actual Git behaviour including
    re-include (!pattern) and last-pattern-wins semantics.

    Requires pathspec>=0.12 (GitIgnoreSpec).
    """
    try:
        from pathspec import GitIgnoreSpec

        return GitIgnoreSpec.from_lines(patterns)
    except ImportError:
        # Graceful fallback if pathspec is somehow unavailable at runtime.
        logger.warning(
            "pathspec.GitIgnoreSpec not available — falling back to basic fnmatch ignore. "
            "Install pathspec>=0.12 for full .gitignore compliance."
        )
        return None


def get_files_to_include(root: Path, spec: Any) -> list[str]:
    """Return relative paths of files that are NOT matched by *spec* (i.e. not ignored)."""
    if spec is None:
        return []
    try:
        # match_tree_files with negate=True returns files NOT matched by the spec
        return list(spec.match_tree_files(str(root), negate=True))
    except Exception:
        return []


def warn_non_indexed_extension(file_path: str) -> None:
    """Emit a WARNING when a file's extension has no AST parser."""
    ext = Path(file_path).suffix.lower()
    if ext and ext not in INDEXED_EXTENSIONS:
        logger.warning(
            "[WARNING] No AST parser available for extension '%s' (file: %s). "
            "File will be indexed as plain text.",
            ext,
            file_path,
        )


def _should_include_file(
    file_path: Path,
    repo_root: Path,
    include_patterns: list[str],
    exclude_patterns: list[str],
    gitignore_spec: Any = None,
) -> bool:
    """
    Decide whether a file should be included.

    Priority:
    1. If gitignore_spec is provided, honour it (replaces old exclude_patterns for
       gitignore-sourced rules).
    2. Check explicit exclude_patterns (user config).
    3. Check include_patterns.
    """

    relative_path = str(file_path.relative_to(repo_root))
    path_parts = relative_path.split("/")

    # 1. Gitignore spec check
    if gitignore_spec is not None:
        try:
            if gitignore_spec.match_file(relative_path):
                return False
        except Exception:
            pass

    # 2. Explicit exclude patterns
    for pattern in exclude_patterns:
        if _match_pattern(relative_path, path_parts, pattern):
            return False

    # 3. Include patterns
    for pattern in include_patterns:
        if _match_pattern(relative_path, path_parts, pattern):
            return True

    return False


def _match_pattern(relative_path: str, path_parts: list[str], pattern: str) -> bool:
    import fnmatch

    if fnmatch.fnmatch(relative_path, pattern):
        return True
    if fnmatch.fnmatch(relative_path, pattern.replace("**/", "*/")):
        return True
    if fnmatch.fnmatch(relative_path, pattern.replace("**", "*")):
        return True
    if pattern.startswith("**/"):
        simple_pattern = pattern[3:]
        for part in path_parts:
            if fnmatch.fnmatch(part, simple_pattern):
                return True
        if fnmatch.fnmatch(relative_path.split("/")[-1], simple_pattern):
            return True
    return False
