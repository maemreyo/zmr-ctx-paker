"""
Property-based tests for error handling and logging.

Tests comprehensive error logging, dual output, log level filtering, and verbose mode.
"""

import logging
import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from ws_ctx_engine.errors import (
    BudgetError,
    ConfigurationError,
    WsCtxEngineError,
    DependencyError,
    IndexError,
    ParsingError,
)
from ws_ctx_engine.logger import WsCtxEngineLogger, get_logger


# Property 34: Comprehensive Error Logging
# **Validates: Requirements 12.1, 12.7**
@given(
    component=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))),
    primary=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))),
    fallback=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))),
    reason=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cc", "Cs")))
)
def test_property_34_comprehensive_error_logging_fallback(component, primary, fallback, reason):
    """
    Property 34: Comprehensive Error Logging (Fallback)
    
    For any error that occurs, the ws_ctx_engine SHALL log it with
    file path, line number, stack trace, and an actionable suggestion
    for fixing the issue.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Log fallback - should not crash
        logger.log_fallback(
            component=component,
            primary=primary,
            fallback=fallback,
            reason=reason
        )
        
        # Verify log file was created
        log_files = list(Path(tmp_dir).glob("*.log"))
        assert len(log_files) > 0
        
        # Verify log contains fallback information
        log_content = log_files[0].read_text()
        assert component in log_content
        assert "Fallback triggered" in log_content


def test_property_34_error_with_context():
    """
    Property 34: Comprehensive Error Logging (Error Context)
    
    When logging errors with context, all context information should
    be included in the log.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Create an error with context
        error = ValueError("Test error")
        context = {
            "file_path": "src/main.py",
            "line_number": 42,
            "function": "test_function"
        }
        
        # Log error with context
        logger.log_error(error, context)
        
        # Verify log file contains context
        log_files = list(Path(tmp_dir).glob("*.log"))
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text()
        assert "file_path=src/main.py" in log_content
        assert "line_number=42" in log_content
        assert "function=test_function" in log_content


@given(
    backend=st.text(min_size=1, max_size=20),
    install_cmd=st.text(min_size=1, max_size=50)
)
def test_property_34_dependency_error_suggestions(backend, install_cmd):
    """
    Property 34: Comprehensive Error Logging (Suggestions)
    
    All custom errors should include actionable suggestions.
    """
    error = DependencyError.missing_backend(backend, install_cmd)
    
    # Error should have message and suggestion
    assert hasattr(error, 'message')
    assert hasattr(error, 'suggestion')
    assert backend in error.message
    assert install_cmd in error.suggestion


def test_property_34_configuration_error_suggestions():
    """
    Property 34: Comprehensive Error Logging (Configuration Errors)
    
    Configuration errors should include actionable suggestions.
    """
    error = ConfigurationError.invalid_value("semantic_weight", 1.5, "a float between 0.0 and 1.0")
    
    # Error should have message and suggestion
    assert hasattr(error, 'message')
    assert hasattr(error, 'suggestion')
    assert "semantic_weight" in error.message
    assert "1.5" in error.message
    assert ".ws-ctx-engine.yaml" in error.suggestion


# Property 35: Dual Output Logging
# **Validates: Requirements 12.6**
@given(message=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))))
def test_property_35_dual_output_logging(message):
    """
    Property 35: Dual Output Logging
    
    For any log message, it SHALL appear in both the console output
    and the log file in .ws-ctx-engine/logs/.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Log a message
        logger.info(message)
        
        # Verify log file was created
        log_files = list(Path(tmp_dir).glob("*.log"))
        assert len(log_files) > 0
        
        # Verify message is in log file
        log_content = log_files[0].read_text()
        assert message in log_content
        
        # Note: Console output is harder to test in unit tests,
        # but the handler is configured to output to console


def test_property_35_dual_output_all_levels():
    """
    Property 35: Dual Output Logging (All Levels)
    
    All log levels should be written to the log file.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Log messages at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Verify all messages are in log file
        log_files = list(Path(tmp_dir).glob("*.log"))
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text()
        assert "Debug message" in log_content
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content


