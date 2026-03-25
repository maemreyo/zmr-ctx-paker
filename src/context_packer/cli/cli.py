"""
Command-line interface for Context Packer.

Provides CLI commands for indexing repositories, querying, and packing context.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ..config import Config
from ..workflow import index_repository, query_and_pack
from ..logger import get_logger

# Initialize CLI app
app = typer.Typer(
    name="ctx-packer",
    help="Intelligently package codebases into optimized context for Large Language Models",
    add_completion=False,
)

# Initialize console for rich output
console = Console()
logger = get_logger()


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
    and saves them to .context-pack/ for later queries.
    
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
            raise typer.Exit(code=1)
        
        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
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
        console.print(f"Indexes saved to: {repo_path_obj / '.context-pack'}")
        
        raise typer.Exit(code=0)
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during indexing:[/red] {e}")
        logger.log_error(e, {"command": "index", "repo_path": repo_path})
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
        help="Output format: 'xml' or 'zip'",
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
) -> None:
    """
    Search indexes and generate output.
    
    This command loads pre-built indexes, performs semantic search,
    and generates output in the configured format (XML or ZIP).
    
    Requirements: 11.3
    """
    try:
        # Load configuration
        cfg = _load_config(config, repo_path=repo_path)
        
        # Override config with CLI flags
        if format is not None:
            if format not in ["xml", "zip"]:
                console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml' or 'zip'")
                raise typer.Exit(code=1)
            cfg.format = format
        
        if budget is not None:
            if budget <= 0:
                console.print(f"[red]Error:[/red] Budget must be positive, got {budget}")
                raise typer.Exit(code=1)
            cfg.token_budget = budget
        
        # Set verbose mode
        if verbose:
            logger.logger.setLevel("DEBUG")
        
        # Validate repo path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)
        
        # Display start message
        console.print(Panel.fit(
            f"[bold cyan]Querying:[/bold cyan] {query_text}\n"
            f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
            f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
            f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
            border_style="cyan"
        ))
        
        # Run query
        output_path = query_and_pack(
            repo_path=repo_path,
            query=query_text,
            config=cfg
        )
        
        # Display success message
        console.print("[bold green]✓[/bold green] Query complete!")
        console.print(f"Output saved to: {output_path}")
        
        raise typer.Exit(code=0)
        
    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("\n[yellow]Suggestion:[/yellow] Run 'context-pack index' first to build indexes")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error during query:[/red] {e}")
        logger.log_error(e, {"command": "query", "repo_path": repo_path})
        raise typer.Exit(code=1)


@app.command()
def pack(
    repo_path: str = typer.Argument(
        ...,
        help="Path to the repository root directory",
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
        help="Output format: 'xml' or 'zip'",
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
) -> None:
    """
    Execute full workflow: index, query, and pack.
    
    This command performs the complete workflow: builds indexes if needed,
    performs semantic search (if query provided), and generates output.
    
    Requirements: 11.4
    """
    try:
        # Load configuration
        cfg = _load_config(config, repo_path=repo_path)
        
        # Override config with CLI flags
        if format is not None:
            if format not in ["xml", "zip"]:
                console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml' or 'zip'")
                raise typer.Exit(code=1)
            cfg.format = format
        
        if budget is not None:
            if budget <= 0:
                console.print(f"[red]Error:[/red] Budget must be positive, got {budget}")
                raise typer.Exit(code=1)
            cfg.token_budget = budget
        
        # Set verbose mode
        if verbose:
            logger.logger.setLevel("DEBUG")
        
        # Validate repo path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)
        
        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            raise typer.Exit(code=1)
        
        # Display start message
        console.print(Panel.fit(
            f"[bold cyan]Packing repository:[/bold cyan] {repo_path}\n"
            f"[bold cyan]Query:[/bold cyan] {query_text or 'None (using PageRank only)'}\n"
            f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
            f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
            border_style="cyan"
        ))
        
        # Step 1: Index (will auto-rebuild if stale)
        console.print("\n[bold]Step 1:[/bold] Checking indexes...")
        index_path = repo_path_obj / ".context-pack"
        
        if not index_path.exists() or not (index_path / "metadata.json").exists():
            console.print("  → Building indexes (first time)...")
            index_repository(repo_path=repo_path, config=cfg)
        else:
            console.print("  → Indexes found (will auto-rebuild if stale)")
        
        # Step 2: Query and pack
        console.print("\n[bold]Step 2:[/bold] Querying and packing...")
        output_path = query_and_pack(
            repo_path=repo_path,
            query=query_text,
            config=cfg
        )
        
        # Display success message
        console.print("\n[bold green]✓[/bold green] Packing complete!")
        console.print(f"Output saved to: {output_path}")
        
        raise typer.Exit(code=0)
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during packing:[/red] {e}")
        logger.log_error(e, {"command": "pack", "repo_path": repo_path})
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
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            raise typer.Exit(code=1)

        index_path = repo_path_obj / ".context-pack"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'context-pack index' first to build indexes")
            raise typer.Exit(code=1)

        if not (index_path / "metadata.json").exists():
            console.print(f"[red]Error:[/red] Incomplete index - metadata.json is missing")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'context-pack index' to rebuild indexes")
            raise typer.Exit(code=1)

        import json
        with open(index_path / "metadata.json", "r") as f:
            metadata = json.load(f)

        console.print(f"\n[bold]Index Status for:[/bold] {repo_path}")
        console.print(f"[bold]Index directory:[/bold] {index_path}")

        total_size = sum(f.stat().st_size for f in index_path.rglob("*") if f.is_file())
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

        console.print(f"\n[bold]Last indexed:[/bold] {metadata.get('indexed_at', 'unknown')}")

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error showing status:[/red] {e}")
        logger.log_error(e, {"command": "status", "repo_path": repo_path})
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

        index_path = repo_path_obj / ".context-pack"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'context-pack index' first to build indexes")
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

        index_path = repo_path_obj / ".context-pack"
        if not index_path.exists():
            console.print(f"[red]Error:[/red] No index found at {index_path}")
            console.print("\n[yellow]Suggestion:[/yellow] Run 'context-pack index' first to build indexes")
            raise typer.Exit(code=1)

        if not (index_path / "metadata.json").exists():
            console.print(f"[red]Error:[/red] Incomplete index - metadata.json is missing")
            raise typer.Exit(code=1)

        console.print("[bold]Rebuilding domain map database...[/bold]")

        from ..workflow.indexer import index_repository
        tracker = index_repository(
            repo_path=repo_path,
            config=_load_config(config, repo_path=repo_path),
            index_dir=".context-pack",
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
        raise typer.Exit(code=1)


def _load_config(config_path: Optional[str], repo_path: Optional[str] = None) -> Config:
    """
    Load configuration from file or use defaults.

    Args:
        config_path: Optional path to custom configuration file
        repo_path: Optional repository path to look for .context-pack.yaml

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
    
    # Try to load from repo_path/.context-pack.yaml if repo_path is provided
    if repo_path is not None:
        repo_config = Path(repo_path) / ".context-pack.yaml"
        if repo_config.exists():
            return Config.load(str(repo_config))
    
    # Try to load from default location, fall back to defaults
    return Config.load()


def main() -> None:
    """
    Main entry point for the CLI.
    
    This function is called when the user runs 'context-pack' command.
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
