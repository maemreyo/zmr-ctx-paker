import json
import shutil
import subprocess
from pathlib import Path

import pytest


def _run_emit_mcp_config(target: Path, force: bool) -> subprocess.CompletedProcess[str]:
    script_dir = Path(__file__).resolve().parents[2] / "src" / "ws_ctx_engine" / "scripts"
    force_value = "true" if force else "false"
    command = (
        "set -euo pipefail; "
        f'SCRIPT_DIR="{script_dir}"; '
        'source "$SCRIPT_DIR/lib/core.sh"; '
        'source "$SCRIPT_DIR/lib/mcp.sh"; '
        f'CTX_TARGET="{target}"; '
        f"CTX_FORCE={force_value}; "
        "emit_mcp_config"
    )
    return subprocess.run(["bash", "-c", command], capture_output=True, text=True)


@pytest.mark.skipif(
    shutil.which("envsubst") is None, reason="envsubst is required for init template rendering"
)
def test_emit_mcp_config_creates_default_file(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir(parents=True, exist_ok=True)

    result = _run_emit_mcp_config(target=target, force=False)
    assert result.returncode == 0, result.stderr

    config_path = target / ".ws-ctx-engine" / "mcp_config.json"
    assert config_path.exists()

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "workspace": str(target),
        "rate_limits": {
            "search_codebase": 60,
            "get_file_context": 120,
            "get_domain_map": 10,
            "get_index_status": 10,
        },
        "cache_ttl_seconds": 30,
    }


@pytest.mark.skipif(
    shutil.which("envsubst") is None, reason="envsubst is required for init template rendering"
)
def test_emit_mcp_config_does_not_overwrite_without_force(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    config_dir = target / ".ws-ctx-engine"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "mcp_config.json"
    original = '{"cache_ttl_seconds": 999}'
    config_path.write_text(original, encoding="utf-8")

    result = _run_emit_mcp_config(target=target, force=False)
    assert result.returncode == 0, result.stderr
    assert config_path.read_text(encoding="utf-8") == original


@pytest.mark.skipif(
    shutil.which("envsubst") is None, reason="envsubst is required for init template rendering"
)
def test_emit_mcp_config_overwrites_with_force(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    config_dir = target / ".ws-ctx-engine"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "mcp_config.json"
    config_path.write_text('{"cache_ttl_seconds": 999}', encoding="utf-8")

    result = _run_emit_mcp_config(target=target, force=True)
    assert result.returncode == 0, result.stderr

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["cache_ttl_seconds"] == 30
    assert payload["rate_limits"]["search_codebase"] == 60
