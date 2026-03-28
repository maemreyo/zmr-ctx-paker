"""
Shared utilities for CLI commands.

Provides common helpers for configuration loading, dependency checking,
gitignore handling, and output formatting.
"""

import importlib.metadata
import importlib.util
import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console

from ..config import Config
from ..logger import get_logger

# Initialize console and logger
console = Console()
logger = get_logger()
AGENT_MODE = False


def _set_console_log_level(level: int) -> None:
    """Set logging level for the console."""
    logging.getLogger("ws_ctx_engine").setLevel(level)


def _set_agent_mode(enabled: bool) -> None:
    """Enable or disable agent mode."""
    global AGENT_MODE, console
    AGENT_MODE = enabled
    console = Console(stderr=enabled)


def _emit_ndjson(payload: dict[str, Any]) -> None:
    """Emit NDJSON payload to stdout if in agent mode."""
    if AGENT_MODE:
        typer.echo(json.dumps(payload, ensure_ascii=False))


def _enable_command_agent_mode(command_agent_mode: bool) -> None:
    """Enable agent mode if requested by command."""
    if command_agent_mode and not AGENT_MODE:
        _set_agent_mode(True)


def _utc_now() -> str:
    """Get current UTC time as ISO format string."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _copy_to_clipboard(text: str) -> None:
    """Copy *text* to the system clipboard (macOS / Linux / Windows)."""
    candidates: list[tuple[list[str], dict[str, Any]]] = [
        (["pbcopy"], {}),  # macOS
        (["clip"], {}),  # Windows
        (["xclip", "-selection", "clipboard"], {}),  # Linux (xclip)
        (["xsel", "--clipboard", "--input"], {}),  # Linux (xsel)
    ]
    for cmd, kwargs in candidates:
        try:
            proc = subprocess.run(cmd, input=text.encode(), check=False, **kwargs)
            if proc.returncode == 0:
                if not AGENT_MODE:
                    console.print("[green]✓ Copied to clipboard[/green]")
                return
        except FileNotFoundError:
            continue
    Console(stderr=True).print(
        "[yellow]Warning:[/yellow] Could not copy to clipboard (no clipboard tool found)",
    )


def _extract_gitignore_patterns(repo_path: Path) -> list[str]:
    """Extract ignore patterns from .gitignore file."""
    gitignore_path = repo_path / ".gitignore"
    if not gitignore_path.exists():
        return []

    patterns: list[str] = []
    seen: set[str] = set()

    for raw_line in gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            continue

        if " #" in line:
            line = line.split(" #", 1)[0].strip()

        normalized = line.lstrip("/")
        if not normalized:
            continue

        if normalized.endswith("/"):
            normalized = f"{normalized.rstrip('/')}/**"

        if normalized not in seen:
            patterns.append(normalized)
            seen.add(normalized)

    return patterns


def _apply_gitignore_patterns(cfg: Config, repo_path: Path) -> Config:
    """Apply gitignore patterns to config exclude patterns."""
    if not getattr(cfg, "respect_gitignore", True):
        return cfg

    existing_excludes = getattr(cfg, "exclude_patterns", None)
    if existing_excludes is None:
        return cfg

    exclude_patterns = list(existing_excludes)

    for pattern in _extract_gitignore_patterns(repo_path):
        if pattern not in exclude_patterns:
            exclude_patterns.append(pattern)

    cfg.exclude_patterns = exclude_patterns
    return cfg


def _build_smart_config(
    repo_path: Path, include_gitignore: bool, vector_index: str, graph: str, embeddings_backend: str
) -> dict[str, Any]:
    """Build a smart configuration based on available backends."""
    cfg = Config()

    exclude_patterns = list(cfg.exclude_patterns)
    if include_gitignore:
        for pattern in _extract_gitignore_patterns(repo_path):
            if pattern not in exclude_patterns:
                exclude_patterns.append(pattern)

    config_payload: dict[str, Any] = {
        "format": cfg.format,
        "token_budget": cfg.token_budget,
        "output_path": cfg.output_path,
        "semantic_weight": cfg.semantic_weight,
        "pagerank_weight": cfg.pagerank_weight,
        "include_tests": cfg.include_tests,
        "respect_gitignore": include_gitignore,
        "include_patterns": cfg.include_patterns,
        "exclude_patterns": exclude_patterns,
        "backends": {
            "vector_index": vector_index,
            "graph": graph,
            "embeddings": embeddings_backend,
        },
        "embeddings": cfg.embeddings,
        "performance": cfg.performance,
    }

    return config_payload


def _ensure_repo_gitignore_has_wsctx_artifacts(repo_path: Path) -> bool:
    """Ensure .gitignore includes ws-ctx-engine artifact patterns."""
    gitignore_path = repo_path / ".gitignore"
    wsctx_patterns = [
        ".ws-ctx-engine/",
        ".ws-ctx-engine.yaml",
        "output/",
        "*.ws-ctx-engine.zip",
        "repomix-output.xml",
    ]

    if gitignore_path.exists():
        existing_lines = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    else:
        existing_lines = []

    existing_set = {line.strip() for line in existing_lines if line.strip()}
    missing = [pattern for pattern in wsctx_patterns if pattern not in existing_set]
    if not missing:
        return False

    lines_to_append: list[str] = []
    if existing_lines and existing_lines[-1].strip() != "":
        lines_to_append.append("")
    lines_to_append.append("# ws-ctx-engine artifacts")
    lines_to_append.extend(missing)

    content_to_append = "\n".join(lines_to_append) + "\n"
    with gitignore_path.open("a", encoding="utf-8") as fh:
        fh.write(content_to_append)

    return True


def _parse_rate_limits(values: list[str]) -> dict[str, int]:
    """Parse rate limit arguments from CLI."""
    parsed: dict[str, int] = {}
    allowed_tools = {"search_codebase", "get_file_context", "get_domain_map", "get_index_status"}

    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid --rate-limit '{value}'. Expected TOOL=LIMIT format.")

        tool_name, raw_limit = value.split("=", 1)
        tool_name = tool_name.strip()
        raw_limit = raw_limit.strip()

        if tool_name not in allowed_tools:
            raise ValueError(f"Invalid tool '{tool_name}' in --rate-limit.")

        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ValueError(f"Invalid limit '{raw_limit}' for tool '{tool_name}'.") from exc

        if limit <= 0:
            raise ValueError(f"Rate limit for '{tool_name}' must be positive.")

        parsed[tool_name] = limit

    return parsed


def _is_module_available(module_name: str) -> bool:
    """Check if a module is available."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _doctor_dependency_report() -> dict[str, bool]:
    """Generate dependency report for doctor command."""
    modules = {
        "leann": "leann",
        "igraph": "igraph",
        "sentence-transformers": "sentence_transformers",
        "tree-sitter": "tree_sitter",
        "tree-sitter-python": "tree_sitter_python",
        "tree-sitter-javascript": "tree_sitter_javascript",
        "tree-sitter-typescript": "tree_sitter_typescript",
        "tree-sitter-rust": "tree_sitter_rust",
        "faiss-cpu": "faiss",
        "networkx": "networkx",
        "scikit-learn": "sklearn",
        # Optional performance / quality enhancements
        "astchunk": "astchunk",
        "rank-bm25": "rank_bm25",
        "onnxruntime": "onnxruntime",
    }
    return {name: _is_module_available(module) for name, module in modules.items()}


