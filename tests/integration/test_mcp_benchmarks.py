"""Benchmark-style tests for MCP performance hardening."""

from __future__ import annotations

import importlib.util
import sys
import time
import types
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ws_ctx_engine.config import Config
from ws_ctx_engine.mcp.config import MCPConfig
from ws_ctx_engine.mcp.tools import MCPToolService
from ws_ctx_engine.secret_scanner import SecretScanner
from ws_ctx_engine.workflow import index_repository

pytestmark = [pytest.mark.benchmark, pytest.mark.integration]

FAISS_AVAILABLE = importlib.util.find_spec("faiss") is not None
NETWORKX_AVAILABLE = importlib.util.find_spec("networkx") is not None


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
def benchmark_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "mcp_benchmark_repo"
    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)

    for i in range(80):
        (src / f"module_{i}.py").write_text(
            f"""
def authenticate_{i}(username: str, password: str) -> bool:
    token = f"{{username}}:{{password}}"
    return token.startswith("admin")


def login_flow_{i}(user: str, pwd: str) -> bool:
    return authenticate_{i}(user, pwd)
""",
            encoding="utf-8",
        )

    return repo


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * p))))
    return ordered[idx]


@pytest.mark.skipif(
    not (FAISS_AVAILABLE and NETWORKX_AVAILABLE),
    reason="MCP benchmark requires faiss-cpu and networkx",
)
def test_search_codebase_p99_latency_under_200ms(benchmark_repo: Path) -> None:
    cfg = Config()
    cfg.backends["vector_index"] = "faiss"
    cfg.backends["graph"] = "networkx"
    cfg.backends["embeddings"] = "local"
    index_repository(repo_path=str(benchmark_repo), config=cfg)

    service = MCPToolService(workspace=str(benchmark_repo), config=MCPConfig())

    for _ in range(5):
        service.call_tool("search_codebase", {"query": "authentication login", "limit": 10})

    samples_ms: list[float] = []
    for _ in range(30):
        started = time.perf_counter()
        payload = service.call_tool(
            "search_codebase", {"query": "authentication login", "limit": 10}
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        assert "error" not in payload
        samples_ms.append(elapsed_ms)

    p50 = _percentile(samples_ms, 0.50)
    p99 = _percentile(samples_ms, 0.99)
    print(f"search_codebase latency: p50={p50:.2f}ms p99={p99:.2f}ms")

    assert p99 < 200.0


def test_secret_scan_cache_hit_rate_high_for_repeated_reads(tmp_path: Path) -> None:
    repo = tmp_path / "scan_cache_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".ws-ctx-engine").mkdir(parents=True, exist_ok=True)

    target = repo / "config.py"
    target.write_text('API_KEY = "sk-live-secret-benchmark-token"\n', encoding="utf-8")

    scanner = SecretScanner(repo_path=str(repo))
    read_calls = {"count": 0}
    original_read_text = scanner._read_text

    def counting_read_text(path: Path):
        read_calls["count"] += 1
        return original_read_text(path)

    scanner._read_text = counting_read_text  # type: ignore[method-assign]

    total_scans = 25
    for _ in range(total_scans):
        result = scanner.scan("config.py")
        assert len(result.secrets_detected) >= 1

    cache_hits = total_scans - read_calls["count"]
    hit_rate = cache_hits / total_scans
    print(f"secret scan cache hit rate: {hit_rate:.2%}")

    assert read_calls["count"] == 1
    assert hit_rate >= 0.95


def test_secret_scan_cache_hit_rate_realistic_repo(tmp_path: Path) -> None:
    repo = tmp_path / "scan_cache_realistic_repo"
    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)
    (repo / ".ws-ctx-engine").mkdir(parents=True, exist_ok=True)

    total_files = 120
    secret_file_count = 0
    relative_paths: list[str] = []

    for i in range(total_files):
        file_path = src / f"module_{i}.py"
        if i % 10 == 0:
            secret_file_count += 1
            content = f'API_KEY = "sk-live-realistic-secret-{i:03d}"\n'
        else:
            content = "def helper(value: int) -> int:\n" "    return value * 2\n"
        file_path.write_text(content, encoding="utf-8")
        relative_paths.append(file_path.relative_to(repo).as_posix())

    scanner = SecretScanner(repo_path=str(repo))
    read_calls = {"count": 0}
    original_read_text = scanner._read_text

    def counting_read_text(path: Path):
        read_calls["count"] += 1
        return original_read_text(path)

    scanner._read_text = counting_read_text  # type: ignore[method-assign]

    first_pass_secret_hits = 0
    for rel_path in relative_paths:
        result = scanner.scan(rel_path)
        if result.secrets_detected:
            first_pass_secret_hits += 1

    reads_after_first_pass = read_calls["count"]

    second_pass_secret_hits = 0
    for rel_path in relative_paths:
        result = scanner.scan(rel_path)
        if result.secrets_detected:
            second_pass_secret_hits += 1

    second_pass_reads = read_calls["count"] - reads_after_first_pass
    cache_hit_rate = (total_files - second_pass_reads) / total_files
    print(f"secret scan realistic cache hit rate: {cache_hit_rate:.2%}")

    assert reads_after_first_pass == total_files
    assert second_pass_reads == 0
    assert first_pass_secret_hits == secret_file_count
    assert second_pass_secret_hits == secret_file_count
    assert cache_hit_rate >= 0.99


