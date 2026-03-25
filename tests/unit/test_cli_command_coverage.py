from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from ws_ctx_engine.cli.cli import _load_config, app


runner = CliRunner()


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(format="xml", token_budget=1000)


def test_index_command_repo_not_found() -> None:
    result = runner.invoke(app, ["index", "/definitely/missing"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_index_command_repo_not_directory() -> None:
    with runner.isolated_filesystem():
        file_path = Path("file.txt")
        file_path.write_text("x", encoding="utf-8")
        result = runner.invoke(app, ["index", str(file_path)])
        assert result.exit_code == 1
        assert "not a directory" in result.stdout


def test_search_command_repo_not_found() -> None:
    result = runner.invoke(app, ["search", "auth", "--repo", "/definitely/missing"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_search_command_repo_not_directory() -> None:
    with runner.isolated_filesystem():
        file_path = Path("repo.txt")
        file_path.write_text("x", encoding="utf-8")
        result = runner.invoke(app, ["search", "auth", "--repo", str(file_path)])
        assert result.exit_code == 1
        assert "not a directory" in result.stdout


def test_search_command_agent_mode_outputs_ndjson(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())
    monkeypatch.setattr(
        "ws_ctx_engine.cli.cli.search_codebase",
        lambda **kwargs: (
            [{"path": "src/a.py", "score": 0.9, "domain": "auth", "summary": "ok"}],
            {"index_built_at": "2026-01-01T00:00:00Z", "files_indexed": 1},
        ),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["--agent-mode", "search", "auth", "--repo", "."])

    assert result.exit_code == 0
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) >= 2
    assert '"type": "meta"' in lines[0]
    assert '"type": "result"' in lines[1]


def test_search_command_handles_filenotfound(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    def _raise_not_found(**kwargs):
        raise FileNotFoundError("index missing")

    monkeypatch.setattr("ws_ctx_engine.cli.cli.search_codebase", _raise_not_found)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["search", "auth", "--repo", "."])

    assert result.exit_code == 1
    assert "index missing" in result.stdout


def test_search_command_handles_generic_error(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    def _raise_error(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("ws_ctx_engine.cli.cli.search_codebase", _raise_error)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["search", "auth", "--repo", "."])

    assert result.exit_code == 1
    assert "Error during search" in result.stdout


def test_query_command_rejects_invalid_format(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["query", "auth", "--repo", ".", "--format", "txt"])

    assert result.exit_code == 1
    assert "Invalid format" in result.stdout


def test_query_command_rejects_non_positive_budget(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["query", "auth", "--repo", ".", "--budget", "0"])

    assert result.exit_code == 1
    assert "Budget must be positive" in result.stdout


def test_query_command_success_path(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())
    monkeypatch.setattr("ws_ctx_engine.cli.cli.query_and_pack", lambda **kwargs: (Path("output.xml"), {}))

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["query", "auth", "--repo", "."])

    assert result.exit_code == 0
    assert "Query complete" in result.stdout


def test_pack_command_rejects_invalid_format(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pack", ".", "--format", "txt"])

    assert result.exit_code == 1
    assert "Invalid format" in result.stdout


def test_pack_command_rejects_non_positive_budget(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pack", ".", "--budget", "0"])

    assert result.exit_code == 1
    assert "Budget must be positive" in result.stdout


def test_pack_command_success_path_calls_index_and_query(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    called = {"index": 0, "query": 0}

    def _fake_index_repository(**kwargs):
        called["index"] += 1

    def _fake_query_and_pack(**kwargs):
        called["query"] += 1
        return Path("ws-ctx-engine.zip"), {}

    monkeypatch.setattr("ws_ctx_engine.cli.cli.index_repository", _fake_index_repository)
    monkeypatch.setattr("ws_ctx_engine.cli.cli.query_and_pack", _fake_query_and_pack)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pack", ".", "--query", "auth"])

    assert result.exit_code == 0
    assert called["index"] == 1
    assert called["query"] == 1


def test_load_config_missing_explicit_file_exits() -> None:
    with runner.isolated_filesystem():
        with pytest.raises(typer.Exit) as exc_info:
            _load_config("./missing.yaml")

    assert exc_info.value.exit_code == 1


def test_load_config_prefers_repo_local_config(monkeypatch) -> None:
    loaded: dict[str, str | None] = {"path": None}

    def _fake_load(path=None):
        loaded["path"] = path
        return _cfg()

    monkeypatch.setattr("ws_ctx_engine.cli.cli.Config.load", _fake_load)

    with runner.isolated_filesystem():
        Path(".ws-ctx-engine.yaml").write_text("format: xml\n", encoding="utf-8")
        cfg = _load_config(None, repo_path=".")

    assert cfg.format == "xml"
    assert loaded["path"] == str(Path(".") / ".ws-ctx-engine.yaml")


def test_version_flag_falls_back_to_unknown(monkeypatch) -> None:
    import importlib.metadata

    def _raise_not_found(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr("importlib.metadata.version", _raise_not_found)
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "unknown" in result.stdout


def test_index_command_success_path(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())
    called = {"count": 0}

    def _fake_index_repository(**kwargs):
        called["count"] += 1

    monkeypatch.setattr("ws_ctx_engine.cli.cli.index_repository", _fake_index_repository)

    with runner.isolated_filesystem():
        Path("repo").mkdir()
        result = runner.invoke(app, ["index", "repo", "--verbose"])

    assert result.exit_code == 0
    assert called["count"] == 1


def test_index_command_handles_generic_error(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    def _raise_index_error(**kwargs):
        raise RuntimeError("index failed")

    monkeypatch.setattr("ws_ctx_engine.cli.cli.index_repository", _raise_index_error)

    with runner.isolated_filesystem():
        Path("repo").mkdir()
        result = runner.invoke(app, ["index", "repo"])

    assert result.exit_code == 1
    assert "Error during indexing" in result.stdout


def test_search_command_non_agent_mode_no_results(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())
    monkeypatch.setattr(
        "ws_ctx_engine.cli.cli.search_codebase",
        lambda **kwargs: ([], {"index_built_at": "2026-01-01T00:00:00Z", "files_indexed": 0}),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["search", "auth", "--repo", ".", "--verbose"])

    assert result.exit_code == 0
    assert "No matching files found" in result.stdout


def test_mcp_command_invalid_rate_limit_exits() -> None:
    result = runner.invoke(app, ["mcp", "--rate-limit", "bad"])
    assert result.exit_code == 1
    assert "Invalid --rate-limit" in result.stdout


def test_mcp_command_keyboard_interrupt_exits_zero(monkeypatch) -> None:
    def _raise_interrupt(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("ws_ctx_engine.cli.cli.run_mcp_server", _raise_interrupt)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["mcp"])

    assert result.exit_code == 0


def test_query_command_handles_file_not_found(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    def _raise_not_found(**kwargs):
        raise FileNotFoundError("missing index")

    monkeypatch.setattr("ws_ctx_engine.cli.cli.query_and_pack", _raise_not_found)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["query", "auth", "--repo", ".", "--format", "md", "--budget", "100"])

    assert result.exit_code == 1
    assert "missing index" in result.stdout


def test_query_command_handles_generic_error(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    def _raise_error(**kwargs):
        raise RuntimeError("query boom")

    monkeypatch.setattr("ws_ctx_engine.cli.cli.query_and_pack", _raise_error)

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["query", "auth", "--repo", "."])

    assert result.exit_code == 1
    assert "Error during query" in result.stdout


def test_pack_command_handles_generic_error(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    def _raise_error(**kwargs):
        raise RuntimeError("pack boom")

    monkeypatch.setattr("ws_ctx_engine.cli.cli.query_and_pack", _raise_error)

    with runner.isolated_filesystem():
        Path("repo").mkdir()
        Path("repo/.ws-ctx-engine").mkdir(parents=True, exist_ok=True)
        Path("repo/.ws-ctx-engine/metadata.json").write_text("{}", encoding="utf-8")
        result = runner.invoke(app, ["pack", "repo", "--query", "auth"])

    assert result.exit_code == 1
    assert "Error during packing" in result.stdout


def test_status_command_success_path(monkeypatch) -> None:
    class _FakeDB:
        def __init__(self, path: str):
            self.path = path

        def stats(self):
            return {"keywords": 2, "directories": 1}

        def close(self):
            return None

    monkeypatch.setattr("ws_ctx_engine.domain_map.DomainMapDB", _FakeDB)

    with runner.isolated_filesystem():
        repo = Path("repo")
        index_dir = repo / ".ws-ctx-engine"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "metadata.json").write_text('{"file_count": 3, "backend": "faiss"}', encoding="utf-8")
        (index_dir / "vector.idx").write_bytes(b"x")
        (index_dir / "graph.pkl").write_bytes(b"x")
        (index_dir / "domain_map.db").write_bytes(b"x")

        result = runner.invoke(app, ["status", "repo"])

    assert result.exit_code == 0
    assert "Index Status" in result.stdout


def test_status_command_handles_unexpected_error() -> None:
    with runner.isolated_filesystem():
        repo = Path("repo")
        index_dir = repo / ".ws-ctx-engine"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "metadata.json").write_text("{invalid json", encoding="utf-8")

        result = runner.invoke(app, ["status", "repo"])

    assert result.exit_code == 1
    assert "Error showing status" in result.stdout


def test_vacuum_command_success_path(monkeypatch) -> None:
    calls = {"vacuum": 0, "close": 0}

    class _FakeConn:
        def execute(self, sql: str) -> None:
            if sql == "VACUUM":
                calls["vacuum"] += 1

    class _FakeDB:
        def __init__(self, path: str):
            self.path = path

        def _get_conn(self):
            return _FakeConn()

        def close(self):
            calls["close"] += 1

    monkeypatch.setattr("ws_ctx_engine.domain_map.DomainMapDB", _FakeDB)

    with runner.isolated_filesystem():
        repo = Path("repo")
        db_path = repo / ".ws-ctx-engine" / "domain_map.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"x")

        result = runner.invoke(app, ["vacuum", "repo"])

    assert result.exit_code == 0
    assert calls["vacuum"] == 1
    assert calls["close"] == 1


def test_vacuum_command_handles_unexpected_error(monkeypatch) -> None:
    class _BadDB:
        def __init__(self, path: str):
            raise RuntimeError("db down")

    monkeypatch.setattr("ws_ctx_engine.domain_map.DomainMapDB", _BadDB)

    with runner.isolated_filesystem():
        repo = Path("repo")
        db_path = repo / ".ws-ctx-engine" / "domain_map.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"x")

        result = runner.invoke(app, ["vacuum", "repo"])

    assert result.exit_code == 1
    assert "Error during VACUUM" in result.stdout


def test_reindex_domain_success_path(monkeypatch) -> None:
    class _Tracker:
        def format_metrics(self, kind: str) -> str:
            return f"{kind}-ok"

    monkeypatch.setattr("ws_ctx_engine.workflow.indexer.index_repository", lambda **kwargs: _Tracker())
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    with runner.isolated_filesystem():
        repo = Path("repo")
        index_dir = repo / ".ws-ctx-engine"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "metadata.json").write_text("{}", encoding="utf-8")

        result = runner.invoke(app, ["reindex-domain", "repo"])

    assert result.exit_code == 0
    assert "Domain map rebuilt" in result.stdout


def test_reindex_domain_handles_unexpected_error(monkeypatch) -> None:
    def _raise_error(**kwargs):
        raise RuntimeError("cannot reindex")

    monkeypatch.setattr("ws_ctx_engine.workflow.indexer.index_repository", _raise_error)
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())

    with runner.isolated_filesystem():
        repo = Path("repo")
        index_dir = repo / ".ws-ctx-engine"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "metadata.json").write_text("{}", encoding="utf-8")

        result = runner.invoke(app, ["reindex-domain", "repo"])

    assert result.exit_code == 1
    assert "Error rebuilding domain map" in result.stdout


def test_cli_entrypoint_maps_keyboard_interrupt_to_130(monkeypatch) -> None:
    import ws_ctx_engine.cli.cli as cli_module

    def _raise_interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_module, "app", _raise_interrupt)

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()

    assert exc_info.value.code == 130


def test_cli_entrypoint_maps_unexpected_error_to_1(monkeypatch) -> None:
    import ws_ctx_engine.cli.cli as cli_module

    def _raise_error() -> None:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(cli_module, "app", _raise_error)

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()

    assert exc_info.value.code == 1


def test_search_command_non_agent_mode_prints_ranked_results(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())
    monkeypatch.setattr(
        "ws_ctx_engine.cli.cli.search_codebase",
        lambda **kwargs: (
            [{"path": "src/a.py", "score": 0.9, "domain": "auth", "summary": "ok"}],
            {"index_built_at": "2026-01-01T00:00:00Z", "files_indexed": 1},
        ),
    )

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["search", "auth", "--repo", "."])

    assert result.exit_code == 0
    assert "src/a.py" in result.stdout


def test_query_command_repo_not_found() -> None:
    result = runner.invoke(app, ["query", "auth", "--repo", "/definitely/missing", "--verbose"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_pack_command_success_with_valid_overrides(monkeypatch) -> None:
    monkeypatch.setattr("ws_ctx_engine.cli.cli._load_config", lambda config, repo_path=None: _cfg())
    monkeypatch.setattr("ws_ctx_engine.cli.cli.index_repository", lambda **kwargs: None)
    monkeypatch.setattr("ws_ctx_engine.cli.cli.query_and_pack", lambda **kwargs: (Path("out.zip"), {}))

    with runner.isolated_filesystem():
        repo = Path("repo")
        repo.mkdir()
        result = runner.invoke(app, ["pack", "repo", "--format", "zip", "--budget", "123", "--verbose"])

    assert result.exit_code == 0


def test_pack_command_repo_not_found_and_not_directory() -> None:
    missing = runner.invoke(app, ["pack", "/definitely/missing"])
    assert missing.exit_code == 1
    assert "does not exist" in missing.stdout

    with runner.isolated_filesystem():
        file_path = Path("repo.txt")
        file_path.write_text("x", encoding="utf-8")
        not_dir = runner.invoke(app, ["pack", str(file_path)])

    assert not_dir.exit_code == 1
    assert "not a directory" in not_dir.stdout


def test_status_command_fails_for_missing_repo_no_index_and_incomplete_index() -> None:
    missing_repo = runner.invoke(app, ["status", "/definitely/missing"])
    assert missing_repo.exit_code == 1
    assert "does not exist" in missing_repo.stdout

    with runner.isolated_filesystem():
        Path("repo").mkdir()
        no_index = runner.invoke(app, ["status", "repo"])
        assert no_index.exit_code == 1
        assert "No index found" in no_index.stdout

        index_dir = Path("repo/.ws-ctx-engine")
        index_dir.mkdir(parents=True, exist_ok=True)
        incomplete = runner.invoke(app, ["status", "repo"])

    assert incomplete.exit_code == 1
    assert "metadata.json is missing" in incomplete.stdout


def test_vacuum_command_fails_for_missing_repo_no_index_and_no_db() -> None:
    missing_repo = runner.invoke(app, ["vacuum", "/definitely/missing"])
    assert missing_repo.exit_code == 1
    assert "does not exist" in missing_repo.stdout

    with runner.isolated_filesystem():
        Path("repo").mkdir()
        no_index = runner.invoke(app, ["vacuum", "repo"])
        assert no_index.exit_code == 1
        assert "No index found" in no_index.stdout

        index_dir = Path("repo/.ws-ctx-engine")
        index_dir.mkdir(parents=True, exist_ok=True)
        no_db = runner.invoke(app, ["vacuum", "repo"])

    assert no_db.exit_code == 1
    assert "Domain map database not found" in no_db.stdout


def test_reindex_domain_fails_for_missing_repo_no_index_and_missing_metadata() -> None:
    missing_repo = runner.invoke(app, ["reindex-domain", "/definitely/missing"])
    assert missing_repo.exit_code == 1
    assert "does not exist" in missing_repo.stdout

    with runner.isolated_filesystem():
        Path("repo").mkdir()
        no_index = runner.invoke(app, ["reindex-domain", "repo"])
        assert no_index.exit_code == 1
        assert "No index found" in no_index.stdout

        index_dir = Path("repo/.ws-ctx-engine")
        index_dir.mkdir(parents=True, exist_ok=True)
        missing_metadata = runner.invoke(app, ["reindex-domain", "repo"])

    assert missing_metadata.exit_code == 1
    assert "metadata.json is missing" in missing_metadata.stdout


def test_load_config_explicit_existing_file(monkeypatch) -> None:
    loaded: dict[str, str | None] = {"path": None}

    def _fake_load(path=None):
        loaded["path"] = path
        return _cfg()

    monkeypatch.setattr("ws_ctx_engine.cli.cli.Config.load", _fake_load)

    with runner.isolated_filesystem():
        cfg_file = Path("cfg.yaml")
        cfg_file.write_text("format: xml\n", encoding="utf-8")
        _load_config(str(cfg_file))

    assert loaded["path"] == "cfg.yaml"
