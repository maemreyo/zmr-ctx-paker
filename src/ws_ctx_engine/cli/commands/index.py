"""Index command for building repository indexes."""

import typer

from ..utils import _emit_ndjson, _load_config, _preflight_runtime_dependencies, _utc_now

app = typer.Typer(name="index", help="Build and save indexes for a repository.")


@app.command()
def index(
    repo_path: str = typer.Argument(
        ...,
        help="Path to the repository root directory",
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
    from ...logger import logger
    from ...workflow import index_repository
    from ...main import console

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
            _emit_ndjson(
                {"type": "error", "command": "index", "error": "repo_not_found", "repo": repo_path}
            )
            raise typer.Exit(code=1)

        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson(
                {
                    "type": "error",
                    "command": "index",
                    "error": "repo_not_directory",
                    "repo": repo_path,
                }
            )
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "index")

        # Display start message
        console.print(
            Panel.fit(
                f"[bold cyan]Indexing repository:[/bold cyan] {repo_path}", border_style="cyan"
            )
        )

        # Run indexing
        index_repository(repo_path=repo_path, config=cfg, incremental=incremental)

        # Display success message
        console.print("[bold green]✓[/bold green] Indexing complete!")
        console.print(f"Indexes saved to: {repo_path_obj / '.ws-ctx-engine'}")
        _emit_ndjson(
            {
                "type": "status",
                "command": "index",
                "status": "success",
                "repo": str(repo_path_obj),
                "index_dir": str(repo_path_obj / ".ws-ctx-engine"),
                "generated_at": _utc_now(),
            }
        )

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during indexing:[/red] {e}")
        logger.log_error(e, {"command": "index", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "index", "error": str(e)})
        raise typer.Exit(code=1) from e