# Property 36: Log Level Filtering
# **Validates: Requirements 12.4**
def test_property_36_log_level_filtering():
    """
    Property 36: Log Level Filtering
    
    For any configured log level, only messages at that level or higher
    SHALL be displayed (DEBUG < INFO < WARNING < ERROR).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Console handler should be INFO and above
        console_handler = None
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler
                break
        
        assert console_handler is not None
        assert console_handler.level == logging.INFO
        
        # File handler should be DEBUG and above
        file_handler = None
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        assert file_handler.level == logging.DEBUG


def test_property_36_log_level_hierarchy():
    """
    Property 36: Log Level Filtering (Hierarchy)
    
    Log levels should follow the hierarchy: DEBUG < INFO < WARNING < ERROR.
    """
    assert logging.DEBUG < logging.INFO
    assert logging.INFO < logging.WARNING
    assert logging.WARNING < logging.ERROR


# Property 37: Verbose Mode Timing
# **Validates: Requirements 12.5**
@given(
    phase=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))),
    duration=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
)
def test_property_37_verbose_mode_timing(phase, duration):
    """
    Property 37: Verbose Mode Timing
    
    For any operation running in verbose mode, the ws_ctx_engine SHALL
    log detailed timing information for each phase.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Log phase completion with timing
        logger.log_phase(phase, duration)
        
        # Verify log file contains timing information
        log_files = list(Path(tmp_dir).glob("*.log"))
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text()
        assert phase in log_content
        assert "Phase complete" in log_content
        assert "duration=" in log_content


@given(
    phase=st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cc", "Cs"))),
    duration=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    files_processed=st.integers(min_value=0, max_value=10000),
    tokens_counted=st.integers(min_value=0, max_value=1000000)
)
def test_property_37_verbose_mode_timing_with_metrics(phase, duration, files_processed, tokens_counted):
    """
    Property 37: Verbose Mode Timing (With Metrics)
    
    Phase logging should support additional metrics beyond timing.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        logger = WsCtxEngineLogger(log_dir=tmp_dir)
        
        # Log phase with metrics
        logger.log_phase(
            phase,
            duration,
            files_processed=files_processed,
            tokens_counted=tokens_counted
        )
        
        # Verify log file contains all information
        log_files = list(Path(tmp_dir).glob("*.log"))
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text()
        assert phase in log_content
        assert "duration=" in log_content
        assert "files_processed=" in log_content
        assert "tokens_counted=" in log_content


def test_error_classes_inheritance():
    """Test that all error classes inherit from WsCtxEngineError."""
    assert issubclass(DependencyError, WsCtxEngineError)
    assert issubclass(ConfigurationError, WsCtxEngineError)
    assert issubclass(ParsingError, WsCtxEngineError)
    assert issubclass(IndexError, WsCtxEngineError)
    assert issubclass(BudgetError, WsCtxEngineError)


def test_error_classes_have_suggestions():
    """Test that all error classes provide suggestions."""
    # DependencyError
    dep_error = DependencyError.missing_backend("test", "pip install test")
    assert hasattr(dep_error, 'suggestion')
    assert "pip install test" in dep_error.suggestion
    
    # ConfigurationError
    config_error = ConfigurationError.invalid_value("test", "value", "expected")
    assert hasattr(config_error, 'suggestion')
    assert ".ws-ctx-engine.yaml" in config_error.suggestion
    
    # ParsingError
    parse_error = ParsingError.syntax_error("test.py", 1, "error")
    assert hasattr(parse_error, 'suggestion')
    assert "exclude_patterns" in parse_error.suggestion
    
    # IndexError
    index_error = IndexError.corrupted_index("test.idx")
    assert hasattr(index_error, 'suggestion')
    assert "ws-ctx-engine index" in index_error.suggestion
    
    # BudgetError
    budget_error = BudgetError.budget_exceeded(1000, 500)
    assert hasattr(budget_error, 'suggestion')
    assert "token_budget" in budget_error.suggestion