def test_get_domain_map_cache_latency_and_rate_limit_behavior(tmp_path: Path) -> None:
    config = MCPConfig(
        rate_limits={
            "search_codebase": 60,
            "get_file_context": 120,
            "get_domain_map": 1,
            "get_index_status": 10,
        },
        cache_ttl_seconds=30,
    )
    service = MCPToolService(workspace=str(tmp_path), config=config)

    calls = {"count": 0}

    def fake_domain_map() -> dict[str, object]:
        calls["count"] += 1
        return {
            "domains": [],
            "graph_stats": {"total_nodes": 0, "total_edges": 0, "avg_degree": 0.0},
            "index_health": {"status": "unknown"},
        }

    service._get_domain_map = fake_domain_map  # type: ignore[method-assign]

    first = service.call_tool("get_domain_map", {})
    assert "error" not in first
    assert calls["count"] == 1

    samples_ms: list[float] = []
    for _ in range(60):
        started = time.perf_counter()
        payload = service.call_tool("get_domain_map", {})
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        assert "error" not in payload
        samples_ms.append(elapsed_ms)

    p99 = _percentile(samples_ms, 0.99)
    print(f"get_domain_map cached latency: p99={p99:.2f}ms")

    assert calls["count"] == 1
    assert p99 < 20.0


def test_get_index_status_cache_latency_and_rate_limit_behavior(tmp_path: Path) -> None:
    config = MCPConfig(
        rate_limits={
            "search_codebase": 60,
            "get_file_context": 120,
            "get_domain_map": 10,
            "get_index_status": 1,
        },
        cache_ttl_seconds=30,
    )
    service = MCPToolService(workspace=str(tmp_path), config=config)

    calls = {"count": 0}

    def fake_index_status() -> dict[str, object]:
        calls["count"] += 1
        return {
            "index_health": {
                "status": "current",
                "stale_reason": None,
                "files_indexed": 1,
                "index_built_at": "2026-03-25T00:00:00Z",
                "vcs": "none",
            },
            "recommendation": "Index appears up-to-date.",
            "workspace": str(tmp_path),
        }

    service._get_index_status = fake_index_status  # type: ignore[method-assign]

    first = service.call_tool("get_index_status", {})
    assert "error" not in first
    assert calls["count"] == 1

    samples_ms: list[float] = []
    for _ in range(60):
        started = time.perf_counter()
        payload = service.call_tool("get_index_status", {})
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        assert "error" not in payload
        samples_ms.append(elapsed_ms)

    p99 = _percentile(samples_ms, 0.99)
    print(f"get_index_status cached latency: p99={p99:.2f}ms")

    assert calls["count"] == 1
    assert p99 < 20.0
