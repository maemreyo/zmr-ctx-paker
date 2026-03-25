import io
import tempfile
from pathlib import Path

import pytest

from context_packer.mcp.server import MCPStdioServer
from context_packer.mcp_server import run_mcp_server as run_mcp_server_wrapper


def test_initialize_response_shape() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)
        response = server._handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["capabilities"] == {"tools": {}}
        assert response["result"]["serverInfo"]["name"] == "ctx-packer"


def test_initialized_notifications_return_none() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)
        assert server._handle_request({"method": "initialized", "params": {}}) is None
        assert server._handle_request({"method": "notifications/initialized", "params": {}}) is None


def test_tools_list_uses_service_schemas(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)
        monkeypatch.setattr(server._service, "tool_schemas", lambda: [{"name": "search_codebase"}])

        response = server._handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

        assert response is not None
        assert response["result"]["tools"] == [{"name": "search_codebase"}]


def test_tools_call_returns_structured_content(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)
        monkeypatch.setattr(server._service, "call_tool", lambda name, args: {"ok": True, "tool": name, "args": args})

        response = server._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "search_codebase", "arguments": {"query": "auth"}},
            }
        )

        assert response is not None
        payload = response["result"]["structuredContent"]
        assert payload["ok"] is True
        assert payload["tool"] == "search_codebase"
        assert payload["args"] == {"query": "auth"}


def test_invalid_method_and_params_return_errors() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)

        bad_method = server._handle_request({"jsonrpc": "2.0", "id": 4, "method": 123, "params": {}})
        assert bad_method is not None
        assert bad_method["error"]["code"] == -32600

        bad_params = server._handle_request({"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": []})
        assert bad_params is not None
        assert bad_params["error"]["code"] == -32602

        not_found = server._handle_request({"jsonrpc": "2.0", "id": 6, "method": "unknown", "params": {}})
        assert not_found is not None
        assert not_found["error"]["code"] == -32601


def test_server_rejects_explicit_invalid_config_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / "missing-config.json"
        with pytest.raises(ValueError):
            MCPStdioServer(workspace=tmpdir, config_path=str(bad_path))


def test_server_uses_workspace_from_config_when_runtime_missing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        configured_ws = root / "configured-workspace"
        configured_ws.mkdir(parents=True, exist_ok=True)

        cfg_path = root / "mcp-config.json"
        cfg_path.write_text('{"workspace":"./configured-workspace"}', encoding="utf-8")

        server = MCPStdioServer(workspace=None, config_path=str(cfg_path))
        assert server._service.workspace_root == configured_ws.resolve()


def test_server_runtime_workspace_takes_precedence_over_config_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        configured_ws = root / "configured-workspace"
        runtime_ws = root / "runtime-workspace"
        configured_ws.mkdir(parents=True, exist_ok=True)
        runtime_ws.mkdir(parents=True, exist_ok=True)

        cfg_path = root / "mcp-config.json"
        cfg_path.write_text('{"workspace":"./configured-workspace"}', encoding="utf-8")

        server = MCPStdioServer(workspace=str(runtime_ws), config_path=str(cfg_path))
        assert server._service.workspace_root == runtime_ws.resolve()


def test_server_rejects_config_workspace_that_is_not_directory() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        cfg_path = root / "mcp-config.json"
        cfg_path.write_text('{"workspace":"./missing-workspace"}', encoding="utf-8")

        with pytest.raises(ValueError):
            MCPStdioServer(workspace=None, config_path=str(cfg_path))


def test_tools_call_rejects_missing_name_and_invalid_arguments_shape() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)

        missing_name = server._handle_request(
            {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"arguments": {}}}
        )
        assert missing_name is not None
        assert missing_name["error"]["code"] == -32602

        invalid_args = server._handle_request(
            {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "search_codebase", "arguments": []}}
        )
        assert invalid_args is not None
        assert invalid_args["error"]["code"] == -32602


def test_run_loop_ignores_bad_json_and_writes_valid_response(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)

        fake_stdin = io.StringIO("\nnot-json\n{\"id\": 1, \"method\": \"initialize\", \"params\": {}}\n")
        fake_stdout = io.StringIO()

        monkeypatch.setattr("sys.stdin", fake_stdin)
        monkeypatch.setattr("sys.stdout", fake_stdout)

        server.run()

        lines = [line for line in fake_stdout.getvalue().splitlines() if line.strip()]
        assert len(lines) == 1
        assert '"id": 1' in lines[0]
        assert '"jsonrpc": "2.0"' in lines[0]


def test_server_version_falls_back_to_unknown_when_package_missing(monkeypatch) -> None:
    import importlib.metadata

    def _raise_not_found(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", _raise_not_found)
    assert MCPStdioServer._server_version() == "unknown"


def test_mcp_server_wrapper_forwards_arguments(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_mcp_server(workspace=None, config_path=None, rate_limit=None):
        captured["workspace"] = workspace
        captured["config_path"] = config_path
        captured["rate_limit"] = rate_limit

    monkeypatch.setattr("context_packer.mcp_server._run_mcp_server", _fake_run_mcp_server)

    run_mcp_server_wrapper(workspace="/tmp/work", config_path="/tmp/cfg.json", rate_limit={"search_codebase": 10})

    assert captured == {
        "workspace": "/tmp/work",
        "config_path": "/tmp/cfg.json",
        "rate_limit": {"search_codebase": 10},
    }


def test_handle_request_accepts_none_params_for_tools_list() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)
        response = server._handle_request({"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": None})

    assert response is not None
    assert response["result"]["tools"]


def test_run_loop_skips_notification_with_no_response(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)

        fake_stdin = io.StringIO("{\"id\": 1, \"method\": \"initialized\", \"params\": {}}\n")
        fake_stdout = io.StringIO()

        monkeypatch.setattr("sys.stdin", fake_stdin)
        monkeypatch.setattr("sys.stdout", fake_stdout)

        server.run()

        assert fake_stdout.getvalue().strip() == ""


def test_run_mcp_server_constructs_server_and_calls_run(monkeypatch) -> None:
    from context_packer.mcp import server as server_module

    called = {"run": 0}

    class _FakeServer:
        def __init__(self, workspace=None, config_path=None, rate_limit=None):
            self.workspace = workspace
            self.config_path = config_path
            self.rate_limit = rate_limit

        def run(self):
            called["run"] += 1

    monkeypatch.setattr(server_module, "MCPStdioServer", _FakeServer)

    server_module.run_mcp_server(workspace="/tmp/ws", config_path="/tmp/cfg", rate_limit={"search_codebase": 1})

    assert called["run"] == 1


def test_tools_call_uses_default_empty_arguments_when_not_provided(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        server = MCPStdioServer(workspace=tmpdir)
        monkeypatch.setattr(server._service, "call_tool", lambda name, args: {"name": name, "args": args})

        response = server._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {"name": "search_codebase"},
            }
        )

    assert response is not None
    assert response["result"]["structuredContent"] == {"name": "search_codebase", "args": {}}


def test_error_response_helper_shape() -> None:
    payload = MCPStdioServer._error_response(req_id="abc", code=-32001, message="boom")
    assert payload == {
        "jsonrpc": "2.0",
        "id": "abc",
        "error": {"code": -32001, "message": "boom"},
    }


def test_server_version_returns_installed_package_version(monkeypatch) -> None:
    monkeypatch.setattr("importlib.metadata.version", lambda _: "9.9.9")
    assert MCPStdioServer._server_version() == "9.9.9"
