"""Reindex domain command for rebuilding domain map database."""

from pathlib import Path

import typer

from ...utils import _emit_ndjson, _load_config

app = typer.Typer()


@app.command("reindex-domain")
def reindex_domain(
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
) -> None:
    """
    Rebuild only the domain map database (SQLite).

    This command re-extracts domain keywords from existing indexes
    and rebuilds the domain_map.db file without rebuilding the
    entire vector index or graph. This is much faster than a full
    reindex and is useful when only the domain mapping needs updating.

    Requirements: 11.11
    """
    from ...logger import logger
    from ...workflow.indexer import index_repository
    from ...main import console

    try:
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)

        index_path = repo_path_obj / ".ws-ctx-engine"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print(
                "\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes"
            )
            raise typer.Exit(code=1)

        if not (index_path / "metadata.json").exists():
            console.print("[red]Error:[/red] Incomplete index - metadata.json is missing")
            raise typer.Exit(code=1)

        console.print("[bold]Rebuilding domain map database...[/bold]")

        tracker = index_repository(
            repo_path=repo_path,
            config=_load_config(config, repo_path=repo_path),
            index_dir=".ws-ctx-engine",
            domain_only=True,
        )

        console.print("\n[bold green]✓[/bold green] Domain map rebuilt!")
        console.print(tracker.format_metrics("index"))

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error rebuilding domain map:[/red] {e}")
        logger.log_error(e, {"command": "reindex-domain", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "reindex-domain", "error": str(e)})
        raise typer.Exit(code=1) from e
