"""Performance benchmark tests for Context Packer.

These tests verify that the system meets performance targets for indexing
and querying operations with large repositories.

Requirements: 13.4, 13.5, 13.6, 13.7
"""

import os
import time
from pathlib import Path

import pytest

from context_packer.indexer import index_repository
from context_packer.query import query_and_pack
from context_packer.config import Config


# Mark all tests in this module as benchmarks
pytestmark = pytest.mark.benchmark


@pytest.fixture
def benchmark_repo_1k(tmp_path):
    """Create a benchmark repository with ~1000 files for testing.
    
    This creates a smaller repository for faster testing while still
    validating performance characteristics.
    """
    repo_path = tmp_path / "benchmark_repo_1k"
    repo_path.mkdir()
    
    # Create 1000 Python files with realistic content
    for i in range(1000):
        module_dir = repo_path / f"module_{i // 100}"
        module_dir.mkdir(exist_ok=True)
        
        file_path = module_dir / f"file_{i}.py"
        file_path.write_text(f"""
\"\"\"Module {i} for benchmark testing.\"\"\"

import os
import sys
from typing import List, Dict, Optional

class Class{i}:
    \"\"\"Test class {i}.\"\"\"
    
    def __init__(self, value: int):
        self.value = value
        self.data = []
    
    def method_{i}(self, param: str) -> str:
        \"\"\"Process parameter and return result.\"\"\"
        result = f"{{param}}_{{self.value}}"
        self.data.append(result)
        return result
    
    def compute(self, x: int, y: int) -> int:
        \"\"\"Compute something with x and y.\"\"\"
        return (x + y) * self.value

def function_{i}(arg1: str, arg2: int) -> Dict[str, int]:
    \"\"\"Test function {i}.\"\"\"
    obj = Class{i}(arg2)
    result = obj.method_{i}(arg1)
    return {{"result": len(result), "value": arg2}}

def helper_{i}(data: List[int]) -> int:
    \"\"\"Helper function {i}.\"\"\"
    return sum(data) + {i}

# Constants
CONSTANT_{i} = {i}
CONFIG_{i} = {{"key": "value_{i}", "number": {i}}}
""")
    
    return str(repo_path)


@pytest.fixture
def benchmark_repo_10k(tmp_path):
    """Create a benchmark repository with ~10,000 files for testing.
    
    This creates a large repository to test performance at scale.
    Note: This fixture is expensive and should only be used for
    actual performance benchmarks.
    """
    repo_path = tmp_path / "benchmark_repo_10k"
    repo_path.mkdir()
    
    # Create 10,000 Python files with realistic content
    for i in range(10000):
        module_dir = repo_path / f"module_{i // 100}"
        module_dir.mkdir(exist_ok=True)
        
        file_path = module_dir / f"file_{i}.py"
        file_path.write_text(f"""
\"\"\"Module {i} for benchmark testing.\"\"\"

import os
import sys
from typing import List, Dict, Optional

class Class{i}:
    \"\"\"Test class {i}.\"\"\"
    
    def __init__(self, value: int):
        self.value = value
        self.data = []
    
    def method_{i}(self, param: str) -> str:
        \"\"\"Process parameter and return result.\"\"\"
        result = f"{{param}}_{{self.value}}"
        self.data.append(result)
        return result
    
    def compute(self, x: int, y: int) -> int:
        \"\"\"Compute something with x and y.\"\"\"
        return (x + y) * self.value

def function_{i}(arg1: str, arg2: int) -> Dict[str, int]:
    \"\"\"Test function {i}.\"\"\"
    obj = Class{i}(arg2)
    result = obj.method_{i}(arg1)
    return {{"result": len(result), "value": arg2}}

def helper_{i}(data: List[int]) -> int:
    \"\"\"Helper function {i}.\"\"\"
    return sum(data) + {i}

# Constants
CONSTANT_{i} = {i}
CONFIG_{i} = {{"key": "value_{i}", "number": {i}}}
""")
    
    return str(repo_path)


