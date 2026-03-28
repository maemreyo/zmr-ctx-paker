"""Search command for querying indexed codebase."""

from pathlib import Path

import typer

from ..utils import (
    _emit_ndjson,
    _enable_command_agent_mode,
    _load_config,
    _preflight_runtime_dependencies,
    _utc_now,
)

app = typer.Typer(name="search", help="Search the indexed codebase and return ranked file paths.")


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
    domain_filter: str | None = typer.Option(
        None,
        "--domain-filter",
        help="Optional domain filter applied to results.",
    ),
    config: str | None = typer.Option(
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
    from ...logger import logger
    from ...workflow import search_codebase
    from ...main import console

    try:
        _enable_command_agent_mode(agent_mode)
        cfg = _load_config(config, repo_path=repo_path)

        if verbose:
            logger.logger.setLevel("DEBUG")

        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson(
                {"type": "error", "command": "search", "error": "repo_not_found", "repo": repo_path}
            )
            raise typer.Exit(code=1)

        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson(
                {
                    "type": "error",
                    "command": "search",
                    "error": "repo_not_directory",
                    "repo": repo_path,
                }
            )
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "search")

        # Get AGENT_MODE from utils module
        from ..utils import AGENT_MODE

        if not AGENT_MODE:
            console.print(
                Panel.fit(
                    f"[bold cyan]Searching:[/bold cyan] {query_text}\n"
                    f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
                    f"[bold cyan]Limit:[/bold cyan] {limit}",
                    border_style="cyan",
                )
            )

        results, index_health = search_codebase(
            repo_path=repo_path,
            query=query_text,
            config=cfg,
            limit=limit,
            domain_filter=domain_filter,
        )

        _emit_ndjson(
            {
                "type": "meta",
                "query": query_text,
                "limit": limit,
                "domain_filter": domain_filter,
                "index_built_at": index_health.get("index_built_at"),
                "files_indexed": index_health.get("files_indexed"),
                "index_health": index_health,
                "generated_at": _utc_now(),
            }
        )

        if AGENT_MODE:
            for rank, result in enumerate(results, start=1):
                _emit_ndjson(
                    {
                        "type": "result",
                        "rank": rank,
                        "path": result["path"],
                        "score": result["score"],
                        "domain": result["domain"],
                        "summary": result["summary"],
                    }
                )
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
        console.print(
            "\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes"
        )
        _emit_ndjson({"type": "error", "command": "search", "error": str(e)})
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error during search:[/red] {e}")
        logger.log_error(e, {"command": "search", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "search", "error": str(e)})
        raise typer.Exit(code=1) from e
