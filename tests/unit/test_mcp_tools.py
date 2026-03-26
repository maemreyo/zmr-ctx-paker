import tempfile
from pathlib import Path

from ws_ctx_engine.mcp.config import MCPConfig
from ws_ctx_engine.mcp.security.path_guard import WorkspacePathGuard
from ws_ctx_engine.mcp.tools import MCPToolService


def test_workspace_path_guard_blocks_path_traversal() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = WorkspacePathGuard(tmpdir)

        inside = guard.resolve_relative("src/app.py")
        assert str(inside).startswith(str(Path(tmpdir).resolve()))

        try:
            guard.resolve_relative("../../etc/passwd")
            raise AssertionError("Expected traversal to be blocked")
        except PermissionError as exc:
            assert "ACCESS_DENIED" in str(exc)


def test_workspace_path_guard_blocks_absolute_outside_workspace() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        guard = WorkspacePathGuard(tmpdir)
        outside = Path("/") / "tmp" / "outside.txt"

        try:
            guard.resolve_relative(str(outside))
            raise AssertionError("Expected absolute outside path to be blocked")
        except PermissionError as exc:
            assert "ACCESS_DENIED" in str(exc)


def test_get_file_context_blocks_symlink_escape_path() -> None:
    with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as outside_dir:
        repo = Path(repo_dir)
        outside = Path(outside_dir) / "outside_mcp_service.txt"
        outside.write_text("secret\n", encoding="utf-8")

        link = repo / "leak.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError, PermissionError):
            return

        service = MCPToolService(workspace=str(repo), config=MCPConfig())
        payload = service.call_tool("get_file_context", {"path": "leak.txt"})

        assert payload["content"] is None
        assert payload["sanitized"] is False
        assert "ACCESS_DENIED" in payload["error"]


def test_get_file_context_redacts_secrets_and_writes_cache() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        src_dir = repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        target = src_dir / "auth.py"
        target.write_text('API_KEY = "sk-live-secret-12345"\n', encoding="utf-8")

        service = MCPToolService(workspace=str(repo), config=MCPConfig())
        payload = service.call_tool("get_file_context", {"path": "src/auth.py"})

        assert payload["path"] == "src/auth.py"
        assert payload["content"] is None
        assert payload["sanitized"] is False
        assert len(payload["secrets_detected"]) >= 1
        assert "index_health" in payload

        cache_path = repo / ".ws-ctx-engine" / "secret_scan_cache.json"
        assert cache_path.exists()


def test_get_file_context_wraps_safe_content_with_rade_markers() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        src_dir = repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        target = src_dir / "safe.py"
        target.write_text("def ok() -> int:\n    return 1\n", encoding="utf-8")

        service = MCPToolService(workspace=str(repo), config=MCPConfig())
        payload = service.call_tool("get_file_context", {"path": "src/safe.py"})

        assert payload["sanitized"] is True
        assert payload["secrets_detected"] == []
        assert payload["content_start_marker"].startswith("CTX_")
        assert payload["content_end_marker"].startswith("CTX_")
        assert payload["content"].startswith(payload["content_start_marker"])
        assert payload["content"].endswith(payload["content_end_marker"])
        assert "index_health" in payload


def test_get_file_context_validates_boolean_flags() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        src_dir = repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "safe.py").write_text("x = 1\n", encoding="utf-8")

        service = MCPToolService(workspace=str(repo), config=MCPConfig())

        bad_deps = service.call_tool(
            "get_file_context",
            {"path": "src/safe.py", "include_dependencies": "false"},
        )
        assert bad_deps["error"] == "INVALID_ARGUMENT"

        bad_dependents = service.call_tool(
            "get_file_context",
            {"path": "src/safe.py", "include_dependents": 1},
        )
        assert bad_dependents["error"] == "INVALID_ARGUMENT"


def test_get_file_context_obeys_rate_limit() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        src_dir = repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "safe.py").write_text("def ok() -> int:\n    return 1\n", encoding="utf-8")

        config = MCPConfig(
            rate_limits={
                "search_codebase": 60,
                "get_file_context": 1,
                "get_domain_map": 10,
                "get_index_status": 10,
            }
        )
        service = MCPToolService(workspace=str(repo), config=config)

        first = service.call_tool("get_file_context", {"path": "src/safe.py"})
        assert first.get("error") is None

        second = service.call_tool("get_file_context", {"path": "src/safe.py"})
        assert second.get("error") == "RATE_LIMIT_EXCEEDED"


