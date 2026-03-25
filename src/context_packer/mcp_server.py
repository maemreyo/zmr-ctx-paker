from __future__ import annotations

from typing import Optional

from .mcp import run_mcp_server as _run_mcp_server


def run_mcp_server(workspace: Optional[str] = None, config_path: Optional[str] = None, rate_limit: Optional[dict[str, int]] = None) -> None:
    _run_mcp_server(workspace=workspace, config_path=config_path, rate_limit=rate_limit)
