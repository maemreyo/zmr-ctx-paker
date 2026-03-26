"""
Command-line interface for ws-ctx-engine.

Provides CLI commands for indexing repositories, querying, and packing context.
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
import importlib.metadata
import importlib.util

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from ..config import Config
from ..workflow import index_repository, query_and_pack, search_codebase
from ..logger import get_logger
from ..mcp_server import run_mcp_server

# Initialize CLI app
app = typer.Typer(
    name="ws-ctx-engine",
    help="Intelligently package codebases into optimized context for Large Language Models",
    add_completion=False,
)

# Initialize console for rich output
console = Console()
logger = get_logger()
AGENT_MODE = False


def _set_console_log_level(level: int) -> None:
    logging.getLogger("ws_ctx_engine").setLevel(level)


def _set_agent_mode(enabled: bool) -> None:
    global AGENT_MODE, console
    AGENT_MODE = enabled
    console = Console(stderr=enabled)


def _emit_ndjson(payload: dict[str, Any]) -> None:
    if AGENT_MODE:
        typer.echo(json.dumps(payload, ensure_ascii=False))


def _enable_command_agent_mode(command_agent_mode: bool) -> None:
    if command_agent_mode and not AGENT_MODE:
        _set_agent_mode(True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _copy_to_clipboard(text: str) -> None:
    """Copy *text* to the system clipboard (macOS / Linux / Windows)."""
    import subprocess
    candidates = [
        (["pbcopy"], {}),                                    # macOS
        (["clip"], {}),                                      # Windows
        (["xclip", "-selection", "clipboard"], {}),          # Linux (xclip)
        (["xsel", "--clipboard", "--input"], {}),             # Linux (xsel)
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
    console.print(
        "[yellow]Warning:[/yellow] Could not copy to clipboard (no clipboard tool found)",
        file=sys.stderr,
    )


def _extract_gitignore_patterns(repo_path: Path) -> list[str]:
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


def _build_smart_config(repo_path: Path, include_gitignore: bool, vector_index: str, graph: str, embeddings_backend: str) -> dict[str, Any]:
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


def _parse_rate_limits(values: List[str]) -> dict[str, int]:
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
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def _doctor_dependency_report() -> dict[str, bool]:
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
    }
    return {name: _is_module_available(module) for name, module in modules.items()}


def _preflight_runtime_dependencies(cfg: Config, command_name: str) -> Config:
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
            warnings.append("embeddings auto could not be validated (local/api requirements may be missing)")

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
            f"Recommended install: pip install \"ws-ctx-engine[all]\"\n"
            f"Or run: ws-ctx-engine doctor"
        )

    if warnings and not AGENT_MODE:
        console.print("[yellow]Dependency preflight:[/yellow]")
        for warning in warnings:
            console.print(f"[yellow]- {warning}[/yellow]")

    cfg.backends = resolved_backends
    return cfg


@app.command()
def doctor() -> None:
    """Check optional dependencies and recommend setup profile."""
    report = _doctor_dependency_report()

    recommended_all = [
        "leann",
        "igraph",
        "sentence-transformers",
        "tree-sitter",
        "tree-sitter-python",
        "tree-sitter-javascript",
        "tree-sitter-typescript",
        "tree-sitter-rust",
    ]

    console.print("[bold]Dependency Doctor[/bold]")
    for name in sorted(report.keys()):
        status = "[green]OK[/green]" if report[name] else "[yellow]MISSING[/yellow]"
        console.print(f"- {name:<24} {status}")

    missing_all = [name for name in recommended_all if not report.get(name, False)]

    if not missing_all:
        console.print("\n[bold green]✓ Ready for full feature set (all backends available).[/bold green]")
        raise typer.Exit(code=0)

    console.print("\n[yellow]Some recommended dependencies are missing for full feature set.[/yellow]")
    typer.echo('Recommended install: pip install "ws-ctx-engine[all]"')
    console.print("[yellow]Missing:[/yellow] " + ", ".join(missing_all))
    raise typer.Exit(code=1)


def version_callback(value: bool):
    if value:
        try:
            version = importlib.metadata.version("ws-ctx-engine")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
        console.print(f"ws-ctx-engine version: [bold cyan]{version}[/bold cyan]")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show the application's version and exit.",
    ),
    agent_mode: bool = typer.Option(
        False,
        "--agent-mode",
        help="Emit parseable NDJSON on stdout and send human-readable logs to stderr.",
    ),
    quiet: bool = typer.Option(
        True,
        "--quiet/--no-quiet",
        help="Suppress informational logs in terminal; only warnings/errors are shown.",
    ),
):
    """
    Intelligently package codebases into optimized context for Large Language Models.
    """
    _set_agent_mode(agent_mode)
    if quiet:
        _set_console_log_level(logging.WARNING)


@app.command()
def index(
    repo_path: str = typer.Argument(
        ...,
        help="Path to the repository root directory",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging with detailed timing information",
    ),
    incremental: bool = typer.Option(
        False,
        "--incremental",
        help="Only re-index files that have changed since last build (M6).",
    ),
) -> None:
    """
    Build and save indexes for a repository.

    This command parses the codebase, builds vector and graph indexes,
    and saves them to .ws-ctx-engine/ for later queries.

    Requirements: 11.2
    """
    try:
        # Load configuration
        cfg = _load_config(config, repo_path=repo_path)

        # Set verbose mode
        if verbose:
            logger.logger.setLevel("DEBUG")
        
        # Validate repo path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson({"type": "error", "command": "index", "error": "repo_not_found", "repo": repo_path})
            raise typer.Exit(code=1)

        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson({"type": "error", "command": "index", "error": "repo_not_directory", "repo": repo_path})
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "index")

        # Display start message
        console.print(Panel.fit(
            f"[bold cyan]Indexing repository:[/bold cyan] {repo_path}",
            border_style="cyan"
        ))
        
        # Run indexing
        index_repository(repo_path=repo_path, config=cfg, incremental=incremental)
        
        # Display success message
        console.print("[bold green]✓[/bold green] Indexing complete!")
        console.print(f"Indexes saved to: {repo_path_obj / '.ws-ctx-engine'}")
        _emit_ndjson({
            "type": "status",
            "command": "index",
            "status": "success",
            "repo": str(repo_path_obj),
            "index_dir": str(repo_path_obj / '.ws-ctx-engine'),
            "generated_at": _utc_now(),
        })

        raise typer.Exit(code=0)
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during indexing:[/red] {e}")
        logger.log_error(e, {"command": "index", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "index", "error": str(e)})
        raise typer.Exit(code=1)


@app.command()
def search(
    query_text: str = typer.Argument(
        ...,
        help="Natural language query for semantic search",
    ),
    repo_path: str = typer.Option(
        ".",
        "--repo",
        "-r",
        help="Path to the repository root directory",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        min=1,
        max=50,
        help="Maximum number of ranked results to return (1-50)",
    ),
    domain_filter: Optional[str] = typer.Option(
        None,
        "--domain-filter",
        help="Optional domain filter applied to results.",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging with detailed timing information",
    ),
    agent_mode: bool = typer.Option(
        False,
        "--agent-mode",
        help="Emit parseable NDJSON on stdout and send human-readable logs to stderr.",
    ),
) -> None:
    """Search the indexed codebase and return ranked file paths."""
    try:
        _enable_command_agent_mode(agent_mode)
        cfg = _load_config(config, repo_path=repo_path)

        if verbose:
            logger.logger.setLevel("DEBUG")

        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson({"type": "error", "command": "search", "error": "repo_not_found", "repo": repo_path})
            raise typer.Exit(code=1)

        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson({"type": "error", "command": "search", "error": "repo_not_directory", "repo": repo_path})
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "search")

        if not AGENT_MODE:
            console.print(Panel.fit(
                f"[bold cyan]Searching:[/bold cyan] {query_text}\n"
                f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
                f"[bold cyan]Limit:[/bold cyan] {limit}",
                border_style="cyan"
            ))

        results, index_health = search_codebase(
            repo_path=repo_path,
            query=query_text,
            config=cfg,
            limit=limit,
            domain_filter=domain_filter,
        )

        _emit_ndjson({
            "type": "meta",
            "query": query_text,
            "limit": limit,
            "domain_filter": domain_filter,
            "index_built_at": index_health.get("index_built_at"),
            "files_indexed": index_health.get("files_indexed"),
            "index_health": index_health,
            "generated_at": _utc_now(),
        })

        if AGENT_MODE:
            for rank, result in enumerate(results, start=1):
                _emit_ndjson({
                    "type": "result",
                    "rank": rank,
                    "path": result["path"],
                    "score": result["score"],
                    "domain": result["domain"],
                    "summary": result["summary"],
                })
        else:
            if not results:
                console.print("[yellow]No matching files found.[/yellow]")
            for rank, result in enumerate(results, start=1):
                console.print(
                    f"{rank}. {result['path']:<40} "
                    f"[{result['score']:.2f}] {result['domain']:<20} {result['summary']}"
                )

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes")
        _emit_ndjson({"type": "error", "command": "search", "error": str(e)})
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error during search:[/red] {e}")
        logger.log_error(e, {"command": "search", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "search", "error": str(e)})
        raise typer.Exit(code=1)


@app.command()
def mcp(
    workspace: Optional[str] = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace root bound to MCP session (overrides mcp_config.workspace when set)",
    ),
    mcp_config: Optional[str] = typer.Option(
        None,
        "--mcp-config",
        help="Path to MCP config JSON (defaults to .ws-ctx-engine/mcp_config.json)",
    ),
    rate_limit: List[str] = typer.Option(
        [],
        "--rate-limit",
        help="Override rate limit as TOOL=LIMIT, e.g. search_codebase=60",
    ),
) -> None:
    """Run ws-ctx-engine as an MCP stdio server bound to a single workspace."""
    try:
        if workspace is not None:
            workspace_path = Path(workspace)
            if not workspace_path.exists() or not workspace_path.is_dir():
                console.print(f"[red]Error:[/red] Invalid workspace path: {workspace}")
                raise typer.Exit(code=1)
            resolved_workspace: Optional[str] = str(workspace_path.resolve())
        else:
            resolved_workspace = None

        try:
            parsed_limits = _parse_rate_limits(rate_limit)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1)

        run_mcp_server(
            workspace=resolved_workspace,
            config_path=mcp_config,
            rate_limit=parsed_limits,
        )
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        raise typer.Exit(code=0)
    except Exception as e:
        console.print(f"[red]Error starting MCP server:[/red] {e}")
        logger.log_error(e, {"command": "mcp", "workspace": workspace})
        raise typer.Exit(code=1)


@app.command()
def query(
    query_text: str = typer.Argument(
        ...,
        help="Natural language query for semantic search",
    ),
    repo_path: str = typer.Option(
        ".",
        "--repo",
        "-r",
        help="Path to the repository root directory",
    ),
    format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format: 'xml', 'zip', 'json', 'yaml', 'md', or 'toon' (experimental)",
    ),
    budget: Optional[int] = typer.Option(
        None,
        "--budget",
        "-b",
        help="Token budget for context window",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging with detailed timing information",
    ),
    secrets_scan: bool = typer.Option(
        False,
        "--secrets-scan",
        help="Enable secret scanning and redact sensitive file content in generated outputs.",
    ),
    agent_mode: bool = typer.Option(
        False,
        "--agent-mode",
        help="Emit parseable NDJSON on stdout and send human-readable logs to stderr.",
    ),
    stdout: bool = typer.Option(
        False,
        "--stdout",
        help="Write output content to stdout instead of saving to file.",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        help="Copy output to clipboard after packing.",
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        help="Apply smart compression: full content for high-relevance files, signatures for others.",
    ),
    shuffle: bool = typer.Option(
        True,
        "--shuffle/--no-shuffle",
        help="Reorder files to combat 'Lost in the Middle' (default: on).",
    ),
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        help="Agent phase mode: 'discovery', 'edit', or 'test'. Adjusts ranking weights.",
    ),
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Session identifier for semantic deduplication cache.",
    ),
    no_dedup: bool = typer.Option(
        False,
        "--no-dedup",
        help="Disable session-level semantic deduplication.",
    ),
) -> None:
    """
    Search indexes and generate output.

    This command loads pre-built indexes, performs semantic search,
    and generates output in the configured format.

    Requirements: 11.3
    """
    try:
        _enable_command_agent_mode(agent_mode)

        # Load configuration
        cfg = _load_config(config, repo_path=repo_path)

        # Override config with CLI flags
        if format is not None:
            if format not in ["xml", "zip", "json", "yaml", "md", "toon"]:
                console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml', 'zip', 'json', 'yaml', 'md', or 'toon'")
                _emit_ndjson({"type": "error", "command": "query", "error": "invalid_format", "format": format})
                raise typer.Exit(code=1)
            cfg.format = format

        if budget is not None:
            if budget <= 0:
                console.print(f"[red]Error:[/red] Budget must be positive, got {budget}")
                _emit_ndjson({"type": "error", "command": "query", "error": "invalid_budget", "budget": budget})
                raise typer.Exit(code=1)
            cfg.token_budget = budget

        # Set verbose mode
        if verbose:
            logger.logger.setLevel("DEBUG")

        # Validate repo path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson({"type": "error", "command": "query", "error": "repo_not_found", "repo": repo_path})
            raise typer.Exit(code=1)

        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson({"type": "error", "command": "query", "error": "repo_not_directory", "repo": repo_path})
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "query")

        _stdout_formats = {"json", "xml", "yaml", "md"}
        stdout_mode = stdout or (cfg.format in _stdout_formats and not AGENT_MODE)
        json_stdout_mode = cfg.format == "json" and not AGENT_MODE and not stdout

        # Validate mode flag
        if mode is not None and mode not in ("discovery", "edit", "test"):
            console.print(f"[red]Error:[/red] Invalid --mode '{mode}'. Must be 'discovery', 'edit', or 'test'")
            raise typer.Exit(code=1)

        # Display start message
        if not AGENT_MODE and not json_stdout_mode and not stdout:
            console.print(Panel.fit(
                f"[bold cyan]Querying:[/bold cyan] {query_text}\n"
                f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
                f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
                f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
                border_style="cyan"
            ))

        # Run query
        output_path, query_meta = query_and_pack(
            repo_path=repo_path,
            query=query_text,
            config=cfg,
            secrets_scan=secrets_scan,
            compress=compress,
            shuffle=shuffle,
            agent_phase=mode,
            session_id=None if no_dedup else session_id,
        )

        is_binary_format = cfg.format == "zip"
        output_content = (
            None if is_binary_format
            else Path(output_path).read_text(encoding="utf-8")
        )
        total_tokens = query_meta.get("total_tokens", 0) if isinstance(query_meta, dict) else 0

        # Display success message
        if stdout and output_content is not None:
            typer.echo(output_content)
        elif json_stdout_mode and output_content is not None:
            typer.echo(output_content)
        elif not AGENT_MODE:
            console.print("[bold green]✓[/bold green] Query complete!")
            if total_tokens:
                console.print(f"[green]Context packed ({total_tokens:,} / {cfg.token_budget:,} tokens)[/green]")
            console.print(f"Output saved to: {output_path}")

        if copy and output_content is not None:
            _copy_to_clipboard(output_content)

        _emit_ndjson({
            "type": "status",
            "command": "query",
            "status": "success",
            "output_path": str(output_path),
            "total_tokens": total_tokens,
            "generated_at": _utc_now(),
        })

        raise typer.Exit(code=0)
        
    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes")
        _emit_ndjson({"type": "error", "command": "query", "error": str(e)})
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error during query:[/red] {e}")
        logger.log_error(e, {"command": "query", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "query", "error": str(e)})
        raise typer.Exit(code=1)


@app.command()
def pack(
    repo_path: str = typer.Argument(
        ".",
        help="Path to the repository root directory (defaults to current directory)",
    ),
    query_text: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Optional natural language query for semantic search",
    ),
    changed_files_path: Optional[str] = typer.Option(
        None,
        "--changed-files",
        help="Path to a file listing changed files (one per line) for PageRank boosting.",
    ),
    format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format: 'xml', 'zip', 'json', 'yaml', 'md', or 'toon' (experimental)",
    ),
    budget: Optional[int] = typer.Option(
        None,
        "--budget",
        "-b",
        help="Token budget for context window",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging with detailed timing information",
    ),
    secrets_scan: bool = typer.Option(
        False,
        "--secrets-scan",
        help="Enable secret scanning and redact sensitive file content in generated outputs.",
    ),
    agent_mode: bool = typer.Option(
        False,
        "--agent-mode",
        help="Emit parseable NDJSON on stdout and send human-readable logs to stderr.",
    ),
    stdout: bool = typer.Option(
        False,
        "--stdout",
        help="Write output content to stdout instead of saving to file.",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        help="Copy output to clipboard after packing.",
    ),
    compress: bool = typer.Option(
        False,
        "--compress",
        help="Apply smart compression: full content for high-relevance files, signatures for others.",
    ),
    shuffle: bool = typer.Option(
        True,
        "--shuffle/--no-shuffle",
        help="Reorder files to combat 'Lost in the Middle' (default: on in agent-mode).",
    ),
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        help="Agent phase mode: 'discovery', 'edit', or 'test'. Adjusts ranking weights.",
    ),
    session_id: str = typer.Option(
        "default",
        "--session-id",
        help="Session identifier for semantic deduplication cache.",
    ),
    no_dedup: bool = typer.Option(
        False,
        "--no-dedup",
        help="Disable session-level semantic deduplication.",
    ),
) -> None:
    """
    Execute full workflow: index, query, and pack.

    This command performs the complete workflow: builds indexes if needed,
    performs semantic search (if query provided), and generates output.

    Requirements: 11.4
    """
    try:
        _enable_command_agent_mode(agent_mode)

        # Load configuration
        cfg = _load_config(config, repo_path=repo_path)

        # Override config with CLI flags
        if format is not None:
            if format not in ["xml", "zip", "json", "yaml", "md", "toon"]:
                console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml', 'zip', 'json', 'yaml', 'md', or 'toon'")
                _emit_ndjson({"type": "error", "command": "pack", "error": "invalid_format", "format": format})
                raise typer.Exit(code=1)
            cfg.format = format
        
        if budget is not None:
            if budget <= 0:
                console.print(f"[red]Error:[/red] Budget must be positive, got {budget}")
                _emit_ndjson({"type": "error", "command": "pack", "error": "invalid_budget", "budget": budget})
                raise typer.Exit(code=1)
            cfg.token_budget = budget
        
        # Set verbose mode
        if verbose:
            logger.logger.setLevel("DEBUG")
        
        # Validate repo path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson({"type": "error", "command": "pack", "error": "repo_not_found", "repo": repo_path})
            raise typer.Exit(code=1)
        
        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson({"type": "error", "command": "pack", "error": "repo_not_directory", "repo": repo_path})
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "pack")

        _stdout_formats = {"json", "xml", "yaml", "md"}
        stdout_mode = stdout or (cfg.format in _stdout_formats and not AGENT_MODE)
        json_stdout_mode = cfg.format == "json" and not AGENT_MODE and not stdout

        # Validate mode flag
        if mode is not None and mode not in ("discovery", "edit", "test"):
            console.print(f"[red]Error:[/red] Invalid --mode '{mode}'. Must be 'discovery', 'edit', or 'test'")
            raise typer.Exit(code=1)

        # Display start message
        if not AGENT_MODE and not json_stdout_mode and not stdout:
            console.print(Panel.fit(
                f"[bold cyan]Packing repository:[/bold cyan] {repo_path}\n"
                f"[bold cyan]Query:[/bold cyan] {query_text or 'None (using PageRank only)'}\n"
                f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
                f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
                border_style="cyan"
            ))

        # Parse --changed-files file if provided
        changed_files: Optional[List[str]] = None
        if changed_files_path is not None:
            cf_path = Path(changed_files_path)
            if not cf_path.exists():
                console.print(f"[red]Error:[/red] --changed-files path does not exist: {changed_files_path}")
                raise typer.Exit(code=1)
            lines = cf_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            changed_files = [ln.strip() for ln in lines if ln.strip()]

        # Step 1: Index (will auto-rebuild if stale)
        if not AGENT_MODE and not json_stdout_mode and not stdout:
            console.print("\n[bold]Step 1:[/bold] Checking indexes...")
        index_path = repo_path_obj / ".ws-ctx-engine"

        if not index_path.exists() or not (index_path / "metadata.json").exists():
            if not AGENT_MODE and not json_stdout_mode and not stdout:
                console.print("  → Building indexes (first time)...")
            index_repository(repo_path=repo_path, config=cfg)
        else:
            if not AGENT_MODE and not json_stdout_mode and not stdout:
                console.print("  → Indexes found (will auto-rebuild if stale)")

        # Step 2: Query and pack
        if not AGENT_MODE and not json_stdout_mode and not stdout:
            console.print("\n[bold]Step 2:[/bold] Querying and packing...")
        output_path, pack_meta = query_and_pack(
            repo_path=repo_path,
            query=query_text,
            changed_files=changed_files,
            config=cfg,
            secrets_scan=secrets_scan,
            compress=compress,
            shuffle=shuffle,
            agent_phase=mode,
            session_id=None if no_dedup else session_id,
        )

        is_binary_format = cfg.format == "zip"
        output_content = (
            None if is_binary_format
            else Path(output_path).read_text(encoding="utf-8")
        )
        total_tokens = pack_meta.get("total_tokens", 0) if isinstance(pack_meta, dict) else 0
        budget_tokens = cfg.token_budget

        # Display success message
        if stdout and output_content is not None:
            typer.echo(output_content)
        elif json_stdout_mode and output_content is not None:
            typer.echo(output_content)
        elif not AGENT_MODE:
            console.print("\n[bold green]✓[/bold green] Packing complete!")
            if total_tokens:
                console.print(f"[green]Context packed ({total_tokens:,} / {budget_tokens:,} tokens)[/green]")
            console.print(f"Output saved to: {output_path}")

        if copy and output_content is not None:
            _copy_to_clipboard(output_content)

        _emit_ndjson({
            "type": "status",
            "command": "pack",
            "status": "success",
            "output_path": str(output_path),
            "total_tokens": total_tokens,
            "generated_at": _utc_now(),
        })

        raise typer.Exit(code=0)
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during packing:[/red] {e}")
        logger.log_error(e, {"command": "pack", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "pack", "error": str(e)})
        raise typer.Exit(code=1)


@app.command()
def status(
    repo_path: str = typer.Argument(
        ...,
        help="Path to the repository root directory",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
    agent_mode: bool = typer.Option(
        False,
        "--agent-mode",
        help="Emit parseable NDJSON on stdout and send human-readable logs to stderr.",
    ),
) -> None:
    """
    Show index status and statistics.

    Displays information about the current index including:
    - Index directory location and total size
    - Number of indexed files
    - Vector index and graph statistics
    - Domain map database statistics

    Requirements: 11.9
    """
    try:
        _enable_command_agent_mode(agent_mode)
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson({"type": "error", "command": "status", "error": "repo_not_found", "repo": repo_path})
            raise typer.Exit(code=1)

        index_path = repo_path_obj / ".ws-ctx-engine"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes")
            _emit_ndjson({"type": "error", "command": "status", "error": "index_not_found", "index_dir": str(index_path)})
            raise typer.Exit(code=1)

        if not (index_path / "metadata.json").exists():
            console.print(f"[red]Error:[/red] Incomplete index - metadata.json is missing")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' to rebuild indexes")
            _emit_ndjson({"type": "error", "command": "status", "error": "metadata_missing", "index_dir": str(index_path)})
            raise typer.Exit(code=1)

        import json
        with open(index_path / "metadata.json", "r") as f:
            metadata = json.load(f)

        total_size = sum(f.stat().st_size for f in index_path.rglob("*") if f.is_file())

        if not AGENT_MODE:
            console.print(f"\n[bold]Index Status for:[/bold] {repo_path}")
            console.print(f"[bold]Index directory:[/bold] {index_path}")
            console.print(f"[bold]Total size:[/bold] {total_size / 1024:.1f} KB")

            console.print(f"\n[bold]Indexed Files:[/bold] {metadata.get('file_count', 'unknown')}")
            console.print(f"[bold]Backend:[/bold] {metadata.get('backend', 'unknown')}")

            if (index_path / "vector.idx").exists():
                vec_size = (index_path / "vector.idx").stat().st_size
                console.print(f"[bold]Vector index size:[/bold] {vec_size / 1024:.1f} KB")

            if (index_path / "graph.pkl").exists():
                graph_size = (index_path / "graph.pkl").stat().st_size
                console.print(f"[bold]Graph index size:[/bold] {graph_size / 1024:.1f} KB")

            if (index_path / "domain_map.db").exists():
                db_size = (index_path / "domain_map.db").stat().st_size
                console.print(f"[bold]Domain map DB size:[/bold] {db_size / 1024:.1f} KB")

                from ..domain_map import DomainMapDB
                db = DomainMapDB(str(index_path / "domain_map.db"))
                stats = db.stats()
                console.print(f"[bold]Domain keywords:[/bold] {stats['keywords']}")
                console.print(f"[bold]Domain directories:[/bold] {stats['directories']}")
                db.close()

        if AGENT_MODE:
            _emit_ndjson({
                "type": "status",
                "command": "status",
                "repo": str(repo_path_obj),
                "index_dir": str(index_path),
                "file_count": metadata.get("file_count", 0),
                "backend": metadata.get("backend", "unknown"),
                "indexed_at": metadata.get("created_at", "unknown"),
                "total_size_bytes": total_size,
                "generated_at": _utc_now(),
            })
        else:
            console.print(f"\n[bold]Last indexed:[/bold] {metadata.get('created_at', 'unknown')}")

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error showing status:[/red] {e}")
        logger.log_error(e, {"command": "status", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "status", "error": str(e)})
        raise typer.Exit(code=1)


@app.command()
def vacuum(
    repo_path: str = typer.Argument(
        ...,
        help="Path to the repository root directory",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
) -> None:
    """
    Optimize SQLite database by running VACUUM.

    This command reclaims disk space and optimizes the SQLite database
    for better performance. The domain_map.db file will be rebuilt.

    Requirements: 11.10
    """
    try:
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)

        index_path = repo_path_obj / ".ws-ctx-engine"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes")
            raise typer.Exit(code=1)

        db_path = index_path / "domain_map.db"
        if not db_path.exists():
            console.print(f"[red]Error:[/red] Domain map database not found: {db_path}")
            raise typer.Exit(code=1)

        from ..domain_map import DomainMapDB
        db = DomainMapDB(str(db_path))

        console.print(f"[bold]Running VACUUM on:[/bold] {db_path}")

        conn = db._get_conn()
        conn.execute("VACUUM")
        db.close()

        new_size = db_path.stat().st_size
        console.print(f"\n[bold green]✓[/bold green] VACUUM complete!")
        console.print(f"Database size after optimization: {new_size / 1024:.1f} KB")

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during VACUUM:[/red] {e}")
        logger.log_error(e, {"command": "vacuum", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "vacuum", "error": str(e)})
        raise typer.Exit(code=1)


@app.command()
def reindex_domain(
    repo_path: str = typer.Argument(
        ...,
        help="Path to the repository root directory",
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom configuration file",
    ),
) -> None:
    """
    Rebuild only the domain map database (SQLite).

    This command re-extracts domain keywords from existing indexes
    and rebuilds the domain_map.db file without rebuilding the
    entire vector index or graph. This is much faster than a full
    reindex and is useful when only the domain mapping needs updating.

    Requirements: 11.11
    """
    try:
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)

        index_path = repo_path_obj / ".ws-ctx-engine"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes")
            raise typer.Exit(code=1)

        if not (index_path / "metadata.json").exists():
            console.print(f"[red]Error:[/red] Incomplete index - metadata.json is missing")
            raise typer.Exit(code=1)

        console.print("[bold]Rebuilding domain map database...[/bold]")

        from ..workflow.indexer import index_repository
        tracker = index_repository(
            repo_path=repo_path,
            config=_load_config(config, repo_path=repo_path),
            index_dir=".ws-ctx-engine",
            domain_only=True
        )

        console.print(f"\n[bold green]✓[/bold green] Domain map rebuilt!")
        console.print(tracker.format_metrics("index"))

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error rebuilding domain map:[/red] {e}")
        logger.log_error(e, {"command": "reindex-domain", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "reindex-domain", "error": str(e)})
        raise typer.Exit(code=1)


@app.command("init-config")
def init_config(
    repo_path: str = typer.Argument(
        ".",
        help="Path to the repository root directory (defaults to current directory)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing .ws-ctx-engine.yaml",
    ),
    include_gitignore: bool = typer.Option(
        True,
        "--include-gitignore/--no-include-gitignore",
        help="Include .gitignore patterns into exclude_patterns",
    ),
    vector_index: str = typer.Option(
        "auto",
        "--vector-index",
        help="Vector index backend: auto | native-leann | leann | faiss",
    ),
    graph: str = typer.Option(
        "auto",
        "--graph",
        help="Graph backend: auto | igraph | networkx",
    ),
    embeddings_backend: str = typer.Option(
        "auto",
        "--embeddings",
        help="Embeddings backend: auto | local | api",
    ),
) -> None:
    """Generate a smart `.ws-ctx-engine.yaml` for the target repository."""
    try:
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)
        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            raise typer.Exit(code=1)

        valid_vector = {"auto", "native-leann", "leann", "faiss"}
        valid_graph = {"auto", "igraph", "networkx"}
        valid_embeddings = {"auto", "local", "api"}

        if vector_index not in valid_vector:
            console.print(f"[red]Error:[/red] Invalid --vector-index: {vector_index}")
            raise typer.Exit(code=1)
        if graph not in valid_graph:
            console.print(f"[red]Error:[/red] Invalid --graph: {graph}")
            raise typer.Exit(code=1)
        if embeddings_backend not in valid_embeddings:
            console.print(f"[red]Error:[/red] Invalid --embeddings: {embeddings_backend}")
            raise typer.Exit(code=1)

        target_config = repo_path_obj / ".ws-ctx-engine.yaml"
        if target_config.exists() and not force:
            console.print(
                f"[yellow]Config already exists:[/yellow] {target_config}. "
                "Use --force to overwrite."
            )
            raise typer.Exit(code=1)

        payload = _build_smart_config(
            repo_path=repo_path_obj,
            include_gitignore=include_gitignore,
            vector_index=vector_index,
            graph=graph,
            embeddings_backend=embeddings_backend,
        )

        target_config.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        gitignore_updated = _ensure_repo_gitignore_has_wsctx_artifacts(repo_path_obj)

        console.print(f"[bold green]✓[/bold green] Generated config: {target_config}")
        console.print(
            "Backends: "
            f"vector_index={vector_index}, graph={graph}, embeddings={embeddings_backend}"
        )
        if include_gitignore:
            console.print("Included .gitignore patterns into exclude_patterns")
        if gitignore_updated:
            console.print("Updated .gitignore with ws-ctx-engine artifact patterns")

        raise typer.Exit(code=0)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error generating config:[/red] {e}")
        logger.log_error(e, {"command": "init-config", "repo_path": repo_path})
        raise typer.Exit(code=1)


def _load_config(config_path: Optional[str], repo_path: Optional[str] = None) -> Config:
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


# ---------------------------------------------------------------------------
# session sub-app
# ---------------------------------------------------------------------------

session_app = typer.Typer(name="session", help="Manage session-level deduplication caches.")
app.add_typer(session_app)


@session_app.command("clear")
def session_clear(
    repo_path: str = typer.Argument(
        ".",
        help="Repository root used to locate .ws-ctx-engine/ cache directory.",
    ),
    session_id: Optional[str] = typer.Option(
        None,
        "--session-id",
        help="Clear only this session's cache.  Omit to clear ALL session caches.",
    ),
) -> None:
    """Delete session deduplication cache file(s)."""
    from ..session.dedup_cache import SessionDeduplicationCache, clear_all_sessions

    cache_dir = Path(repo_path) / ".ws-ctx-engine"
    if session_id:
        cache = SessionDeduplicationCache(session_id=session_id, cache_dir=cache_dir)
        cache.clear()
        console.print(f"[green]✓[/green] Cleared session cache: {session_id}")
    else:
        deleted = clear_all_sessions(cache_dir)
        console.print(f"[green]✓[/green] Cleared {deleted} session cache file(s) from {cache_dir}")


def main() -> None:
    """
    Main entry point for the CLI.

    This function is called when the user runs 'ws-ctx-engine' command.
    It handles all CLI commands and exits with appropriate status codes.

    Requirements: 11.1, 11.8
    """
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
