"""
Unit tests for configuration management.

Tests Config dataclass, YAML loading, validation, and default fallback.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from ws_ctx_engine.config import Config


class TestConfigDefaults:
    """Test default configuration values."""
    
    def test_default_output_settings(self):
        """Test default output settings."""
        config = Config()
        assert config.format == "zip"
        assert config.token_budget == 100000
        assert config.output_path == "./output"
    
    def test_default_scoring_weights(self):
        """Test default scoring weights."""
        config = Config()
        assert config.semantic_weight == 0.6
        assert config.pagerank_weight == 0.4
        assert config.semantic_weight + config.pagerank_weight == 1.0
    
    def test_default_file_filtering(self):
        """Test default file filtering settings."""
        config = Config()
        assert config.include_tests is False
        assert config.respect_gitignore is True
        assert "**/*.py" in config.include_patterns
        assert "**/*.js" in config.include_patterns
        assert "node_modules/**" in config.exclude_patterns
        assert "__pycache__/**" in config.exclude_patterns
    
    def test_default_backends(self):
        """Test default backend selection."""
        config = Config()
        assert config.backends["vector_index"] == "auto"
        assert config.backends["graph"] == "auto"
        assert config.backends["embeddings"] == "auto"
    
    def test_default_embeddings(self):
        """Test default embeddings configuration."""
        config = Config()
        assert config.embeddings["model"] == "all-MiniLM-L6-v2"
        assert config.embeddings["device"] == "cpu"
        assert config.embeddings["batch_size"] == 32
        assert config.embeddings["api_provider"] == "openai"
        assert config.embeddings["api_key_env"] == "OPENAI_API_KEY"
    
    def test_default_performance(self):
        """Test default performance settings."""
        config = Config()
        assert config.performance["max_workers"] == 4
        assert config.performance["cache_embeddings"] is True
        assert config.performance["incremental_index"] is True


class TestConfigLoading:
    """Test configuration loading from YAML files."""
    
    def test_load_missing_file(self):
        """Test loading when configuration file doesn't exist."""
        config = Config.load("nonexistent.yaml")
        assert config.format == "zip"  # Should use defaults
        assert config.token_budget == 100000
    
    def test_load_empty_file(self):
        """Test loading empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "zip"  # Should use defaults
        finally:
            os.unlink(temp_path)
    
    def test_load_valid_config(self):
        """Test loading valid configuration."""
        config_data = {
            "format": "xml",
            "token_budget": 50000,
            "output_path": "./custom_output",
            "semantic_weight": 0.7,
            "pagerank_weight": 0.3,
            "include_tests": True,
            "respect_gitignore": False,
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "xml"
            assert config.token_budget == 50000
            assert config.output_path == "./custom_output"
            assert config.semantic_weight == 0.7
            assert config.pagerank_weight == 0.3
            assert config.include_tests is True
            assert config.respect_gitignore is False
        finally:
            os.unlink(temp_path)
    
    def test_load_partial_config(self):
        """Test loading partial configuration with defaults."""
        config_data = {
            "format": "xml",
            "token_budget": 75000,
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "xml"
            assert config.token_budget == 75000
            assert config.semantic_weight == 0.6  # Default
            assert config.pagerank_weight == 0.4  # Default
        finally:
            os.unlink(temp_path)
    
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "zip"  # Should use defaults
        finally:
            os.unlink(temp_path)


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_format_valid(self):
        """Test valid format values."""
        config_data = {"format": "xml"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "xml"
        finally:
            os.unlink(temp_path)
    
    def test_validate_format_invalid(self):
        """Test invalid format value."""
        config_data = {"format": "invalid"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "zip"  # Should use default
        finally:
            os.unlink(temp_path)
    
    def test_validate_format_wrong_type(self):
        """Test format with wrong type."""
        config_data = {"format": 123}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "zip"  # Should use default
        finally:
            os.unlink(temp_path)
    
    def test_validate_token_budget_valid(self):
        """Test valid token budget."""
        config_data = {"token_budget": 50000}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.token_budget == 50000
        finally:
            os.unlink(temp_path)
    
    def test_validate_token_budget_negative(self):
        """Test negative token budget."""
        config_data = {"token_budget": -1000}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.token_budget == 100000  # Should use default
        finally:
            os.unlink(temp_path)
    
    def test_validate_token_budget_wrong_type(self):
        """Test token budget with wrong type."""
        config_data = {"token_budget": "50000"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.token_budget == 100000  # Should use default
        finally:
            os.unlink(temp_path)
    
    def test_validate_weights_valid(self):
        """Test valid scoring weights."""
        config_data = {
            "semantic_weight": 0.8,
            "pagerank_weight": 0.2
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.semantic_weight == 0.8
            assert config.pagerank_weight == 0.2
        finally:
            os.unlink(temp_path)
    
    def test_validate_weights_out_of_range(self):
        """Test weights out of valid range."""
        config_data = {
            "semantic_weight": 1.5,
            "pagerank_weight": -0.2
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.semantic_weight == 0.5  # Should use fallback
            assert config.pagerank_weight == 0.5  # Should use fallback
        finally:
            os.unlink(temp_path)
    
    def test_validate_weights_wrong_type(self):
        """Test weights with wrong type."""
        config_data = {
            "semantic_weight": "0.6",
            "pagerank_weight": "0.4"
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.semantic_weight == 0.5  # Should use fallback
            assert config.pagerank_weight == 0.5  # Should use fallback
        finally:
            os.unlink(temp_path)
    
    def test_validate_patterns_valid(self):
        """Test valid file patterns."""
        config_data = {
            "include_patterns": ["**/*.py", "**/*.js"],
            "exclude_patterns": ["*.min.js", "node_modules/**"]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.include_patterns == ["**/*.py", "**/*.js"]
            assert config.exclude_patterns == ["*.min.js", "node_modules/**"]
        finally:
            os.unlink(temp_path)
    
    def test_validate_patterns_wrong_type(self):
        """Test patterns with wrong type."""
        config_data = {
            "include_patterns": "**/*.py",
            "exclude_patterns": 123
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.include_patterns == []  # Should use empty list
            assert config.exclude_patterns == []  # Should use empty list
        finally:
            os.unlink(temp_path)
    
    def test_validate_patterns_mixed_types(self):
        """Test patterns with mixed types in list."""
        config_data = {
            "include_patterns": ["**/*.py", 123, "**/*.js", None]
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            # Should only include string values
            assert "**/*.py" in config.include_patterns
            assert "**/*.js" in config.include_patterns
            assert 123 not in config.include_patterns
        finally:
            os.unlink(temp_path)
    
    def test_validate_backends_valid(self):
        """Test valid backend configuration."""
        config_data = {
            "backends": {
                "vector_index": "faiss",
                "graph": "networkx",
                "embeddings": "local"
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.backends["vector_index"] == "faiss"
            assert config.backends["graph"] == "networkx"
            assert config.backends["embeddings"] == "local"
        finally:
            os.unlink(temp_path)
    
    def test_validate_backends_invalid_values(self):
        """Test invalid backend values."""
        config_data = {
            "backends": {
                "vector_index": "invalid",
                "graph": "unknown",
                "embeddings": "bad"
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            # Should use "auto" for invalid values
            assert config.backends["vector_index"] == "auto"
            assert config.backends["graph"] == "auto"
            assert config.backends["embeddings"] == "auto"
        finally:
            os.unlink(temp_path)
    
    def test_validate_backends_wrong_type(self):
        """Test backends with wrong type."""
        config_data = {"backends": "invalid"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.backends["vector_index"] == "auto"
            assert config.backends["graph"] == "auto"
            assert config.backends["embeddings"] == "auto"
        finally:
            os.unlink(temp_path)
    
    def test_validate_embeddings_valid(self):
        """Test valid embeddings configuration."""
        config_data = {
            "embeddings": {
                "model": "custom-model",
                "device": "cuda",
                "batch_size": 64,
                "api_provider": "custom",
                "api_key_env": "CUSTOM_API_KEY"
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.embeddings["model"] == "custom-model"
            assert config.embeddings["device"] == "cuda"
            assert config.embeddings["batch_size"] == 64
            assert config.embeddings["api_provider"] == "custom"
            assert config.embeddings["api_key_env"] == "CUSTOM_API_KEY"
        finally:
            os.unlink(temp_path)
    
    def test_validate_embeddings_invalid_device(self):
        """Test invalid embeddings device."""
        config_data = {
            "embeddings": {
                "device": "gpu"  # Invalid, should be "cpu" or "cuda"
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.embeddings["device"] == "cpu"  # Should use default
        finally:
            os.unlink(temp_path)
    
    def test_validate_embeddings_invalid_batch_size(self):
        """Test invalid embeddings batch size."""
        config_data = {
            "embeddings": {
                "batch_size": -10
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.embeddings["batch_size"] == 32  # Should use default
        finally:
            os.unlink(temp_path)
    
    def test_validate_performance_valid(self):
        """Test valid performance configuration."""
        config_data = {
            "performance": {
                "max_workers": 8,
                "cache_embeddings": False,
                "incremental_index": False
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.performance["max_workers"] == 8
            assert config.performance["cache_embeddings"] is False
            assert config.performance["incremental_index"] is False
        finally:
            os.unlink(temp_path)
    
    def test_validate_performance_invalid_max_workers(self):
        """Test invalid max_workers."""
        config_data = {
            "performance": {
                "max_workers": -1
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.performance["max_workers"] == 4  # Should use default
        finally:
            os.unlink(temp_path)


class TestConfigEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_load_with_extra_fields(self):
        """Test loading config with extra unknown fields."""
        config_data = {
            "format": "xml",
            "unknown_field": "value",
            "another_unknown": 123
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "xml"
            # Unknown fields should be ignored
        finally:
            os.unlink(temp_path)
    
    def test_weight_sum_warning(self):
        """Test warning when weights don't sum to 1.0."""
        config_data = {
            "semantic_weight": 0.5,
            "pagerank_weight": 0.3  # Sum is 0.8, not 1.0
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            # Should load but log warning
            assert config.semantic_weight == 0.5
            assert config.pagerank_weight == 0.3
        finally:
            os.unlink(temp_path)
    
    def test_case_insensitive_format(self):
        """Test case-insensitive format handling."""
        config_data = {"format": "XML"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            assert config.format == "xml"  # Should be lowercase
        finally:
            os.unlink(temp_path)