def _preflight_runtime_dependencies(cfg: Config, command_name: str) -> Config:
    """Check runtime dependencies before executing command."""
    report = _doctor_dependency_report()
    resolved_backends = dict(cfg.backends)
    warnings: list[str] = []
    errors: list[str] = []

    embeddings_backend = cfg.backends.get("embeddings", "auto")
    api_key_env = str(cfg.embeddings.get("api_key_env", "OPENAI_API_KEY"))

    if embeddings_backend == "local" and not report.get("sentence-transformers", False):
        errors.append("embeddings=local requires sentence-transformers")
    elif embeddings_backend == "api":
        if not _is_module_available("openai"):
            errors.append("embeddings=api requires openai package")
        if not os.environ.get(api_key_env):
            errors.append(f"embeddings=api requires environment variable {api_key_env}")
    elif embeddings_backend == "auto":
        if report.get("sentence-transformers", False):
            resolved_backends["embeddings"] = "local"
        elif _is_module_available("openai") and os.environ.get(api_key_env):
            resolved_backends["embeddings"] = "api"
            warnings.append("embeddings auto-resolved to api (sentence-transformers unavailable)")
        else:
            warnings.append(
                "embeddings auto could not be validated (local/api requirements may be missing)"
            )

    vector_backend = cfg.backends.get("vector_index", "auto")
    if vector_backend == "native-leann" and not report.get("leann", False):
        errors.append("vector_index=native-leann requires leann")
    elif vector_backend == "faiss" and not report.get("faiss-cpu", False):
        errors.append("vector_index=faiss requires faiss-cpu")
    elif vector_backend == "auto":
        if report.get("leann", False):
            resolved_backends["vector_index"] = "native-leann"
        elif report.get("faiss-cpu", False):
            resolved_backends["vector_index"] = "faiss"
            warnings.append("vector_index auto-resolved to faiss (leann unavailable)")
        else:
            resolved_backends["vector_index"] = "leann"
            warnings.append("vector_index auto-resolved to leann fallback")

    graph_backend = cfg.backends.get("graph", "auto")
    if graph_backend == "igraph" and not report.get("igraph", False):
        errors.append("graph=igraph requires python-igraph")
    elif graph_backend == "networkx" and not report.get("networkx", False):
        errors.append("graph=networkx requires networkx")
    elif graph_backend == "auto":
        if report.get("igraph", False):
            resolved_backends["graph"] = "igraph"
        elif report.get("networkx", False):
            resolved_backends["graph"] = "networkx"
            warnings.append("graph auto-resolved to networkx (igraph unavailable)")
        else:
            warnings.append("graph auto could not be validated (igraph/networkx may be missing)")

    if errors:
        details = "\n".join(f"- {item}" for item in errors)
        raise RuntimeError(
            f"Dependency check failed for '{command_name}':\n{details}\n"
            f'Recommended install: pip install "ws-ctx-engine[all]"\n'
            f"Or run: ws-ctx-engine doctor"
        )

    if warnings and not AGENT_MODE:
        console.print("[yellow]Dependency preflight:[/yellow]")
        for warning in warnings:
            console.print(f"[yellow]- {warning}[/yellow]")

    cfg.backends = resolved_backends
    return cfg


