from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from ws_ctx_engine.mcp.config import MCPConfig
from ws_ctx_engine.mcp.tools import MCPToolService


def _config() -> MCPConfig:
    return MCPConfig(
        rate_limits={
            "search_codebase": 60,
            "get_file_context": 60,
            "get_domain_map": 60,
            "get_index_status": 60,
        }
    )


class _FakeMetadata:
    def __init__(self, *, stale: bool = False, file_hashes: dict[str, str] | None = None):
        self.created_at = datetime(2026, 1, 1, 0, 0, 0)
        self.repo_path = "."
        self.file_count = len(file_hashes or {})
        self.backend = "faiss"
        self.file_hashes = file_hashes or {}
        self._stale = stale

    def is_stale(self, repo_path: str) -> bool:
        return self._stale


class _FakeNXGraphObj:
    def successors(self, path: str):
        if path == "src/a.py":
            return ["src/b.py"]
        return []

    def predecessors(self, path: str):
        if path == "src/a.py":
            return ["src/c.py"]
        return []

    def number_of_nodes(self) -> int:
        return 3

    def number_of_edges(self) -> int:
        return 2


class _FakeNXGraph:
    def __init__(self):
        self._nx = True
        self.graph = _FakeNXGraphObj()

    def pagerank(self) -> dict[str, float]:
        return {"src/a.py": 0.9, "src/b.py": 0.4, "src/c.py": 0.2}


class _FakeIGraphObj:
    def successors(self, vertex: int):
        if vertex == 1:
            return [2]
        return []

    def predecessors(self, vertex: int):
        if vertex == 1:
            return [3]
        return []

    def vcount(self) -> int:
        return 3

    def ecount(self) -> int:
        return 2


class _FakeIGraph:
    def __init__(self):
        self.graph = _FakeIGraphObj()
        self.file_to_vertex = {"src/a.py": 1}
        self.vertex_to_file = {1: "src/a.py", 2: "src/b.py", 3: "src/c.py"}

    def pagerank(self) -> dict[str, float]:
        return {"src/a.py": 0.8, "src/b.py": 0.5, "src/c.py": 0.3}


def test_search_codebase_maps_file_not_found_to_index_not_found(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())

        def _raise_not_found(**kwargs):
            raise FileNotFoundError("index missing")

        monkeypatch.setattr("ws_ctx_engine.mcp.tools.search_codebase", _raise_not_found)
        payload = service.call_tool("search_codebase", {"query": "auth"})

    assert payload["error"] == "INDEX_NOT_FOUND"


def test_get_domain_map_returns_index_not_found_when_metadata_missing(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())
        monkeypatch.setattr(service, "_load_metadata", lambda: None)

        payload = service.call_tool("get_domain_map", {})

    assert payload["error"] == "INDEX_NOT_FOUND"


def test_get_domain_map_success_path_with_ranked_domains(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())
        metadata = _FakeMetadata(file_hashes={"src/a.py": "h1", "src/b.py": "h2", "src/c.py": "h3"})
        monkeypatch.setattr(service, "_load_metadata", lambda: metadata)
        monkeypatch.setattr(
            "ws_ctx_engine.mcp.tools.load_indexes",
            lambda *args, **kwargs: (None, _FakeNXGraph(), None),
        )

        class _FakeDB:
            def __init__(self, path: str):
                self.keywords = {"auth", "payments"}

            def get(self, keyword: str):
                if keyword == "auth":
                    return ["src"]
                return ["docs"]

            def close(self):
                return None

        monkeypatch.setattr("ws_ctx_engine.mcp.tools.DomainMapDB", _FakeDB)

        payload = service.call_tool("get_domain_map", {})

    assert "error" not in payload
    assert payload["graph_stats"]["total_nodes"] == 3
    assert payload["domains"]
    assert payload["domains"][0]["name"] == "auth"
    assert payload["domains"][0]["top_files"]


def test_get_domain_map_handles_index_and_db_failures(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())
        metadata = _FakeMetadata(file_hashes={"src/a.py": "h1"})
        monkeypatch.setattr(service, "_load_metadata", lambda: metadata)

        def _raise_load_indexes(*args, **kwargs):
            raise RuntimeError("graph unavailable")

        class _BadDB:
            def __init__(self, path: str):
                raise RuntimeError("db unavailable")

        monkeypatch.setattr("ws_ctx_engine.mcp.tools.load_indexes", _raise_load_indexes)
        monkeypatch.setattr("ws_ctx_engine.mcp.tools.DomainMapDB", _BadDB)

        payload = service.call_tool("get_domain_map", {})

    assert payload["domains"] == []
    assert payload["graph_stats"] == {"total_nodes": 0, "total_edges": 0, "avg_degree": 0.0}


