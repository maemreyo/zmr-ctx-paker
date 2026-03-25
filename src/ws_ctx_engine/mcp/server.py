from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .config import MCPConfig
from .tools import MCPToolService


class MCPStdioServer:
    def __init__(self, workspace: Optional[str] = None, config_path: Optional[str] = None, rate_limit: Optional[dict[str, int]] = None) -> None:
        bootstrap_workspace = str(Path(workspace or ".").resolve())
        config = MCPConfig.load(
            workspace=bootstrap_workspace,
            config_path=config_path,
            rate_limit_overrides=rate_limit,
            strict=bool(config_path),
        )
        workspace_base = bootstrap_workspace
        if workspace is None and config_path:
            workspace_base = str(Path(config_path).resolve().parent)

        effective_workspace = config.resolve_workspace(runtime_workspace=workspace, bootstrap_workspace=workspace_base)
        effective_workspace_path = Path(effective_workspace)
        if not effective_workspace_path.exists() or not effective_workspace_path.is_dir():
            raise ValueError(f"Invalid workspace path: {effective_workspace}")
        self._service = MCPToolService(workspace=str(effective_workspace_path), config=config)

    def run(self) -> None:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            response = self._handle_request(request)
            if response is None:
                continue

            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    def _handle_request(self, request: dict[str, Any]) -> Optional[dict[str, Any]]:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params")
        if params is None:
            params = {}

        if not isinstance(method, str):
            return self._error_response(req_id, -32600, "Invalid request")
        if not isinstance(params, dict):
            return self._error_response(req_id, -32602, "Invalid params")

        if method in {"initialized", "notifications/initialized"}:
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "ws-ctx-engine",
                        "version": self._server_version(),
                    },
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self._service.tool_schemas()},
            }

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str):
                return self._error_response(req_id, -32602, "Missing tool name")
            if not isinstance(arguments, dict):
                return self._error_response(req_id, -32602, "Invalid tool arguments")

            payload = self._service.call_tool(name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                    "structuredContent": payload,
                },
            }

        return self._error_response(req_id, -32601, f"Method not found: {method}")

    @staticmethod
    def _error_response(req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }

    @staticmethod
    def _server_version() -> str:
        try:
            return importlib.metadata.version("ws-ctx-engine")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"


def run_mcp_server(workspace: Optional[str] = None, config_path: Optional[str] = None, rate_limit: Optional[dict[str, int]] = None) -> None:
    server = MCPStdioServer(workspace=workspace, config_path=config_path, rate_limit=rate_limit)
    server.run()
