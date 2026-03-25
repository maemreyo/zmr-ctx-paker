"""
Unit tests for WsCtxEngineLogger.
"""

import logging
import os
import tempfile
from pathlib import Path

import pytest

from ws_ctx_engine.logger import WsCtxEngineLogger, get_logger


class TestWsCtxEngineLogger:
    """Test WsCtxEngineLogger functionality."""
    
    def _flush_logger(self, logger):
        """Helper to flush logger handlers."""
        for handler in logger.logger.handlers:
            handler.flush()
    
    def test_logger_creates_log_directory(self, tmp_path):
        """Test that logger creates log directory if it doesn't exist."""
        log_dir = tmp_path / "logs"
        assert not log_dir.exists()
        
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        assert log_dir.exists()
        assert log_dir.is_dir()
    
    def test_logger_creates_log_file(self, tmp_path):
        """Test that logger creates a log file."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        # Log a message to ensure file is created
        logger.info("Test message")
        
        # Flush handlers to ensure file is written
        for handler in logger.logger.handlers:
            handler.flush()
        
        # Check that a log file was created
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        assert len(log_files) == 1
        assert log_files[0].name.startswith("ws-ctx-engine-")
        assert log_files[0].name.endswith(".log")
    
    def test_logger_writes_to_file(self, tmp_path):
        """Test that logger writes messages to file."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        test_message = "Test log message"
        logger.info(test_message)
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert test_message in log_content
        assert "INFO" in log_content
    
    def test_logger_structured_format(self, tmp_path):
        """Test that logger uses structured format: timestamp | level | name | message."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.info("Test message")
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        # Check format: timestamp | level | name | message
        lines = log_content.strip().split('\n')
        assert len(lines) >= 1
        
        parts = lines[0].split(' | ')
        assert len(parts) == 4
        assert "INFO" in parts[1]
        assert "ws_ctx_engine" in parts[2]
        assert "Test message" in parts[3]
    
    def test_log_fallback(self, tmp_path):
        """Test log_fallback method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.log_fallback(
            component="vector_index",
            primary="LEANN",
            fallback="FAISS",
            reason="ImportError: No module named 'leann'"
        )
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Fallback triggered" in log_content
        assert "component=vector_index" in log_content
        assert "primary=LEANN" in log_content
        assert "fallback=FAISS" in log_content
        assert "WARNING" in log_content
    
    def test_log_phase(self, tmp_path):
        """Test log_phase method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.log_phase(
            phase="parsing",
            duration=2.5,
            files_processed=100,
            chunks_created=500
        )
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Phase complete" in log_content
        assert "phase=parsing" in log_content
        assert "duration=2.50s" in log_content
        assert "files_processed=100" in log_content
        assert "chunks_created=500" in log_content
        assert "INFO" in log_content
    
    def test_log_phase_without_metrics(self, tmp_path):
        """Test log_phase method without additional metrics."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.log_phase(phase="indexing", duration=1.2)
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Phase complete" in log_content
        assert "phase=indexing" in log_content
        assert "duration=1.20s" in log_content
    
    def test_log_error(self, tmp_path):
        """Test log_error method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.log_error(
                error=e,
                context={"file_path": "test.py", "line_number": 42}
            )
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Error occurred" in log_content
        assert "file_path=test.py" in log_content
        assert "line_number=42" in log_content
        assert "ERROR" in log_content
        assert "Traceback" in log_content
        assert "ValueError: Test error" in log_content
    
    def test_log_error_without_context(self, tmp_path):
        """Test log_error method without context."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        try:
            raise RuntimeError("Test runtime error")
        except RuntimeError as e:
            logger.log_error(error=e)
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Error occurred" in log_content
        assert "Test runtime error" in log_content
        assert "ERROR" in log_content
    
    def test_debug_method(self, tmp_path):
        """Test debug method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.debug("Debug message")
        self._flush_logger(logger)
        
        # Read log file (DEBUG should be in file)
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Debug message" in log_content
        assert "DEBUG" in log_content
    
    def test_info_method(self, tmp_path):
        """Test info method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.info("Info message")
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Info message" in log_content
        assert "INFO" in log_content
    
    def test_warning_method(self, tmp_path):
        """Test warning method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.warning("Warning message")
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Warning message" in log_content
        assert "WARNING" in log_content
    
    def test_error_method(self, tmp_path):
        """Test error method."""
        log_dir = tmp_path / "logs"
        logger = WsCtxEngineLogger(log_dir=str(log_dir))
        
        logger.error("Error message")
        self._flush_logger(logger)
        
        # Read log file
        log_files = list(log_dir.glob("ws-ctx-engine-*.log"))
        log_content = log_files[0].read_text()
        
        assert "Error message" in log_content
        assert "ERROR" in log_content
    
    def test_get_logger_singleton(self, tmp_path):
        """Test that get_logger returns singleton instance."""
        log_dir = tmp_path / "logs"
        
        logger1 = get_logger(log_dir=str(log_dir))
        logger2 = get_logger(log_dir=str(log_dir))
        
        assert logger1 is logger2
    
    def test_no_duplicate_handlers(self, tmp_path):
        """Test that creating multiple loggers doesn't create duplicate handlers."""
        log_dir = tmp_path / "logs"
        
        # Create logger twice with same name
        logger1 = WsCtxEngineLogger(log_dir=str(log_dir), name="test_logger")
        logger2 = WsCtxEngineLogger(log_dir=str(log_dir), name="test_logger")
        
        # Should have same underlying logger
        assert logger1.logger is logger2.logger
        
        # Should not have duplicate handlers
        assert len(logger1.logger.handlers) == 2  # console + file
