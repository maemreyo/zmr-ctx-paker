"""Graph backup command."""

import shutil
from pathlib import Path

import typer

app = typer.Typer()


@app.command("backup")
def graph_backup(
    dest: str = typer.Argument(..., help="Destination directory for the backup."),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Workspace path (defaults to current directory).",
    ),
) -> None:
    """Back up the graph store (RocksDB / SQLite) to a destination directory."""
    from ...config import Config
    from ...main import console

    ws = workspace or Path.cwd()

    try:
        config = Config.load(str(ws / ".ws-ctx-engine.yaml"))
    except Exception:
        config = Config()

    if config.graph_store_storage == "mem":
        console.print("[yellow]In-memory graph store has no persistent data to back up.[/yellow]")
        raise typer.Exit(1)

    src_path = Path(config.graph_store_path)
    if not src_path.is_absolute():
        src_path = ws / src_path

    if not src_path.exists():
        console.print(
            f"[red]Graph store not found at {src_path}. "
            "Run 'wsctx index' first to create the store.[/red]"
        )
        raise typer.Exit(1)

    dest_path = Path(dest)
    if dest_path.exists():
        console.print(f"[red]Destination {dest_path} already exists. Remove it first.[/red]")
        raise typer.Exit(1)

    console.print(
        f"Backing up graph store from [cyan]{src_path}[/cyan] " f"to [cyan]{dest_path}[/cyan]..."
    )
    try:
        shutil.copytree(src_path, dest_path)
        size = sum(f.stat().st_size for f in dest_path.rglob("*") if f.is_file())
        console.print(f"[green]Backup complete.[/green] {size // 1024} KB copied.")
    except Exception as exc:
        console.print(f"[red]Backup failed: {exc}[/red]")
        raise typer.Exit(1) from exc
