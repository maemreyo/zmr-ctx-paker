import json
import tempfile
from pathlib import Path

import pytest

from context_packer.mcp.config import DEFAULT_RATE_LIMITS, MCPConfig, MCPConfigValidationError


def test_mcp_config_loads_defaults_without_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MCPConfig.load(workspace=tmpdir)
        assert config.rate_limits == DEFAULT_RATE_LIMITS
        assert config.cache_ttl_seconds == 30
        assert config.workspace is None


def test_mcp_config_loads_file_values_and_applies_overrides() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        mcp_dir = workspace / ".context-pack"
        mcp_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = mcp_dir / "mcp_config.json"
        cfg_path.write_text(
            json.dumps(
                {
                    "workspace": "./repo",
                    "rate_limits": {
                        "search_codebase": 11,
                        "get_file_context": 22,
                        "get_domain_map": 33,
                        "get_index_status": 44,
                    },
                    "cache_ttl_seconds": 15,
                }
            ),
            encoding="utf-8",
        )

        config = MCPConfig.load(
            workspace=str(workspace),
            rate_limit_overrides={"search_codebase": 77, "get_domain_map": 99},
        )

        assert config.workspace == "./repo"
        assert config.rate_limits["search_codebase"] == 77
        assert config.rate_limits["get_file_context"] == 22
        assert config.rate_limits["get_domain_map"] == 99
        assert config.rate_limits["get_index_status"] == 44
        assert config.cache_ttl_seconds == 15


def test_mcp_config_ignores_invalid_values() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        mcp_dir = workspace / ".context-pack"
        mcp_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = mcp_dir / "mcp_config.json"
        cfg_path.write_text(
            """
{
  "workspace": "",
  "rate_limits": {
    "search_codebase": -1,
    "get_file_context": "x",
    "unknown_tool": 999
  },
  "cache_ttl_seconds": 0
}
""",
            encoding="utf-8",
        )

        config = MCPConfig.load(workspace=str(workspace))

        assert config.workspace is None
        assert config.rate_limits == DEFAULT_RATE_LIMITS
        assert config.cache_ttl_seconds == 30


def test_mcp_config_explicit_missing_file_raises() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        missing = workspace / "missing.json"

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(missing), strict=True)


def test_mcp_config_strict_mode_rejects_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text("{invalid json", encoding="utf-8")

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_mcp_config_strict_mode_rejects_invalid_shape() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text(
            json.dumps({"rate_limits": {"unknown_tool": 5}, "cache_ttl_seconds": 0}),
            encoding="utf-8",
        )

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_mcp_config_strict_mode_rejects_invalid_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text(json.dumps({"workspace": ""}), encoding="utf-8")

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_resolve_workspace_prefers_runtime_over_config() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        runtime = root / "runtime"
        runtime.mkdir(parents=True, exist_ok=True)

        config = MCPConfig(workspace="./from-config")
        resolved = config.resolve_workspace(runtime_workspace=str(runtime), bootstrap_workspace=str(root))
        assert resolved == str(runtime.resolve())


def test_resolve_workspace_uses_config_when_runtime_missing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "from-config").mkdir(parents=True, exist_ok=True)

        config = MCPConfig(workspace="./from-config")
        resolved = config.resolve_workspace(runtime_workspace=None, bootstrap_workspace=str(root))
        assert resolved == str((root / "from-config").resolve())


def test_resolve_workspace_falls_back_to_bootstrap_when_no_runtime_or_config() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config = MCPConfig(workspace=None)
        resolved = config.resolve_workspace(runtime_workspace=None, bootstrap_workspace=str(root))
        assert resolved == str(root.resolve())


def test_mcp_config_strict_mode_rejects_non_object_root_payload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text("[]", encoding="utf-8")

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_mcp_config_strict_mode_rejects_non_object_rate_limits() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text(json.dumps({"rate_limits": []}), encoding="utf-8")

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_mcp_config_strict_mode_rejects_non_positive_rate_limit_value() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text(json.dumps({"rate_limits": {"search_codebase": 0}}), encoding="utf-8")

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_mcp_config_strict_mode_rejects_invalid_cache_ttl_type() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text(json.dumps({"cache_ttl_seconds": "30"}), encoding="utf-8")

        with pytest.raises(MCPConfigValidationError):
            MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=True)


def test_mcp_config_non_strict_ignores_read_failures(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text("{}", encoding="utf-8")

        import builtins

        original_open = builtins.open

        def _raise_open(path, *args, **kwargs):
            if str(path) == str(cfg_path):
                raise OSError("cannot read")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _raise_open)

        cfg = MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=False)
        assert cfg.rate_limits == DEFAULT_RATE_LIMITS
        assert cfg.cache_ttl_seconds == 30


def test_mcp_config_non_strict_ignores_unknown_tool_and_invalid_limit() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text(
            json.dumps({"rate_limits": {"unknown": 10, "search_codebase": -1}}),
            encoding="utf-8",
        )

        cfg = MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=False)
        assert cfg.rate_limits == DEFAULT_RATE_LIMITS


def test_mcp_config_non_strict_ignores_non_object_root_payload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        cfg_path = workspace / "mcp_config.json"
        cfg_path.write_text("[]", encoding="utf-8")

        cfg = MCPConfig.load(workspace=str(workspace), config_path=str(cfg_path), strict=False)
        assert cfg.rate_limits == DEFAULT_RATE_LIMITS
        assert cfg.cache_ttl_seconds == 30


def test_resolve_workspace_uses_absolute_configured_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        abs_workspace = root / "absolute-workspace"
        abs_workspace.mkdir(parents=True, exist_ok=True)

        config = MCPConfig(workspace=str(abs_workspace))
        resolved = config.resolve_workspace(runtime_workspace=None, bootstrap_workspace=str(root))
        assert resolved == str(abs_workspace.resolve())


def test_resolve_workspace_ignores_blank_runtime_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        configured = root / "configured"
        configured.mkdir(parents=True, exist_ok=True)

        config = MCPConfig(workspace="./configured")
        resolved = config.resolve_workspace(runtime_workspace="   ", bootstrap_workspace=str(root))
        assert resolved == str(configured.resolve())
