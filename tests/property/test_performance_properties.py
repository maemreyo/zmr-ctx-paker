"""Property-based tests for performance monitoring and metrics.

These tests validate universal properties that should hold for all valid inputs.
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from context_packer.workflow import index_repository, query_and_pack
from context_packer.config import Config
from context_packer.monitoring import PerformanceTracker, PerformanceMetrics


class TestPerformanceMetricsProperties:
    """Property-based tests for performance metrics tracking."""
    
    def test_property_metrics_reporting_completeness_indexing(self, tmp_path):
        """Property 38: Metrics Reporting Completeness (Indexing).
        
        **Validates: Requirements 13.1, 13.2, 13.3**
        
        For any completed indexing operation, the Context_Packer SHALL report
        total time, files processed, and index size.
        """
        # Create a minimal test repository
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Create a simple Python file
        test_file = repo_path / "test.py"
        test_file.write_text("""
def hello():
    return "world"

class TestClass:
    def method(self):
        pass
""")
        
        # Run indexing
        tracker = index_repository(str(repo_path))
        metrics = tracker.get_metrics()
        
        # Verify all required indexing metrics are reported
        assert metrics.indexing_time > 0, \
            "Indexing time must be reported and positive"
        
        assert metrics.files_processed > 0, \
            "Files processed must be reported and positive"
        
        assert metrics.index_size > 0, \
            "Index size must be reported and positive"
        
        # Verify metrics are accessible via to_dict
        metrics_dict = metrics.to_dict()
        assert "indexing_time" in metrics_dict, \
            "indexing_time must be in metrics dictionary"
        assert "files_processed" in metrics_dict, \
            "files_processed must be in metrics dictionary"
        assert "index_size" in metrics_dict, \
            "index_size must be in metrics dictionary"
    
    def test_property_metrics_reporting_completeness_query(self, tmp_path):
        """Property 38: Metrics Reporting Completeness (Query).
        
        **Validates: Requirements 13.1, 13.2, 13.3**
        
        For any completed query operation, the Context_Packer SHALL report
        query time, files selected, and total tokens.
        """
        # Create a minimal test repository
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Create a simple Python file
        test_file = repo_path / "test.py"
        test_file.write_text("""
def hello():
    return "world"

class TestClass:
    def method(self):
        pass
