"""
Property-based tests for configuration management.

Tests configuration loading, validation, and error handling.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, strategies as st

from ws_ctx_engine.config import Config


# Strategy for valid configuration dictionaries
@st.composite
def valid_config_dict(draw):
    """Generate valid configuration dictionaries."""
    return {
        "format": draw(st.sampled_from(["xml", "zip"])),
        "token_budget": draw(st.integers(min_value=1000, max_value=1000000)),
        "output_path": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="./_ -"))),
        "semantic_weight": draw(st.floats(min_value=0.0, max_value=1.0)),
        "pagerank_weight": draw(st.floats(min_value=0.0, max_value=1.0)),
        "include_tests": draw(st.booleans()),
        "include_patterns": draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5)),
        "exclude_patterns": draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5)),
        "backends": {
            "vector_index": draw(st.sampled_from(["auto", "leann", "faiss"])),
            "graph": draw(st.sampled_from(["auto", "igraph", "networkx"])),
            "embeddings": draw(st.sampled_from(["auto", "local", "api"]))
        },
        "embeddings": {
            "model": draw(st.text(min_size=1, max_size=50)),
            "device": draw(st.sampled_from(["cpu", "cuda"])),
            "batch_size": draw(st.integers(min_value=1, max_value=128)),
            "api_provider": draw(st.text(min_size=1, max_size=20)),
            "api_key_env": draw(st.text(min_size=1, max_size=50))
        },
        "performance": {
            "max_workers": draw(st.integers(min_value=1, max_value=16)),
            "cache_embeddings": draw(st.booleans()),
            "incremental_index": draw(st.booleans())
        }
    }


# Property 22: Configuration Loading
# **Validates: Requirements 8.1, 8.3, 8.4, 8.5, 8.6, 8.7**
@given(config_data=valid_config_dict())
def test_property_22_configuration_loading(config_data):
    """
    Property 22: Configuration Loading
    
    For any valid .ws-ctx-engine.yaml file, the ws_ctx_engine SHALL load
    and apply all configuration values (format, token_budget, weights,
    patterns, backends).
    """
    # Create temporary YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        # Load configuration
        config = Config.load(temp_path)
        
        # Verify all values are loaded correctly
        assert config.format == config_data["format"]
        assert config.token_budget == config_data["token_budget"]
        assert config.output_path == config_data["output_path"]
        
        # Weights should be loaded (may be adjusted if sum != 1.0)
        assert 0.0 <= config.semantic_weight <= 1.0
        assert 0.0 <= config.pagerank_weight <= 1.0
        
        assert config.include_tests == config_data["include_tests"]
        assert config.include_patterns == config_data["include_patterns"]
        assert config.exclude_patterns == config_data["exclude_patterns"]
        
        # Backend selection
        assert config.backends["vector_index"] == config_data["backends"]["vector_index"]
        assert config.backends["graph"] == config_data["backends"]["graph"]
        assert config.backends["embeddings"] == config_data["backends"]["embeddings"]
        
        # Embeddings config
        assert config.embeddings["model"] == config_data["embeddings"]["model"]
        assert config.embeddings["device"] == config_data["embeddings"]["device"]
        assert config.embeddings["batch_size"] == config_data["embeddings"]["batch_size"]
        assert config.embeddings["api_provider"] == config_data["embeddings"]["api_provider"]
        assert config.embeddings["api_key_env"] == config_data["embeddings"]["api_key_env"]
        
        # Performance config
        assert config.performance["max_workers"] == config_data["performance"]["max_workers"]
        assert config.performance["cache_embeddings"] == config_data["performance"]["cache_embeddings"]
        assert config.performance["incremental_index"] == config_data["performance"]["incremental_index"]
        
    finally:
        # Clean up
        os.unlink(temp_path)


# Property 23: Configuration Error Handling
# **Validates: Requirements 8.8**
@given(
    invalid_format=st.one_of(st.integers(), st.floats(), st.lists(st.text()), st.text().filter(lambda x: x.lower() not in ["xml", "zip"])),
    invalid_budget=st.one_of(st.text(), st.floats(), st.integers(max_value=0)),
    invalid_weight=st.one_of(st.text(), st.floats(min_value=-10.0, max_value=-0.1), st.floats(min_value=1.1, max_value=10.0))
)
def test_property_23_configuration_error_handling(invalid_format, invalid_budget, invalid_weight):
    """
    Property 23: Configuration Error Handling
    
    For any invalid configuration value, the ws_ctx_engine SHALL log an error
    and use the corresponding default value instead of crashing.
    """
    # Create configuration with invalid values
    config_data = {
        "format": invalid_format,
        "token_budget": invalid_budget,
        "semantic_weight": invalid_weight,
        "pagerank_weight": invalid_weight
    }
    
    # Create temporary YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        # Load configuration - should not crash
        config = Config.load(temp_path)
        
        # Verify defaults are used for invalid values
        assert config.format in ["xml", "zip"]  # Default: "zip"
        assert config.token_budget > 0  # Default: 100000
        assert 0.0 <= config.semantic_weight <= 1.0  # Default: 0.5 when invalid
        assert 0.0 <= config.pagerank_weight <= 1.0  # Default: 0.5 when invalid
        
        # Config object should be valid
        assert isinstance(config, Config)
        
    finally:
        # Clean up
        os.unlink(temp_path)


def test_property_23_missing_config_file():
    """
    Property 23: Configuration Error Handling (missing file case)
    
    When configuration file is missing, the ws_ctx_engine SHALL use
    default configuration without crashing.
    """
    # Try to load non-existent file
    config = Config.load("/nonexistent/path/to/config.yaml")
    
    # Should return default config
    assert isinstance(config, Config)
    assert config.format == "zip"
    assert config.token_budget == 100000
    assert config.semantic_weight == 0.6
    assert config.pagerank_weight == 0.4


def test_property_23_empty_config_file():
    """
    Property 23: Configuration Error Handling (empty file case)
    
    When configuration file is empty, the ws_ctx_engine SHALL use
    default configuration without crashing.
    """
    # Create empty YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("")
        temp_path = f.name
    
    try:
        # Load configuration
        config = Config.load(temp_path)
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.format == "zip"
        assert config.token_budget == 100000
        
    finally:
        # Clean up
        os.unlink(temp_path)


def test_property_23_malformed_yaml():
    """
    Property 23: Configuration Error Handling (malformed YAML case)
    
    When configuration file contains malformed YAML, the ws_ctx_engine
    SHALL use default configuration without crashing.
    """
    # Create malformed YAML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("format: xml\n  invalid indentation\ntoken_budget: [unclosed")
        temp_path = f.name
    
    try:
        # Load configuration - should not crash
        config = Config.load(temp_path)
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.format == "zip"
        assert config.token_budget == 100000
        
    finally:
        # Clean up
        os.unlink(temp_path)