class TestIndexingPerformance:
    """Performance benchmarks for indexing operations."""
    
    def test_indexing_1k_files_baseline(self, benchmark_repo_1k):
        """Baseline test: Verify indexing works correctly on 1k files.
        
        This test validates that indexing completes successfully on a
        smaller repository before running the full 10k benchmark.
        
        Requirements: 13.1, 13.4
        """
        start_time = time.time()
        
        # Run indexing
        tracker = index_repository(benchmark_repo_1k)
        
        duration = time.time() - start_time
        metrics = tracker.get_metrics()
        
        # Verify indexing completed
        assert metrics.files_processed > 0, \
            "Should have processed files"
        assert metrics.indexing_time > 0, \
            "Should have recorded indexing time"
        assert metrics.index_size > 0, \
            "Should have created index files"
        
        # Log performance for reference
        print(f"\n1k files indexing performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Files processed: {metrics.files_processed}")
        print(f"  Index size: {metrics.index_size / (1024*1024):.2f} MB")
        print(f"  Files/second: {metrics.files_processed / duration:.2f}")
    
    @pytest.mark.slow
    def test_indexing_10k_files_primary_backend(self, benchmark_repo_10k):
        """Benchmark: Indexing SHALL complete within 5 minutes for 10k files (primary).
        
        Requirements: 13.4
        
        When using primary backends (LEANN + igraph), indexing should complete
        within 5 minutes (300 seconds) for a 10,000 file repository.
        """
        start_time = time.time()
        
        # Run indexing with primary backends
        config = Config()
        config.backends = {
            "vector_index": "auto",  # Will try LEANN first
            "graph": "auto",  # Will try igraph first
            "embeddings": "local"
        }
        
        tracker = index_repository(benchmark_repo_10k, config=config)
        
        duration = time.time() - start_time
        metrics = tracker.get_metrics()
        
        # Verify indexing completed
        assert metrics.files_processed > 0, \
            "Should have processed files"
        
        # Log performance
        print(f"\n10k files indexing performance (primary backends):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Files processed: {metrics.files_processed}")
        print(f"  Index size: {metrics.index_size / (1024*1024):.2f} MB")
        print(f"  Files/second: {metrics.files_processed / duration:.2f}")
        print(f"  Backend: {config.backends}")
        
        # Primary backend target: 5 minutes (300 seconds)
        assert duration < 300, \
            f"Indexing took {duration:.2f}s, expected <300s for primary backends"
    
    @pytest.mark.slow
    def test_indexing_10k_files_fallback_backend(self, benchmark_repo_10k):
        """Benchmark: Indexing SHALL complete within 10 minutes for 10k files (fallback).
        
        Requirements: 13.5
        
        When using fallback backends (FAISS + NetworkX), indexing should complete
        within 10 minutes (600 seconds) for a 10,000 file repository.
        """
        start_time = time.time()
        
        # Run indexing with fallback backends
        config = Config()
        config.backends = {
            "vector_index": "faiss",  # Force FAISS fallback
            "graph": "networkx",  # Force NetworkX fallback
            "embeddings": "local"
        }
        
        tracker = index_repository(benchmark_repo_10k, config=config)
        
        duration = time.time() - start_time
        metrics = tracker.get_metrics()
        
        # Verify indexing completed
        assert metrics.files_processed > 0, \
            "Should have processed files"
        
        # Log performance
        print(f"\n10k files indexing performance (fallback backends):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Files processed: {metrics.files_processed}")
        print(f"  Index size: {metrics.index_size / (1024*1024):.2f} MB")
        print(f"  Files/second: {metrics.files_processed / duration:.2f}")
        print(f"  Backend: {config.backends}")
        
        # Fallback backend target: 10 minutes (600 seconds)
        assert duration < 600, \
            f"Indexing took {duration:.2f}s, expected <600s for fallback backends"


