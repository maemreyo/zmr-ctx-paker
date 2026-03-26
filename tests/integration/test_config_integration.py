"""
Integration tests for configuration management.

Tests real-world usage scenarios with actual YAML files.
"""

import os
import tempfile
from pathlib import Path

import yaml

from ws_ctx_engine import Config


class TestConfigIntegration:
    """Integration tests for Config with real file system."""

    def test_load_example_config(self):
        """Test loading the example configuration file."""
        if os.path.exists(".ws-ctx-engine.yaml.example"):
            config = Config.load(".ws-ctx-engine.yaml.example")
            assert config.format in ["xml", "zip"]
            assert config.token_budget > 0
            assert 0.0 <= config.semantic_weight <= 1.0
            assert 0.0 <= config.pagerank_weight <= 1.0

    def test_full_workflow(self):
        """Test complete workflow: create config, save, load, validate."""
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test-config.yaml"

            # Create a custom configuration
            config_data = {
                "format": "xml",
                "token_budget": 50000,
                "output_path": "./custom_output",
                "semantic_weight": 0.7,
                "pagerank_weight": 0.3,
                "include_tests": True,
                "include_patterns": ["**/*.py", "**/*.js"],
                "exclude_patterns": ["node_modules/**"],
                "backends": {"vector_index": "faiss", "graph": "networkx", "embeddings": "local"},
                "embeddings": {"model": "custom-model", "device": "cpu", "batch_size": 64},
                "performance": {
                    "max_workers": 8,
                    "cache_embeddings": True,
                    "incremental_index": False,
                },
            }

            # Save configuration to file
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load configuration
            config = Config.load(str(config_path))

            # Verify all settings
            assert config.format == "xml"
            assert config.token_budget == 50000
            assert config.output_path == "./custom_output"
            assert config.semantic_weight == 0.7
            assert config.pagerank_weight == 0.3
            assert config.include_tests is True
            assert config.include_patterns == ["**/*.py", "**/*.js"]
            assert config.exclude_patterns == ["node_modules/**"]
            assert config.backends["vector_index"] == "faiss"
            assert config.backends["graph"] == "networkx"
            assert config.backends["embeddings"] == "local"
            assert config.embeddings["model"] == "custom-model"
            assert config.embeddings["device"] == "cpu"
            assert config.embeddings["batch_size"] == 64
            assert config.performance["max_workers"] == 8
            assert config.performance["cache_embeddings"] is True
            assert config.performance["incremental_index"] is False

    def test_graceful_degradation(self):
        """Test graceful degradation with partially invalid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "partial-invalid.yaml"

            # Create config with some invalid values
            config_data = {
                "format": "invalid_format",  # Invalid
                "token_budget": 75000,  # Valid
                "semantic_weight": 1.5,  # Invalid (out of range)
                "pagerank_weight": 0.4,  # Valid
                "backends": {"vector_index": "unknown", "graph": "networkx"},  # Invalid  # Valid
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load configuration
            config = Config.load(str(config_path))

            # Valid values should be loaded
            assert config.token_budget == 75000
            assert config.pagerank_weight == 0.4
            assert config.backends["graph"] == "networkx"

            # Invalid values should use defaults
            assert config.format == "zip"  # Default
            assert config.semantic_weight == 0.5  # Fallback
            assert config.backends["vector_index"] == "auto"  # Default

    def test_minimal_config(self):
        """Test loading minimal configuration with only essential fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "minimal.yaml"

            # Create minimal config
            config_data = {"format": "xml", "token_budget": 50000}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load configuration
            config = Config.load(str(config_path))

            # Specified values
            assert config.format == "xml"
            assert config.token_budget == 50000

            # Defaults for unspecified values
            assert config.semantic_weight == 0.6
            assert config.pagerank_weight == 0.4
            assert config.include_tests is False
            assert len(config.include_patterns) > 0
            assert config.backends["vector_index"] == "auto"