def _load_config(config_path: str | None, repo_path: str | None = None) -> Config:
    """
    Load configuration from file or use defaults.

    Args:
        config_path: Optional path to custom configuration file
        repo_path: Optional repository path to look for .ws-ctx-engine.yaml

    Returns:
        Config instance

    Raises:
        typer.Exit: If config file is specified but doesn't exist
    """
    import typer

    cfg: Config

    if config_path is not None:
        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            console.print(f"[red]Error:[/red] Configuration file not found: {config_path}")
            raise typer.Exit(code=1)

        cfg = Config.load(config_path)
    elif repo_path is not None:
        repo_config = Path(repo_path) / ".ws-ctx-engine.yaml"
        if repo_config.exists():
            cfg = Config.load(str(repo_config))
        else:
            cfg = Config.load()
    else:
        cfg = Config.load()

    if repo_path is None:
        return cfg

    repo_path_obj = Path(repo_path)
    if repo_path_obj.exists() and repo_path_obj.is_dir():
        return _apply_gitignore_patterns(cfg, repo_path_obj)

    return cfg


def _load_graph_store_for_status(config: "Any", workspace: Path) -> "Any":
    """Load GraphStore for status display.

    Returns the store if healthy, None on any failure or when disabled.
    """
    try:
        if not getattr(config, "graph_store_enabled", True):
            return None
        from ..graph.cozo_store import GraphStore  # noqa: F401 — imported for test-patching

        db_path = Path(config.graph_store_path)
        if not db_path.is_absolute():
            db_path = workspace / db_path
        storage_str = f"{config.graph_store_storage}:{db_path}"
        store = GraphStore(storage_str)
        return store if store.is_healthy else None
    except Exception:
        return None


# Re-export GraphStore at module level so tests can patch
try:
    from ..graph.cozo_store import GraphStore  # noqa: F401
except Exception:  # pycozo not installed in all environments
    GraphStore = None  # type: ignore[assignment,misc]
