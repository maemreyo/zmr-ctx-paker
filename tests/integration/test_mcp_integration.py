"""Integration tests for MCP tool workflows on real indexes."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ws_ctx_engine.config import Config
from ws_ctx_engine.mcp.config import MCPConfig
from ws_ctx_engine.mcp.server import MCPStdioServer
from ws_ctx_engine.mcp.tools import MCPToolService
from ws_ctx_engine.workflow import index_repository

FAISS_AVAILABLE = importlib.util.find_spec("faiss") is not None
NETWORKX_AVAILABLE = importlib.util.find_spec("networkx") is not None


pytestmark = pytest.mark.skipif(
    not (FAISS_AVAILABLE and NETWORKX_AVAILABLE),
    reason="MCP integration tests require faiss-cpu and networkx",
)


@pytest.fixture(autouse=True)
def fake_sentence_transformers_module():
    fake_st = types.ModuleType("sentence_transformers")

    class _FakeSentenceTransformer:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def encode(self, inputs, *args, **kwargs):
            count = 1 if isinstance(inputs, str) else len(inputs)
            return np.array([[0.1] * 384 for _ in range(count)], dtype=np.float32)

    fake_st.SentenceTransformer = _FakeSentenceTransformer

    with patch.dict(sys.modules, {"sentence_transformers": fake_st}):
        yield


@pytest.fixture
def mcp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)

    (src / "auth.py").write_text(
        """
def authenticate(username: str, password: str) -> bool:
    return username == \"admin\" and password == \"password\"
""",
        encoding="utf-8",
    )

    (src / "service.py").write_text(
        """
from src.auth import authenticate


def login_flow(user: str, pwd: str) -> bool:
    return authenticate(user, pwd)
""",
        encoding="utf-8",
    )

    (src / "secret_config.py").write_text(
        'API_KEY = "sk-live-secret-very-long-token"\n',
        encoding="utf-8",
    )

    return repo


@pytest.fixture
def mcp_indexed_repo(mcp_repo: Path) -> Path:
    cfg = Config()
    cfg.backends["vector_index"] = "faiss"
    cfg.backends["graph"] = "networkx"
    cfg.backends["embeddings"] = "local"

    index_repository(repo_path=str(mcp_repo), config=cfg)

    return mcp_repo


def test_mcp_tools_end_to_end_on_real_index(mcp_indexed_repo: Path) -> None:
    service = MCPToolService(workspace=str(mcp_indexed_repo), config=MCPConfig())

    search_payload = service.call_tool(
        "search_codebase",
        {"query": "authentication login", "limit": 5},
    )
    assert "error" not in search_payload
    assert isinstance(search_payload["results"], list)
    assert len(search_payload["results"]) > 0
    assert "index_health" in search_payload

    domain_payload = service.call_tool("get_domain_map", {})
    assert "error" not in domain_payload
    assert "domains" in domain_payload
    assert "graph_stats" in domain_payload
    assert "index_health" in domain_payload

    status_payload = service.call_tool("get_index_status", {})
    assert "error" not in status_payload
    assert "index_health" in status_payload
    assert "workspace" in status_payload

    safe_file_payload = service.call_tool("get_file_context", {"path": "src/auth.py"})
    assert safe_file_payload["sanitized"] is True
    assert safe_file_payload["content"].startswith(safe_file_payload["content_start_marker"])
    assert safe_file_payload["content"].endswith(safe_file_payload["content_end_marker"])
    assert "index_health" in safe_file_payload

    secret_file_payload = service.call_tool("get_file_context", {"path": "src/secret_config.py"})
    assert secret_file_payload["sanitized"] is False
    assert secret_file_payload["content"] is None
    assert len(secret_file_payload["secrets_detected"]) >= 1
    assert "index_health" in secret_file_payload


def test_mcp_server_tools_call_integration(mcp_indexed_repo: Path) -> None:
    server = MCPStdioServer(workspace=str(mcp_indexed_repo))

    response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "search_codebase",
                "arguments": {"query": "authenticate", "limit": 3},
            },
        }
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert "results" in structured
    assert "index_health" in structured
    assert isinstance(structured["results"], list)


def test_mcp_server_uses_workspace_from_config_when_runtime_missing(mcp_indexed_repo: Path, tmp_path: Path) -> None:
    cfg_path = tmp_path / "mcp-config.json"
    cfg_path.write_text(
        '{"workspace": "%s"}' % str(mcp_indexed_repo),
        encoding="utf-8",
    )

    server = MCPStdioServer(workspace=None, config_path=str(cfg_path))
    response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {
                "name": "search_codebase",
                "arguments": {"query": "authenticate", "limit": 3},
            },
        }
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert "error" not in structured
    assert isinstance(structured["results"], list)
    assert len(structured["results"]) > 0


def test_mcp_server_runtime_workspace_precedence_over_config(mcp_indexed_repo: Path, tmp_path: Path) -> None:
    empty_workspace = tmp_path / "empty-workspace"
    empty_workspace.mkdir(parents=True, exist_ok=True)

    cfg_path = tmp_path / "mcp-config.json"
    cfg_path.write_text(
        '{"workspace": "%s"}' % str(mcp_indexed_repo),
        encoding="utf-8",
    )

    server = MCPStdioServer(workspace=str(empty_workspace), config_path=str(cfg_path))
    response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "tools/call",
            "params": {
                "name": "search_codebase",
                "arguments": {"query": "authenticate", "limit": 3},
            },
        }
    )

    assert response is not None
    structured = response["result"]["structuredContent"]
    assert structured["error"] == "INDEX_NOT_FOUND"
