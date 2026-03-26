"""
Logging infrastructure for ws-ctx-engine.

Provides structured logging with dual output (console + file) and configurable log levels.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class WsCtxEngineLogger:
    """
    Structured logging with dual output (console + file).

    Console: INFO and above
    File: DEBUG and above
    Format: timestamp | level | name | message
    """

    def __init__(self, log_dir: str = ".ws-ctx-engine/logs", name: str = "ws_ctx_engine"):
        """
        Initialize logger with dual output handlers.

        Args:
            log_dir: Directory for log files (default: .ws-ctx-engine/logs)
            name: Logger name (default: ws_ctx_engine)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Prevent propagation to avoid pytest capturing
        self.logger.propagate = False

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler (DEBUG and above)
        log_filename = f"ws-ctx-engine-{datetime.now():%Y%m%d-%H%M%S}.log"
        self.log_file_path = self.log_dir / log_filename
        file_handler = logging.FileHandler(self.log_file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Structured format: timestamp | level | name | message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def log_fallback(self, component: str, primary: str, fallback: str, reason: str) -> None:
        """
        Log backend fallback with context.

        Args:
            component: Component name (e.g., "vector_index", "graph")
            primary: Primary backend that failed
            fallback: Fallback backend being used
            reason: Reason for fallback (exception message)
        """
        self.logger.warning(
            f"Fallback triggered | component={component} | "
            f"primary={primary} | fallback={fallback} | reason={reason}"
        )

    def log_phase(self, phase: str, duration: float, **metrics: Any) -> None:
        """
        Log phase completion with metrics.

        Args:
            phase: Phase name (e.g., "parsing", "indexing", "ranking")
            duration: Phase duration in seconds
            **metrics: Additional metrics to log (e.g., files_processed=100)
        """
        metrics_str = " | ".join(f"{k}={v}" for k, v in metrics.items())
        if metrics_str:
            self.logger.info(
                f"Phase complete | phase={phase} | duration={duration:.2f}s | {metrics_str}"
            )
        else:
            self.logger.info(f"Phase complete | phase={phase} | duration={duration:.2f}s")

    def log_error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """
        Log error with full context and stack trace.

        Args:
            error: Exception that occurred
            context: Additional context (e.g., file_path, line_number)
        """
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            self.logger.error(f"Error occurred | {context_str}", exc_info=True)
        else:
            self.logger.error(f"Error occurred | {str(error)}", exc_info=True)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)


# Global logger instance
_global_logger: WsCtxEngineLogger | None = None


def get_logger(log_dir: str = ".ws-ctx-engine/logs") -> WsCtxEngineLogger:
    """
    Get or create global logger instance.

    Args:
        log_dir: Directory for log files

    Returns:
        Global WsCtxEngineLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = WsCtxEngineLogger(log_dir=log_dir)
    return _global_logger
