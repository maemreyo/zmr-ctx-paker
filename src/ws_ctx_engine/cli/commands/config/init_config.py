"""Init config command for generating configuration files."""

from pathlib import Path

import typer
import yaml

from ...utils import (
    _build_smart_config,
    _emit_ndjson,
    _ensure_repo_gitignore_has_wsctx_artifacts,
)

app = typer.Typer()


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
    from ...logger import logger
    from ...main import console

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
        raise typer.Exit(code=1) from e
