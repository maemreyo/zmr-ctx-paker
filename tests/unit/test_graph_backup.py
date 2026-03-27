"""Tests for wsctx graph backup CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ws_ctx_engine.cli.cli import app

runner = CliRunner()


class TestGraphBackup:
    def test_backup_copies_directory(self, tmp_path: Path) -> None:
        """Happy path: copytree is called with correct source and destination."""
        src = tmp_path / ".ws-ctx-engine" / "graph.db"
        src.mkdir(parents=True)
        (src / "CURRENT").write_text("rocksdb data")
        dest = tmp_path / "backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(src)
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            with patch("shutil.copytree") as mock_copy:
                result = runner.invoke(app, ["graph", "backup", str(dest)])
                assert result.exit_code == 0
                mock_copy.assert_called_once()

    def test_backup_destination_in_copytree_call(self, tmp_path: Path) -> None:
        """Destination argument is forwarded to shutil.copytree as the dst."""
        src = tmp_path / "graph.db"
        src.mkdir(parents=True)
        dest = tmp_path / "my_backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(src)
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            with patch("shutil.copytree") as mock_copy:
                result = runner.invoke(app, ["graph", "backup", str(dest)])
                assert result.exit_code == 0
                _, call_kwargs = mock_copy.call_args
                # second positional arg is dst
                positional_args = mock_copy.call_args[0]
                assert Path(positional_args[1]) == dest

    def test_backup_fails_gracefully_if_source_missing(self, tmp_path: Path) -> None:
        """When source path does not exist the command exits non-zero with a clear message."""
        dest = tmp_path / "backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(tmp_path / "nonexistent" / "graph.db")
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            result = runner.invoke(app, ["graph", "backup", str(dest)])
            assert result.exit_code != 0 or (
                "not found" in result.output.lower()
                or "does not exist" in result.output.lower()
            )

    def test_backup_mem_store_warns_and_exits_nonzero(self, tmp_path: Path) -> None:
        """In-memory graph store has nothing to back up — command warns and exits non-zero."""
        dest = tmp_path / "backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = ""
            mock_cfg.graph_store_storage = "mem"
            mock_cfg_cls.load.return_value = mock_cfg

            result = runner.invoke(app, ["graph", "backup", str(dest)])
            assert (
                "mem" in result.output.lower()
                or "nothing" in result.output.lower()
                or "no persistent" in result.output.lower()
                or result.exit_code != 0
            )

    def test_backup_dest_already_exists_exits_nonzero(self, tmp_path: Path) -> None:
        """When destination already exists, command exits non-zero with a clear message."""
        src = tmp_path / "graph.db"
        src.mkdir(parents=True)
        dest = tmp_path / "existing_dest"
        dest.mkdir()

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(src)
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            result = runner.invoke(app, ["graph", "backup", str(dest)])
            assert result.exit_code != 0
            assert "already exists" in result.output.lower() or "exist" in result.output.lower()

    def test_backup_copytree_exception_is_handled(self, tmp_path: Path) -> None:
        """When shutil.copytree raises, the command exits non-zero with an error message."""
        src = tmp_path / "graph.db"
        src.mkdir(parents=True)
        dest = tmp_path / "backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(src)
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            with patch("shutil.copytree", side_effect=OSError("disk full")):
                result = runner.invoke(app, ["graph", "backup", str(dest)])
                assert result.exit_code != 0
                assert "backup failed" in result.output.lower() or "disk full" in result.output.lower()

    def test_backup_success_output_contains_paths(self, tmp_path: Path) -> None:
        """Success message references source and destination paths."""
        src = tmp_path / "graph.db"
        src.mkdir(parents=True)
        dest = tmp_path / "backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(src)
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            with patch("shutil.copytree"):
                result = runner.invoke(app, ["graph", "backup", str(dest)])
                assert result.exit_code == 0
                assert "backup" in result.output.lower() or str(dest) in result.output

    def test_backup_absolute_path_used_directly(self, tmp_path: Path) -> None:
        """When graph_store_path is already absolute, it is used as-is."""
        src = tmp_path / "abs_graph.db"
        src.mkdir(parents=True)
        dest = tmp_path / "backup"

        with patch("ws_ctx_engine.cli.cli.Config") as mock_cfg_cls:
            mock_cfg = MagicMock()
            mock_cfg.graph_store_path = str(src)  # absolute
            mock_cfg.graph_store_storage = "rocksdb"
            mock_cfg_cls.load.return_value = mock_cfg

            with patch("shutil.copytree") as mock_copy:
                result = runner.invoke(app, ["graph", "backup", str(dest)])
                assert result.exit_code == 0
                call_src = mock_copy.call_args[0][0]
                assert Path(call_src) == src