def test_get_domain_map_cache_bypasses_rate_limit_until_expired() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MCPConfig(
            rate_limits={
                "search_codebase": 60,
                "get_file_context": 120,
                "get_domain_map": 1,
                "get_index_status": 10,
            }
        )
        service = MCPToolService(workspace=tmpdir, config=config)

        calls = {"count": 0}

        def fake_domain_map() -> dict[str, object]:
            calls["count"] += 1
            return {"domains": [], "graph_stats": {}, "index_health": {"status": "unknown"}}

        service._get_domain_map = fake_domain_map  # type: ignore[method-assign]

        first = service.call_tool("get_domain_map", {})
        assert "error" not in first
        assert calls["count"] == 1

        second = service.call_tool("get_domain_map", {})
        assert "error" not in second
        assert calls["count"] == 1

        service._cache["tool:get_domain_map"].expires_at = 0
        third = service.call_tool("get_domain_map", {})
        assert third["error"] == "RATE_LIMIT_EXCEEDED"
        assert calls["count"] == 1


def test_get_index_status_error_is_not_cached() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MCPConfig(
            rate_limits={
                "search_codebase": 60,
                "get_file_context": 120,
                "get_domain_map": 10,
                "get_index_status": 1,
            }
        )
        service = MCPToolService(workspace=tmpdir, config=config)

        service._get_index_status = lambda: {"error": "INDEX_NOT_FOUND", "message": "missing"}  # type: ignore[method-assign]

        first = service.call_tool("get_index_status", {})
        assert first["error"] == "INDEX_NOT_FOUND"

        second = service.call_tool("get_index_status", {})
        assert second["error"] == "RATE_LIMIT_EXCEEDED"


def test_tool_registry_exposes_expected_tools() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=MCPConfig())
        names = {tool["name"] for tool in service.tool_schemas()}
        assert names == {
            "search_codebase",
            "get_file_context",
            "get_domain_map",
            "get_index_status",
        }


def test_call_tool_rejects_unknown_tool() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=MCPConfig())
        payload = service.call_tool("write_file", {})
        assert payload["error"] == "TOOL_NOT_FOUND"


def test_search_codebase_validates_arguments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=MCPConfig())

        missing_query = service.call_tool("search_codebase", {})
        assert missing_query["error"] == "INVALID_ARGUMENT"

        bad_limit = service.call_tool("search_codebase", {"query": "auth", "limit": 0})
        assert bad_limit["error"] == "INVALID_ARGUMENT"

        bad_domain = service.call_tool("search_codebase", {"query": "auth", "domain_filter": 123})
        assert bad_domain["error"] == "INVALID_ARGUMENT"


def test_search_codebase_returns_search_failed_when_backend_raises(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=MCPConfig())

        def _boom(**kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr("ws_ctx_engine.mcp.tools.search_codebase", _boom)
        payload = service.call_tool("search_codebase", {"query": "auth"})
        assert payload["error"] == "SEARCH_FAILED"


def test_get_file_context_returns_invalid_argument_when_path_missing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=MCPConfig())
        payload = service.call_tool("get_file_context", {})
        assert payload["error"] == "INVALID_ARGUMENT"


def test_get_file_context_returns_file_not_found_for_missing_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=MCPConfig())
        payload = service.call_tool("get_file_context", {"path": "src/missing.py"})
        assert payload["error"] == "FILE_NOT_FOUND"


def test_get_file_context_returns_file_read_failed_when_read_errors(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        src_dir = repo / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        target = src_dir / "safe.py"
        target.write_text("def ok():\n    return 1\n", encoding="utf-8")

        service = MCPToolService(workspace=str(repo), config=MCPConfig())

        def _raise_read_text(self: Path, encoding: str = "utf-8", errors: str = "ignore"):
            raise OSError("read failure")

        monkeypatch.setattr(Path, "read_text", _raise_read_text)

        payload = service.call_tool("get_file_context", {"path": "src/safe.py"})
        assert payload["error"].startswith("FILE_READ_FAILED")


def test_load_metadata_returns_none_for_invalid_created_at() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        index_dir = repo / ".ws-ctx-engine"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "metadata.json").write_text(
            '{"created_at": 123, "repo_path": ".", "file_count": 1, "backend": "faiss", "file_hashes": {}}',
            encoding="utf-8",
        )

        service = MCPToolService(workspace=str(repo), config=MCPConfig())
        assert service._load_metadata() is None
