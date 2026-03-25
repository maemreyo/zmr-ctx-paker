import pytest
from typer.testing import CliRunner

from ws_ctx_engine.cli.cli import _parse_rate_limits, app


runner = CliRunner()


def test_parse_rate_limits_accepts_valid_values() -> None:
    parsed = _parse_rate_limits(["search_codebase=10", "get_file_context=20"])
    assert parsed == {"search_codebase": 10, "get_file_context": 20}


@pytest.mark.parametrize(
    "raw",
    [
        "bad-format",
        "unknown_tool=10",
        "search_codebase=abc",
        "get_domain_map=0",
    ],
)
def test_parse_rate_limits_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError):
        _parse_rate_limits([raw])


def test_mcp_command_rejects_invalid_workspace() -> None:
    result = runner.invoke(app, ["mcp", "--workspace", "/path/does/not/exist"])
    assert result.exit_code == 1
    assert "Invalid workspace path" in result.stdout


def test_mcp_command_rejects_missing_explicit_mcp_config() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["mcp", "--workspace", ".", "--mcp-config", "./missing-mcp-config.json"])
        assert result.exit_code == 1
        assert "MCP config file not found" in result.stdout


def test_mcp_command_allows_workspace_to_be_omitted(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_mcp_server(workspace, config_path, rate_limit) -> None:
        captured["workspace"] = workspace
        captured["config_path"] = config_path
        captured["rate_limit"] = rate_limit

    monkeypatch.setattr("ws_ctx_engine.cli.cli.run_mcp_server", _fake_run_mcp_server)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["mcp", "--rate-limit", "search_codebase=42"])

    assert result.exit_code == 0
    assert captured["workspace"] is None
    assert captured["config_path"] is None
    assert captured["rate_limit"] == {"search_codebase": 42}
