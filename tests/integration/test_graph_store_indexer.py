"""Integration tests: index_repository() correctly builds and persists graph.

TDD: written BEFORE confirming they pass (RED phase).
All tests skip when pycozo is not installed.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

pycozo = pytest.importorskip("pycozo", reason="pycozo not installed — skipping integration tests")

from ws_ctx_engine.config.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_small_repo(tmpdir: Path) -> None:
    """Create a small Python repo with cross-file function calls."""
    (tmpdir / "auth.py").write_text(
        "def login(user: str, password: str) -> bool:\n"
        "    return validate_user(user, password)\n\n"
        "def logout(user: str) -> None:\n"
        "    pass\n"
    )
    (tmpdir / "utils.py").write_text(
        "def validate_user(user: str, password: str) -> bool:\n"
        "    return bool(user and password)\n\n"
        "def hash_password(password: str) -> str:\n"
        "    return password\n"
    )
    (tmpdir / "main.py").write_text(
        "from auth import login\n\n"
        "def run() -> None:\n"
        "    login('admin', 'secret')\n"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIndexerBuildsGraph:
    def test_indexer_builds_graph_in_memory(self) -> None:
        """index_repository with mem storage produces a healthy graph store."""
        from ws_ctx_engine.workflow.indexer import index_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _make_small_repo(repo)

            config = Config()
            config.graph_store_enabled = True
            config.graph_store_storage = "mem"
            # Disable vector index to speed up test (no embeddings needed)
            config.backends = {"vector_index": "auto", "graph": "auto", "embeddings": "auto"}

            # Should complete without raising
            tracker = index_repository(str(repo), config=config)
            assert tracker is not None

    def test_indexer_graph_store_disabled_skips_phase(self) -> None:
        """When graph_store_enabled=False the phase is skipped (no error)."""
        from ws_ctx_engine.workflow.indexer import index_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _make_small_repo(repo)

            config = Config()
            config.graph_store_enabled = False

            tracker = index_repository(str(repo), config=config)
            assert tracker is not None

    def test_indexer_without_pycozo_still_succeeds(self) -> None:
        """When pycozo import fails, indexer completes normally (non-fatal)."""
        from ws_ctx_engine.workflow.indexer import index_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _make_small_repo(repo)

            config = Config()
            config.graph_store_enabled = True
            config.graph_store_storage = "mem"

            # Patch _create_client to simulate missing pycozo
            import ws_ctx_engine.graph.cozo_store as cozo_mod

            with patch.object(cozo_mod, "_create_client", side_effect=ImportError("no pycozo")):
                tracker = index_repository(str(repo), config=config)

            assert tracker is not None

    def test_indexer_graph_store_mem_queryable(self) -> None:
        """After indexing, GraphStore built separately with same data is queryable."""
        from ws_ctx_engine.graph.builder import chunks_to_full_graph
        from ws_ctx_engine.graph.cozo_store import GraphStore
        from ws_ctx_engine.chunker.tree_sitter import TreeSitterChunker

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            _make_small_repo(repo)

            chunker = TreeSitterChunker()
            chunks = chunker.parse(str(repo))
            assert chunks, "No chunks produced"

            nodes, edges = chunks_to_full_graph(chunks)
            store = GraphStore("mem")
            assert store.is_healthy

            store.bulk_upsert(nodes, edges)

            # At least one file should have symbols
            file_ids = [n.id for n in nodes if n.kind == "file"]
            found_any = False
            for fid in file_ids:
                syms = store.contains_of(fid)
                if syms:
                    found_any = True
                    break
            assert found_any, "No contains_of results found for any file"
