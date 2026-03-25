"""
Command-line interface for ws-ctx-engine.

Provides CLI commands for indexing repositories, querying, and packing context.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
import importlib.metadata

import typer
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
):
    """
    Intelligently package codebases into optimized context for Large Language Models.
    """
    _set_agent_mode(agent_mode)


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

        # Display start message
        console.print(Panel.fit(
            f"[bold cyan]Indexing repository:[/bold cyan] {repo_path}",
            border_style="cyan"
        ))
        
        # Run indexing
        index_repository(repo_path=repo_path, config=cfg)
        
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
        help="Output format: 'xml', 'zip', 'json', or 'md'",
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
            if format not in ["xml", "zip", "json", "md"]:
                console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml', 'zip', 'json', or 'md'")
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
        
        json_stdout_mode = cfg.format == "json" and not AGENT_MODE

        # Display start message
        if not AGENT_MODE and not json_stdout_mode:
            console.print(Panel.fit(
                f"[bold cyan]Querying:[/bold cyan] {query_text}\n"
                f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
                f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
                f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
                border_style="cyan"
            ))
        
        # Run query
        output_path, _ = query_and_pack(
            repo_path=repo_path,
            query=query_text,
            config=cfg,
            secrets_scan=secrets_scan,
        )
        
        # Display success message
        if json_stdout_mode:
            typer.echo(Path(output_path).read_text(encoding="utf-8"))
        elif not AGENT_MODE:
            console.print("[bold green]✓[/bold green] Query complete!")
            console.print(f"Output saved to: {output_path}")

        _emit_ndjson({
            "type": "status",
            "command": "query",
            "status": "success",
            "output_path": str(output_path),
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
    format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format: 'xml', 'zip', 'json', or 'md'",
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
            if format not in ["xml", "zip", "json", "md"]:
                console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml', 'zip', 'json', or 'md'")
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
        
        json_stdout_mode = cfg.format == "json" and not AGENT_MODE

        # Display start message
        if not AGENT_MODE and not json_stdout_mode:
            console.print(Panel.fit(
                f"[bold cyan]Packing repository:[/bold cyan] {repo_path}\n"
                f"[bold cyan]Query:[/bold cyan] {query_text or 'None (using PageRank only)'}\n"
                f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
                f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
                border_style="cyan"
            ))

        # Step 1: Index (will auto-rebuild if stale)
        if not AGENT_MODE and not json_stdout_mode:
            console.print("\n[bold]Step 1:[/bold] Checking indexes...")
        index_path = repo_path_obj / ".ws-ctx-engine"
        
        if not index_path.exists() or not (index_path / "metadata.json").exists():
            if not AGENT_MODE and not json_stdout_mode:
                console.print("  → Building indexes (first time)...")
            index_repository(repo_path=repo_path, config=cfg)
        else:
            if not AGENT_MODE and not json_stdout_mode:
                console.print("  → Indexes found (will auto-rebuild if stale)")

        # Step 2: Query and pack
        if not AGENT_MODE and not json_stdout_mode:
            console.print("\n[bold]Step 2:[/bold] Querying and packing...")
        output_path, _ = query_and_pack(
            repo_path=repo_path,
            query=query_text,
            config=cfg,
            secrets_scan=secrets_scan,
        )
        
        # Display success message
        if json_stdout_mode:
            typer.echo(Path(output_path).read_text(encoding="utf-8"))
        elif not AGENT_MODE:
            console.print("\n[bold green]✓[/bold green] Packing complete!")
            console.print(f"Output saved to: {output_path}")

        _emit_ndjson({
            "type": "status",
            "command": "pack",
            "status": "success",
            "output_path": str(output_path),
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
                "indexed_at": metadata.get("indexed_at", "unknown"),
                "total_size_bytes": total_size,
                "generated_at": _utc_now(),
            })
        else:
            console.print(f"\n[bold]Last indexed:[/bold] {metadata.get('indexed_at', 'unknown')}")

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
    if config_path is not None:
        config_path_obj = Path(config_path)
        if not config_path_obj.exists():
            console.print(f"[red]Error:[/red] Configuration file not found: {config_path}")
            raise typer.Exit(code=1)
        
        return Config.load(config_path)
    
    # Try to load from repo_path/.ws-ctx-engine.yaml if repo_path is provided
    if repo_path is not None:
        repo_config = Path(repo_path) / ".ws-ctx-engine.yaml"
        if repo_config.exists():
            return Config.load(str(repo_config))
    
    # Try to load from default location, fall back to defaults
    return Config.load()


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
