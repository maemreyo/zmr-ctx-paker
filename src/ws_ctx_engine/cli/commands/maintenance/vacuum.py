"""Vacuum command for optimizing SQLite database."""

from pathlib import Path

import typer

from ...utils import _emit_ndjson

app = typer.Typer(name="maintenance", help="Maintenance commands.")


@app.command("vacuum")
def vacuum(
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
    Optimize SQLite database by running VACUUM.

    This command reclaims disk space and optimizes the SQLite database
    for better performance. The domain_map.db file will be rebuilt.

    Requirements: 11.10
    """
    from ...domain_map import DomainMapDB
    from ...logger import logger
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

        db_path = index_path / "domain_map.db"
        if not db_path.exists():
            console.print(f"[red]Error:[/red] Domain map database not found: {db_path}")
            raise typer.Exit(code=1)

        db = DomainMapDB(str(db_path))

        console.print(f"[bold]Running VACUUM on:[/bold] {db_path}")

        conn = db._get_conn()
        conn.execute("VACUUM")
        db.close()

        new_size = db_path.stat().st_size
        console.print("\n[bold green]✓[/bold green] VACUUM complete!")
        console.print(f"Database size after optimization: {new_size / 1024:.1f} KB")

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during VACUUM:[/red] {e}")
        logger.log_error(e, {"command": "vacuum", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "vacuum", "error": str(e)})
        raise typer.Exit(code=1) from e
