"""Query command for searching and generating output."""

from pathlib import Path

import typer

from ..utils import (
    _copy_to_clipboard,
    _emit_ndjson,
    _enable_command_agent_mode,
    _load_config,
    _preflight_runtime_dependencies,
    _utc_now,
)

app = typer.Typer(name="query", help="Search indexes and generate output.")


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
    format: str | None = typer.Option(
        None,
        "--format",
        "-f",
        help="Output format: 'xml', 'zip', 'json', 'yaml', 'md', or 'toon' (experimental)",
    ),
    budget: int | None = typer.Option(
        None,
        "--budget",
        "-b",
        help="Token budget for context window",
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
    mode: str | None = typer.Option(
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
    from ...logger import logger
    from ...workflow import query_and_pack
    from ...main import console

    try:
        _enable_command_agent_mode(agent_mode)

        # Load configuration
        cfg = _load_config(config, repo_path=repo_path)

        # Override config with CLI flags
        if format is not None:
            if format not in ["xml", "zip", "json", "yaml", "md", "toon"]:
                console.print(
                    f"[red]Error:[/red] Invalid format '{format}'. Must be 'xml', 'zip', 'json', 'yaml', 'md', or 'toon'"
                )
                _emit_ndjson(
                    {
                        "type": "error",
                        "command": "query",
                        "error": "invalid_format",
                        "format": format,
                    }
                )
                raise typer.Exit(code=1)
            cfg.format = format

        if budget is not None:
            if budget <= 0:
                console.print(f"[red]Error:[/red] Budget must be positive, got {budget}")
                _emit_ndjson(
                    {
                        "type": "error",
                        "command": "query",
                        "error": "invalid_budget",
                        "budget": budget,
                    }
                )
                raise typer.Exit(code=1)
            cfg.token_budget = budget

        # Set verbose mode
        if verbose:
            logger.logger.setLevel("DEBUG")

        # Validate repo path
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
            _emit_ndjson(
                {"type": "error", "command": "query", "error": "repo_not_found", "repo": repo_path}
            )
            raise typer.Exit(code=1)

        if not repo_path_obj.is_dir():
            console.print(f"[red]Error:[/red] Repository path is not a directory: {repo_path}")
            _emit_ndjson(
                {
                    "type": "error",
                    "command": "query",
                    "error": "repo_not_directory",
                    "repo": repo_path,
                }
            )
            raise typer.Exit(code=1)

        cfg = _preflight_runtime_dependencies(cfg, "query")

        # Get AGENT_MODE from utils module
        from ..utils import AGENT_MODE

        _stdout_formats = {"json", "xml", "yaml", "md"}
        json_stdout_mode = cfg.format == "json" and not AGENT_MODE and not stdout

        # Validate mode flag
        if mode is not None and mode not in ("discovery", "edit", "test"):
            console.print(
                f"[red]Error:[/red] Invalid --mode '{mode}'. Must be 'discovery', 'edit', or 'test'"
            )
            raise typer.Exit(code=1)

        # Display start message
        if not AGENT_MODE and not json_stdout_mode and not stdout:
            console.print(
                Panel.fit(
                    f"[bold cyan]Querying:[/bold cyan] {query_text}\n"
                    f"[bold cyan]Repository:[/bold cyan] {repo_path}\n"
                    f"[bold cyan]Format:[/bold cyan] {cfg.format.upper()}\n"
                    f"[bold cyan]Budget:[/bold cyan] {cfg.token_budget:,} tokens",
                    border_style="cyan",
                )
            )

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
        output_content = None if is_binary_format else Path(output_path).read_text(encoding="utf-8")
        total_tokens = query_meta.get("total_tokens", 0) if isinstance(query_meta, dict) else 0

        # Display success message
        if stdout and output_content is not None:
            typer.echo(output_content)
        elif json_stdout_mode and output_content is not None:
            typer.echo(output_content)
        elif not AGENT_MODE:
            console.print("[bold green]✓[/bold green] Query complete!")
            if total_tokens:
                console.print(
                    f"[green]Context packed ({total_tokens:,} / {cfg.token_budget:,} tokens)[/green]"
                )
            console.print(f"Output saved to: {output_path}")

        if copy and output_content is not None:
            _copy_to_clipboard(output_content)

        _emit_ndjson(
            {
                "type": "status",
                "command": "query",
                "status": "success",
                "output_path": str(output_path),
                "total_tokens": total_tokens,
                "generated_at": _utc_now(),
            }
        )

        raise typer.Exit(code=0)

    except typer.Exit:
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print(
            "\n[yellow]Suggestion:[/yellow] Run 'ws-ctx-engine index' first to build indexes"
        )
        _emit_ndjson({"type": "error", "command": "query", "error": str(e)})
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Error during query:[/red] {e}")
        logger.log_error(e, {"command": "query", "repo_path": repo_path})
        _emit_ndjson({"type": "error", "command": "query", "error": str(e)})
        raise typer.Exit(code=1) from e