def test_get_index_status_success_response_is_cached(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = MCPConfig(
            rate_limits={
                "search_codebase": 60,
                "get_file_context": 60,
                "get_domain_map": 60,
                "get_index_status": 1,
            }
        )
        service = MCPToolService(workspace=tmpdir, config=cfg)

        calls = {"count": 0}

        def _ok_status():
            calls["count"] += 1
            return {
                "index_health": {"status": "current"},
                "recommendation": "Index appears up-to-date.",
                "workspace": tmpdir,
            }

        monkeypatch.setattr(service, "_get_index_status", _ok_status)

        first = service.call_tool("get_index_status", {})
        second = service.call_tool("get_index_status", {})

    assert "error" not in first
    assert "error" not in second
    assert calls["count"] == 1


def test_build_index_health_handles_git_stale_and_current() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / ".git").mkdir(parents=True, exist_ok=True)
        service = MCPToolService(workspace=str(repo), config=_config())

        stale = service._build_index_health(
            _FakeMetadata(stale=True, file_hashes={"src/a.py": "h"})
        )
        current = service._build_index_health(
            _FakeMetadata(stale=False, file_hashes={"src/a.py": "h"})
        )

    assert stale["status"] == "stale"
    assert stale["stale_reason"]
    assert stale["index_built_at"].endswith("Z")
    assert current["status"] == "current"


def test_load_neighbors_supports_nx_and_igraph_shapes(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())

        monkeypatch.setattr(
            "ws_ctx_engine.mcp.tools.load_indexes",
            lambda *args, **kwargs: (None, _FakeNXGraph(), None),
        )
        deps_nx, dents_nx = service._load_neighbors("src/a.py")

        monkeypatch.setattr(
            "ws_ctx_engine.mcp.tools.load_indexes",
            lambda *args, **kwargs: (None, _FakeIGraph(), None),
        )
        deps_ig, dents_ig = service._load_neighbors("src/a.py")

    assert deps_nx == ["src/b.py"]
    assert dents_nx == ["src/c.py"]
    assert deps_ig == ["src/b.py"]
    assert dents_ig == ["src/c.py"]


def test_graph_stats_and_helpers_cover_edge_cases(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())

        nx_stats = service._graph_stats(_FakeNXGraph())
        ig_stats = service._graph_stats(_FakeIGraph())

        class _BadGraph:
            graph = object()

        bad_stats = service._graph_stats(_BadGraph())

        matched = service._matched_files(["src/a.py", "README.md"], [".", "src", ""])
        language = service._detect_language(Path("file.unknown"))

        import builtins

        missing_path = Path(tmpdir) / "missing.py"
        monkeypatch.setattr(
            builtins, "open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("no read"))
        )
        line_count = service._line_count(missing_path)

    assert nx_stats == {"total_nodes": 3, "total_edges": 2, "avg_degree": 1.33}
    assert ig_stats == {"total_nodes": 3, "total_edges": 2, "avg_degree": 1.33}
    assert bad_stats == {"total_nodes": 0, "total_edges": 0, "avg_degree": 0.0}
    assert matched == ["src/a.py"]
    assert language == "text"
    assert line_count == 0


def test_get_index_status_returns_index_not_found_when_metadata_missing(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())
        monkeypatch.setattr(service, "_load_metadata", lambda: None)

        payload = service.call_tool("get_index_status", {})

    assert payload["error"] == "INDEX_NOT_FOUND"
    assert payload["workspace"] == str(Path(tmpdir).resolve())


def test_load_metadata_reads_valid_metadata_payload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        index_dir = repo / ".ws-ctx-engine"
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "metadata.json").write_text(
            '{"created_at": "2026-01-01T00:00:00", "repo_path": "/repo", "file_count": 2, "backend": "faiss", "file_hashes": {"a.py": "h1"}}',
            encoding="utf-8",
        )

        service = MCPToolService(workspace=str(repo), config=_config())
        metadata = service._load_metadata()

    assert metadata is not None
    assert metadata.repo_path == "/repo"
    assert metadata.file_count == 2
    assert metadata.file_hashes == {"a.py": "h1"}


def test_index_health_or_unknown_when_no_metadata_and_no_git(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service = MCPToolService(workspace=tmpdir, config=_config())
        monkeypatch.setattr(service, "_load_metadata", lambda: None)

        payload = service._index_health_or_unknown()

    assert payload["status"] == "unknown"
    assert payload["vcs"] == "none"
    assert payload["index_built_at"] is None


def test_cache_read_write_and_expiration() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = MCPConfig(
            rate_limits={
                "search_codebase": 60,
                "get_file_context": 60,
                "get_domain_map": 60,
                "get_index_status": 60,
            },
            cache_ttl_seconds=1,
        )
        service = MCPToolService(workspace=tmpdir, config=cfg)

        service._write_cache("k", {"ok": True})
        assert service._read_cache("k") == {"ok": True}

        service._cache["k"].expires_at = 0
        assert service._read_cache("k") is None
        assert "k" not in service._cache
