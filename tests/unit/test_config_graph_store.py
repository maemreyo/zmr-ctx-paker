"""Tests for graph_store config fields added in Sub-phase 2c.

TDD: written BEFORE implementation (RED phase).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
import pytest

from ws_ctx_engine.config.config import Config


class TestGraphStoreConfigDefaults:
    def test_graph_store_enabled_default(self) -> None:
        config = Config()
        assert config.graph_store_enabled is True

    def test_graph_store_storage_default(self) -> None:
        config = Config()
        assert config.graph_store_storage == "rocksdb"

    def test_graph_store_path_default(self) -> None:
        config = Config()
        assert config.graph_store_path == ".ws-ctx-engine/graph.db"


class TestGraphStoreConfigFromYaml:
    def _write_yaml(self, content: dict) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(content, f)
            return f.name

    def test_load_graph_store_enabled_false(self) -> None:
        path = self._write_yaml({"graph_store_enabled": False})
        config = Config.load(path)
        assert config.graph_store_enabled is False

    def test_load_graph_store_storage_mem(self) -> None:
        path = self._write_yaml({"graph_store_storage": "mem"})
        config = Config.load(path)
        assert config.graph_store_storage == "mem"

    def test_load_graph_store_storage_sqlite(self) -> None:
        path = self._write_yaml({"graph_store_storage": "sqlite"})
        config = Config.load(path)
        assert config.graph_store_storage == "sqlite"

    def test_load_graph_store_path_custom(self) -> None:
        path = self._write_yaml({"graph_store_path": "/tmp/custom_graph.db"})
        config = Config.load(path)
        assert config.graph_store_path == "/tmp/custom_graph.db"

    def test_invalid_storage_value_falls_back_to_default(self) -> None:
        """Unknown storage value → default 'rocksdb'."""
        path = self._write_yaml({"graph_store_storage": "unknown_backend"})
        config = Config.load(path)
        assert config.graph_store_storage == "rocksdb"

    def test_missing_fields_keep_defaults(self) -> None:
        """YAML without graph_store keys → fields use defaults."""
        path = self._write_yaml({"format": "xml"})
        config = Config.load(path)
        assert config.graph_store_enabled is True
        assert config.graph_store_storage == "rocksdb"
        assert config.graph_store_path == ".ws-ctx-engine/graph.db"


class TestPhase3ConfigFields:
    def _write_yaml(self, content: dict) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(content, f)
            return f.name

    def test_context_assembler_enabled_default(self) -> None:
        config = Config()
        assert config.context_assembler_enabled is True

    def test_graph_query_weight_default(self) -> None:
        config = Config()
        assert config.graph_query_weight == 0.3

    def test_graph_query_weight_invalid(self) -> None:
        """graph_query_weight outside [0.0, 1.0] raises ValueError."""
        with pytest.raises(ValueError):
            Config(graph_query_weight=1.5)

    def test_graph_query_weight_invalid_negative(self) -> None:
        with pytest.raises(ValueError):
            Config(graph_query_weight=-0.1)

    def test_graph_query_weight_boundary_zero(self) -> None:
        config = Config(graph_query_weight=0.0)
        assert config.graph_query_weight == 0.0

    def test_graph_query_weight_boundary_one(self) -> None:
        config = Config(graph_query_weight=1.0)
        assert config.graph_query_weight == 1.0

    def test_load_graph_query_weight_from_yaml(self) -> None:
        path = self._write_yaml({"graph_query_weight": 0.1})
        config = Config.load(path)
        assert config.graph_query_weight == pytest.approx(0.1)

    def test_load_context_assembler_enabled_false(self) -> None:
        path = self._write_yaml({"context_assembler_enabled": False})
        config = Config.load(path)
        assert config.context_assembler_enabled is False

    def test_load_graph_query_weight_invalid_logs_error(self) -> None:
        path = self._write_yaml({"graph_query_weight": 1.5})
        config = Config.load(path)
        assert config.graph_query_weight == pytest.approx(0.3)