class TestQueryPerformance:
    """Performance benchmarks for query operations."""
    
    def test_query_1k_files_baseline(self, benchmark_repo_1k, tmp_path):
        """Baseline test: Verify querying works correctly on 1k files.
        
        This test validates that querying completes successfully on a
        smaller repository before running the full 10k benchmark.
        
        Requirements: 13.2, 13.6
        """
        # Index first
        index_repository(benchmark_repo_1k)
        
        # Run query
        config = Config()
        config.format = "xml"
        config.output_path = str(tmp_path / "output")
        
        start_time = time.time()
        
        output_path, tracker = query_and_pack(
            repo_path=benchmark_repo_1k,
            query="test function class",
            config=config
        )
        
        duration = time.time() - start_time
        metrics = tracker.get_metrics()
        
        # Verify query completed
        assert metrics.files_selected > 0, \
            "Should have selected files"
        assert metrics.query_time > 0, \
            "Should have recorded query time"
        assert metrics.total_tokens > 0, \
            "Should have counted tokens"
        
        # Log performance for reference
        print(f"\n1k files query performance:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Files selected: {metrics.files_selected}")
        print(f"  Total tokens: {metrics.total_tokens}")
    
    @pytest.mark.slow
    def test_query_10k_files_primary_backend(self, benchmark_repo_10k, tmp_path):
        """Benchmark: Querying SHALL complete within 10 seconds (primary).
        
        Requirements: 13.6
        
        When using primary backends, querying should complete within
        10 seconds for a 10,000 file repository.
        """
        # Index first with primary backends
        config = Config()
        config.backends = {
            "vector_index": "auto",
            "graph": "auto",
            "embeddings": "local"
        }
        index_repository(benchmark_repo_10k, config=config)
        
        # Run query
        config.format = "xml"
        config.output_path = str(tmp_path / "output")
        
        start_time = time.time()
        
        output_path, tracker = query_and_pack(
            repo_path=benchmark_repo_10k,
            query="test function class method",
            config=config
        )
        
        duration = time.time() - start_time
        metrics = tracker.get_metrics()
        
        # Verify query completed
        assert metrics.files_selected > 0, \
            "Should have selected files"
        
        # Log performance
        print(f"\n10k files query performance (primary backends):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Files selected: {metrics.files_selected}")
        print(f"  Total tokens: {metrics.total_tokens}")
        print(f"  Query time: {metrics.query_time:.2f}s")
        
        # Primary backend target: 10 seconds
        assert duration < 10, \
            f"Query took {duration:.2f}s, expected <10s for primary backends"
    
    @pytest.mark.slow
    def test_query_10k_files_fallback_backend(self, benchmark_repo_10k, tmp_path):
        """Benchmark: Querying SHALL complete within 15 seconds (fallback).
        
        Requirements: 13.7
        
        When using fallback backends, querying should complete within
        15 seconds for a 10,000 file repository.
        """
        # Index first with fallback backends
        config = Config()
        config.backends = {
            "vector_index": "faiss",
            "graph": "networkx",
            "embeddings": "local"
        }
        index_repository(benchmark_repo_10k, config=config)
        
        # Run query
        config.format = "xml"
        config.output_path = str(tmp_path / "output")
        
        start_time = time.time()
        
        output_path, tracker = query_and_pack(
            repo_path=benchmark_repo_10k,
            query="test function class method",
            config=config
        )
        
        duration = time.time() - start_time
        metrics = tracker.get_metrics()
        
        # Verify query completed
        assert metrics.files_selected > 0, \
            "Should have selected files"
        
        # Log performance
        print(f"\n10k files query performance (fallback backends):")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Files selected: {metrics.files_selected}")
        print(f"  Total tokens: {metrics.total_tokens}")
        print(f"  Query time: {metrics.query_time:.2f}s")
        
        # Fallback backend target: 15 seconds
        assert duration < 15, \
            f"Query took {duration:.2f}s, expected <15s for fallback backends"


class TestMemoryUsage:
    """Performance benchmarks for memory usage."""
    
    @pytest.mark.slow
    def test_memory_usage_tracked_during_indexing(self, benchmark_repo_1k):
        """Verify that memory usage is tracked during indexing.
        
        Requirements: 13.3
        
        Memory usage should be tracked and reported during indexing operations.
        """
        tracker = index_repository(benchmark_repo_1k)
        metrics = tracker.get_metrics()
        
        # Memory usage should be tracked (may be 0 if psutil not available)
        assert metrics.memory_usage >= 0, \
            "Memory usage should be non-negative"
        
        # If psutil is available, memory usage should be positive
        try:
            import psutil
            assert metrics.memory_usage > 0, \
                "Memory usage should be positive when psutil is available"
            
            # Log memory usage
            print(f"\nMemory usage during indexing:")
            print(f"  Peak memory: {metrics.memory_usage / (1024*1024):.2f} MB")
        except ImportError:
            print("\npsutil not available, memory tracking skipped")
    
    @pytest.mark.slow
    def test_memory_usage_tracked_during_query(self, benchmark_repo_1k, tmp_path):
        """Verify that memory usage is tracked during query.
        
        Requirements: 13.3
        
        Memory usage should be tracked and reported during query operations.
        """
        # Index first
        index_repository(benchmark_repo_1k)
        
        # Run query
        config = Config()
        config.format = "xml"
        config.output_path = str(tmp_path / "output")
        
        output_path, tracker = query_and_pack(
            repo_path=benchmark_repo_1k,
            query="test function",
            config=config
        )
        
        metrics = tracker.get_metrics()
        
        # Memory usage should be tracked (may be 0 if psutil not available)
        assert metrics.memory_usage >= 0, \
            "Memory usage should be non-negative"
        
        # If psutil is available, memory usage should be positive
        try:
            import psutil
            assert metrics.memory_usage > 0, \
                "Memory usage should be positive when psutil is available"
            
            # Log memory usage
            print(f"\nMemory usage during query:")
            print(f"  Peak memory: {metrics.memory_usage / (1024*1024):.2f} MB")
        except ImportError:
            print("\npsutil not available, memory tracking skipped")