""")
        
        # Run indexing first
        index_repository(str(repo_path))
        
        # Run query
        config = Config()
        config.format = "xml"
        config.output_path = str(tmp_path / "output")
        
        output_path, tracker = query_and_pack(
            repo_path=str(repo_path),
            query="test function",
            config=config
        )
        
        metrics = tracker.get_metrics()
        
        # Verify all required query metrics are reported
        assert metrics.query_time > 0, \
            "Query time must be reported and positive"
        
        assert metrics.files_selected > 0, \
            "Files selected must be reported and positive"
        
        assert metrics.total_tokens > 0, \
            "Total tokens must be reported and positive"
        
        # Verify metrics are accessible via to_dict
        metrics_dict = metrics.to_dict()
        assert "query_time" in metrics_dict, \
            "query_time must be in metrics dictionary"
        assert "files_selected" in metrics_dict, \
            "files_selected must be in metrics dictionary"
        assert "total_tokens" in metrics_dict, \
            "total_tokens must be in metrics dictionary"
    
    def test_property_memory_tracking_reported(self, tmp_path):
        """Property: Memory usage SHALL be tracked and reported.
        
        **Validates: Requirements 13.3**
        
        For any operation, memory usage should be tracked and reported
        (may be 0 if psutil is not available).
        """
        # Create a minimal test repository
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Create a simple Python file
        test_file = repo_path / "test.py"
        test_file.write_text("def hello(): pass")
        
        # Run indexing
        tracker = index_repository(str(repo_path))
        metrics = tracker.get_metrics()
        
        # Memory usage should be reported (>= 0)
        assert metrics.memory_usage >= 0, \
            "Memory usage must be reported and non-negative"
        
        # Verify it's in the metrics dictionary
        metrics_dict = metrics.to_dict()
        assert "memory_usage" in metrics_dict, \
            "memory_usage must be in metrics dictionary"
    
    def test_property_phase_timings_reported(self, tmp_path):
        """Property: Phase-specific timings SHALL be tracked.
        
        **Validates: Requirements 13.1, 13.2**
        
        For any operation, individual phase timings should be tracked
        and available in the metrics.
        """
        # Create a minimal test repository
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Create a simple Python file
        test_file = repo_path / "test.py"
        test_file.write_text("def hello(): pass")
        
        # Run indexing
        tracker = index_repository(str(repo_path))
        metrics = tracker.get_metrics()
        
        # Phase timings should be reported
        assert isinstance(metrics.phase_timings, dict), \
            "Phase timings must be a dictionary"
        
        # Should have at least some phases tracked
        assert len(metrics.phase_timings) > 0, \
            "At least one phase timing should be tracked"
        
        # All phase timings should be positive
        for phase, duration in metrics.phase_timings.items():
            assert duration > 0, \
                f"Phase {phase} duration must be positive, got {duration}"
    
    def test_property_metrics_format_readable(self, tmp_path):
        """Property: Metrics SHALL be formattable as human-readable string.
        
        **Validates: Requirements 13.1, 13.2**
        
        For any metrics, the format_metrics method should produce
        a readable string representation.
        """
        # Create a minimal test repository
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # Create a simple Python file
        test_file = repo_path / "test.py"
        test_file.write_text("def hello(): pass")
        
        # Run indexing
        tracker = index_repository(str(repo_path))
        
        # Format metrics
        formatted = tracker.format_metrics("indexing")
        
        # Should be a non-empty string
        assert isinstance(formatted, str), \
            "Formatted metrics must be a string"
        assert len(formatted) > 0, \
            "Formatted metrics must not be empty"
        
        # Should contain key information
        assert "Indexing Metrics" in formatted or "indexing" in formatted.lower(), \
            "Formatted metrics should mention indexing"
    
    @given(st.integers(min_value=0, max_value=1000000))
    def test_property_tracker_set_methods_accept_valid_values(self, value):
        """Property: Tracker set methods SHALL accept valid non-negative values.
        
        **Validates: Requirements 13.1, 13.2, 13.3**
        
        For any non-negative integer, the tracker should accept it
        for files_processed, files_selected, total_tokens, etc.
        """
        tracker = PerformanceTracker()
        
        # Should not raise exceptions
        tracker.set_files_processed(value)
        tracker.set_files_selected(value)
        tracker.set_total_tokens(value)
        tracker.set_memory_usage(value)
        
        metrics = tracker.get_metrics()
        
        # Values should be set correctly
        assert metrics.files_processed == value
        assert metrics.files_selected == value
        assert metrics.total_tokens == value
        assert metrics.memory_usage == value
    
    def test_property_metrics_to_dict_completeness(self):
        """Property: Metrics to_dict SHALL include all metric fields.
        
        **Validates: Requirements 13.1, 13.2, 13.3**
        
        For any PerformanceMetrics instance, to_dict should include
        all required metric fields.
        """
        metrics = PerformanceMetrics(
            indexing_time=10.5,
            files_processed=100,
            index_size=1024000,
            query_time=2.3,
            files_selected=50,
            total_tokens=95000,
            memory_usage=512000000,
            phase_timings={"parsing": 5.0, "indexing": 3.5}
        )
        
        metrics_dict = metrics.to_dict()
        
        # All fields should be present
        required_fields = [
            "indexing_time",
            "files_processed",
            "index_size",
            "query_time",
            "files_selected",
            "total_tokens",
            "memory_usage",
            "phase_timings"
        ]
        
        for field in required_fields:
            assert field in metrics_dict, \
                f"Field {field} must be in metrics dictionary"
        
        # Values should match
        assert metrics_dict["indexing_time"] == 10.5
        assert metrics_dict["files_processed"] == 100
        assert metrics_dict["index_size"] == 1024000
        assert metrics_dict["query_time"] == 2.3
        assert metrics_dict["files_selected"] == 50
        assert metrics_dict["total_tokens"] == 95000
        assert metrics_dict["memory_usage"] == 512000000
        assert metrics_dict["phase_timings"] == {"parsing": 5.0, "indexing": 3.5}
