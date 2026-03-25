"""
Configuration management for ws-ctx-engine.

Loads settings from .ws-ctx-engine.yaml with validation and default fallback.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

from ..logger import get_logger


@dataclass
class Config:
    """System configuration loaded from .ws-ctx-engine.yaml"""
    
    # Output settings
    format: str = "zip"  # "xml" | "zip" | "json" | "md"
    token_budget: int = 100000
    output_path: str = "./output"
    
    # Scoring weights
    semantic_weight: float = 0.6
    pagerank_weight: float = 0.4
    
    # File filtering
    include_tests: bool = False
    include_patterns: List[str] = field(default_factory=lambda: [
        "**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx",
        "**/*.java", "**/*.go", "**/*.rs", "**/*.c", "**/*.cpp", "**/*.h"
    ])
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.min.js", "*.min.css", "node_modules/**", "__pycache__/**",
        ".git/**", "dist/**", "build/**", "*.egg-info/**",
        ".venv/**", "venv/**", ".pytest_cache/**", "htmlcov/**"
    ])
    
    # Backend selection
    backends: Dict[str, str] = field(default_factory=lambda: {
        "vector_index": "auto",  # auto | leann | faiss
        "graph": "auto",         # auto | igraph | networkx
        "embeddings": "auto"     # auto | local | api
    })
    
    # Embeddings config
    embeddings: Dict[str, Any] = field(default_factory=lambda: {
        "model": "all-MiniLM-L6-v2",
        "device": "cpu",
        "batch_size": 32,
        "api_provider": "openai",
        "api_key_env": "OPENAI_API_KEY"
    })
    
    # Performance tuning
    performance: Dict[str, Any] = field(default_factory=lambda: {
        "max_workers": 4,
        "cache_embeddings": True,
        "incremental_index": True
    })
    
    @classmethod
    def load(cls, path: str = ".ws-ctx-engine.yaml") -> 'Config':
        """
        Load configuration from YAML file with validation.
        
        Args:
            path: Path to configuration file (default: .ws-ctx-engine.yaml)
            
        Returns:
            Config instance with validated settings
        """
        logger = get_logger()
        
        # Use defaults if file doesn't exist
        if not os.path.exists(path):
            logger.info(f"Configuration file not found: {path}, using defaults")
            return cls()
        
        # Load YAML file
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            logger.info("Using default configuration")
            return cls()
        except Exception as e:
            logger.error(f"Failed to read configuration file: {e}")
            logger.info("Using default configuration")
            return cls()
        
        # Handle empty file
        if data is None:
            logger.info("Configuration file is empty, using defaults")
            return cls()
        
        # Create config with validation
        config = cls()
        
        # Validate and set output settings
        if "format" in data:
            config.format = cls._validate_format(data["format"], logger)
        
        if "token_budget" in data:
            config.token_budget = cls._validate_token_budget(data["token_budget"], logger)
        
        if "output_path" in data:
            config.output_path = str(data["output_path"])
        
        # Validate and set scoring weights
        if "semantic_weight" in data:
            config.semantic_weight = cls._validate_weight(
                data["semantic_weight"], "semantic_weight", logger
            )
        
        if "pagerank_weight" in data:
            config.pagerank_weight = cls._validate_weight(
                data["pagerank_weight"], "pagerank_weight", logger
            )
        
        # Validate weight sum
        cls._validate_weight_sum(config.semantic_weight, config.pagerank_weight, logger)
        
        # Set file filtering
        if "include_tests" in data:
            config.include_tests = bool(data["include_tests"])
        
        if "include_patterns" in data:
            config.include_patterns = cls._validate_patterns(
                data["include_patterns"], "include_patterns", logger
            )
        
        if "exclude_patterns" in data:
            config.exclude_patterns = cls._validate_patterns(
                data["exclude_patterns"], "exclude_patterns", logger
            )
        
        # Set backend selection
        if "backends" in data:
            config.backends = cls._validate_backends(data["backends"], logger)
        
        # Set embeddings config
        if "embeddings" in data:
            config.embeddings = cls._validate_embeddings(data["embeddings"], logger)
        
        # Set performance tuning
        if "performance" in data:
            config.performance = cls._validate_performance(data["performance"], logger)
        
        logger.info(f"Configuration loaded successfully from {path}")
        return config
    
    @staticmethod
    def _validate_format(value: Any, logger: Any) -> str:
        """Validate output format."""
        if not isinstance(value, str):
            logger.error(f"Invalid format type: {type(value).__name__}, expected str")
            return "zip"
        
        value = value.lower()
        if value not in ["xml", "zip", "json", "md"]:
            logger.error(f"Invalid format: {value}, must be 'xml', 'zip', 'json', or 'md'")
            return "zip"
        
        return value
    
    @staticmethod
    def _validate_token_budget(value: Any, logger: Any) -> int:
        """Validate token budget."""
        if not isinstance(value, int):
            logger.error(f"Invalid token_budget type: {type(value).__name__}, expected int")
            return 100000
        
        if value <= 0:
            logger.error(f"Invalid token_budget: {value}, must be positive")
            return 100000
        
        return value
    
    @staticmethod
    def _validate_weight(value: Any, name: str, logger: Any) -> float:
        """Validate scoring weight."""
        if not isinstance(value, (int, float)):
            logger.error(f"Invalid {name} type: {type(value).__name__}, expected float")
            return 0.5
        
        value = float(value)
        if not 0.0 <= value <= 1.0:
            logger.error(f"Invalid {name}: {value}, must be between 0.0 and 1.0")
            return 0.5
        
        return value
    
    @staticmethod
    def _validate_weight_sum(semantic: float, pagerank: float, logger: Any) -> None:
        """Validate that weights sum to approximately 1.0."""
        total = semantic + pagerank
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            logger.warning(
                f"Scoring weights sum to {total:.2f}, expected 1.0. "
                f"Scores may not be normalized correctly."
            )
    
    @staticmethod
    def _validate_patterns(value: Any, name: str, logger: Any) -> List[str]:
        """Validate file patterns."""
        if not isinstance(value, list):
            logger.error(f"Invalid {name} type: {type(value).__name__}, expected list")
            return []
        
        patterns = []
        for item in value:
            if isinstance(item, str):
                patterns.append(item)
            else:
                logger.warning(f"Skipping non-string pattern in {name}: {item}")
        
        return patterns
    
    @staticmethod
    def _validate_backends(value: Any, logger: Any) -> Dict[str, str]:
        """Validate backend selection."""
        if not isinstance(value, dict):
            logger.error(f"Invalid backends type: {type(value).__name__}, expected dict")
            return {
                "vector_index": "auto",
                "graph": "auto",
                "embeddings": "auto"
            }
        
        valid_backends = {
            "vector_index": ["auto", "native-leann", "leann", "faiss"],
            "graph": ["auto", "igraph", "networkx"],
            "embeddings": ["auto", "local", "api"]
        }
        
        backends = {}
        for key, valid_values in valid_backends.items():
            if key in value:
                backend_value = value[key]
                if isinstance(backend_value, str) and backend_value in valid_values:
                    backends[key] = backend_value
                else:
                    logger.error(
                        f"Invalid backends.{key}: {backend_value}, "
                        f"must be one of {valid_values}"
                    )
                    backends[key] = "auto"
            else:
                backends[key] = "auto"
        
        return backends
    
    @staticmethod
    def _validate_embeddings(value: Any, logger: Any) -> Dict[str, Any]:
        """Validate embeddings configuration."""
        if not isinstance(value, dict):
            logger.error(f"Invalid embeddings type: {type(value).__name__}, expected dict")
            return {
                "model": "all-MiniLM-L6-v2",
                "device": "cpu",
                "batch_size": 32,
                "api_provider": "openai",
                "api_key_env": "OPENAI_API_KEY"
            }
        
        embeddings = {
            "model": "all-MiniLM-L6-v2",
            "device": "cpu",
            "batch_size": 32,
            "api_provider": "openai",
            "api_key_env": "OPENAI_API_KEY"
        }
        
        # Validate model
        if "model" in value and isinstance(value["model"], str):
            embeddings["model"] = value["model"]
        
        # Validate device
        if "device" in value:
            device = value["device"]
            if isinstance(device, str) and device in ["cpu", "cuda"]:
                embeddings["device"] = device
            else:
                logger.error(f"Invalid embeddings.device: {device}, must be 'cpu' or 'cuda'")
        
        # Validate batch_size
        if "batch_size" in value:
            batch_size = value["batch_size"]
            if isinstance(batch_size, int) and batch_size > 0:
                embeddings["batch_size"] = batch_size
            else:
                logger.error(f"Invalid embeddings.batch_size: {batch_size}, must be positive int")
        
        # Validate api_provider
        if "api_provider" in value and isinstance(value["api_provider"], str):
            embeddings["api_provider"] = value["api_provider"]
        
        # Validate api_key_env
        if "api_key_env" in value and isinstance(value["api_key_env"], str):
            embeddings["api_key_env"] = value["api_key_env"]
        
        return embeddings
    
    @staticmethod
    def _validate_performance(value: Any, logger: Any) -> Dict[str, Any]:
        """Validate performance configuration."""
        if not isinstance(value, dict):
            logger.error(f"Invalid performance type: {type(value).__name__}, expected dict")
            return {
                "max_workers": 4,
                "cache_embeddings": True,
                "incremental_index": True
            }
        
        performance = {
            "max_workers": 4,
            "cache_embeddings": True,
            "incremental_index": True
        }
        
        # Validate max_workers
        if "max_workers" in value:
            max_workers = value["max_workers"]
            if isinstance(max_workers, int) and max_workers > 0:
                performance["max_workers"] = max_workers
            else:
                logger.error(f"Invalid performance.max_workers: {max_workers}, must be positive int")
        
        # Validate cache_embeddings
        if "cache_embeddings" in value:
            performance["cache_embeddings"] = bool(value["cache_embeddings"])
        
        # Validate incremental_index
        if "incremental_index" in value:
            performance["incremental_index"] = bool(value["incremental_index"])
        
        return performance
