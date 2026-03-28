"""Status command for showing index statistics."""

import json
from pathlib import Path

import typer

from ..utils import _emit_ndjson, _enable_command_agent_mode, _load_config, _load_graph_store_for_status

app = typer.Typer(name="status", help="Show index status and statistics.")


@app.command()
def status(
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
    from ...config import Config
    from ...domain_map import DomainMapDB
    from ...logger import logger
    from ...main import console

    try:
        _enable_command_agent_mode(agent_mode)
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson(
                {"type": "error", "command": "status", "error": "repo_not_found", "repo": repo_path}
            )
            raise typer.Exit(code=1)

        index_path = repo_path_obj / ".ws-ctx-engine"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print(
                "\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes"
            )
            _emit_ndjson(
                {
                    "type": "error",
                    "command": "status",
                    "error": "index_not_found",
                    "index_dir": str(index_path),
                }
            )
            raise typer.Exit(code=1)

        if not (index_path / "metadata.json").exists():
            console.print("[red]Error:[/red] Incomplete index - metadata.json is missing")
            console.print(
                "\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' to rebuild indexes"
            )
            _emit_ndjson(
                {
                    "type": "error",
                    "command": "status",
                    "error": "metadata_missing",
                    "index_dir": str(index_path),
                }
            )
            raise typer.Exit(code=1)

        with open(index_path / "metadata.json") as f:
            metadata = json.load(f)

        total_size = sum(f.stat().st_size for f in index_path.rglob("*") if f.is_file())

        # Get AGENT_MODE from utils module
        from ..utils import AGENT_MODE

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

                db = DomainMapDB(str(index_path / "domain_map.db"))
                stats = db.stats()
                console.print(f"[bold]Domain keywords:[/bold] {stats['keywords']}")
                console.print(f"[bold]Domain directories:[/bold] {stats['directories']}")
                db.close()

        # --- Graph store section (non-agent mode only) ---
        if not AGENT_MODE:
            try:
                cfg_for_status = Config.load(str(repo_path_obj / ".ws-ctx-engine.yaml"))
            except Exception:
                cfg_for_status = Config()

            graph_store = _load_graph_store_for_status(cfg_for_status, repo_path_obj)
            if graph_store is None:
                console.print(
                    "\n[bold]Graph store:[/bold] [yellow]unavailable[/yellow]"
                    " (run 'wsctx index' to enable)"
                )
            else:
                g_stats = graph_store.stats()
                console.print("\n[bold]Graph store:[/bold] [green]healthy[/green]")
                console.print(f"[bold]Graph nodes:[/bold] {g_stats.get('node_count', 0)}")
                console.print(f"[bold]Graph edges:[/bold] {g_stats.get('edge_count', 0)}")
                console.print(
                    f"[bold]Graph schema version:[/bold] {g_stats.get('schema_version', 'unknown')}"
                )

            # Overall readiness line
            vector_ready = (index_path / "vector.idx").exists()
            graph_ready = graph_store is not None
            if vector_ready and graph_ready:
                console.print("\n[bold]Ready:[/bold] [green]Yes (vector + graph)[/green]")
            elif vector_ready:
                console.print("\n[bold]Ready:[/bold] [yellow]Partial (vector only)[/yellow]")
            else:
                console.print("\n[bold]Ready:[/bold] [red]No[/red]")

        if AGENT_MODE:
            _emit_ndjson(
                {
                    "type": "status",
                    "command": "status",
                    "repo": str(repo_path_obj),
                    "index_dir": str(index_path),
                    "file_count": metadata.get("file_count", 0),
                    "backend": metadata.get("backend", "unknown"),
                    "indexed_at": metadata.get("created_at", "unknown"),
                    "total_size_bytes": total_size,
                    "generated_at": _utc_now(),
                }
            )
        else:
            console.print(f"\n[bold]Last indexed:[/bold] {metadata.get('created_at', 'unknown')}")

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error showing status:[/red] {e}")
        logger.log_error(e, {"command": "status", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "status", "error": str(e)})
        raise typer.Exit(code=1) from e
