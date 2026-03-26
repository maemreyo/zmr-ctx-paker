from __future__ import annotations

from .mcp import run_mcp_server as _run_mcp_server


def run_mcp_server(
    workspace: str | None = None,
    config_path: str | None = None,
    rate_limit: dict[str, int] | None = None,
) -> None:
    _run_mcp_server(workspace=workspace, config_path=config_path, rate_limit=rate_limit)
