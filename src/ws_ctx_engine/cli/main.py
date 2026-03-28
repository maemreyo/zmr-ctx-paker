"""
Main entry point for ws-ctx-engine CLI.

Provides Typer app initialization and command registration.
"""

import importlib.metadata
import logging

import typer
from rich.console import Console

from ..logger import get_logger
from .commands import config, doctor, graph, index, maintenance, pack, query, search, server, session, status

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


def _set_console_log_level(level: int) -> None:
    """Set logging level for the console."""
    logger.logger.setLevel(level)


def _set_agent_mode(enabled: bool) -> None:
    """Enable or disable agent mode."""
    global AGENT_MODE, console
    AGENT_MODE = enabled
    console = Console(stderr=enabled)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        try:
            version = importlib.metadata.version("ws-ctx-engine")
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
        console.print(f"ws-ctx-engine version: [bold cyan]{version}[/bold cyan]")
        raise typer.Exit()


@app.callback()
def _cli_callback(
    version: bool | None = typer.Option(
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
    quiet: bool = typer.Option(
        True,
        "--quiet/--no-quiet",
        help="Suppress informational logs in terminal; only warnings/errors are shown.",
    ),
) -> None:
    """
    Intelligently package codebases into optimized context for Large Language Models.
    """
    _set_agent_mode(agent_mode)
    if quiet:
        _set_console_log_level(logging.WARNING)


# Register commands
app.add_typer(doctor.app)
app.add_typer(index.app)
app.add_typer(search.app)
app.add_typer(query.app)
app.add_typer(pack.app)
app.add_typer(status.app)
app.add_typer(maintenance.app)
app.add_typer(config.app)
app.add_typer(server.app)
app.add_typer(session.app)
app.add_typer(graph.app)


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
        import sys

        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        import sys

        sys.exit(1)


if __name__ == "__main__":
    main()
