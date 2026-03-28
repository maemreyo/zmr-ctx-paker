"""MCP server command."""

from pathlib import Path

import typer

from ...utils import _parse_rate_limits

app = typer.Typer()


@app.command("mcp")
def mcp(
    workspace: str | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help="Path to workspace root bound to MCP session (overrides mcp_config.workspace when set)",
    ),
    mcp_config: str | None = typer.Option(
        None,
        "--mcp-config",
        help="Path to MCP config JSON (defaults to .ws-ctx-engine/mcp_config.json)",
    ),
    rate_limit: list[str] = typer.Option(
        [],
        "--rate-limit",
        help="Override rate limit as TOOL=LIMIT, e.g. search_codebase=60",
    ),
) -> None:
    """Run ws-ctx-engine as an MCP stdio server bound to a single workspace."""
    from ...logger import logger
    from ...mcp_server import run_mcp_server
    from ...main import console

    try:
        if workspace is not None:
            workspace_path = Path(workspace)
            if not workspace_path.exists() or not workspace_path.is_dir():
                console.print(f"[red]Error:[/red] Invalid workspace path: {workspace}")
                raise typer.Exit(code=1)
            resolved_workspace: str | None = str(workspace_path.resolve())
        else:
            resolved_workspace = None

        try:
            parsed_limits = _parse_rate_limits(rate_limit)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        run_mcp_server(
            workspace=resolved_workspace,
            config_path=mcp_config,
            rate_limit=parsed_limits,
        )
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        raise typer.Exit(code=0) from None
    except Exception as e:
        console.print(f"[red]Error starting MCP server:[/red] {e}")
        logger.log_error(e, {"command": "mcp", "workspace": workspace})
        raise typer.Exit(code=1) from e
