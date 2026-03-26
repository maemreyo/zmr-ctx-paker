"""
Demo script showing WsCtxEngineLogger usage.
"""

from ws_ctx_engine import get_logger

# Get logger instance
logger = get_logger()

# Basic logging
logger.info("Starting ws-ctx-engine")
logger.debug("Debug information (only in file)")
logger.warning("This is a warning")
logger.error("This is an error")

# Log backend fallback
logger.log_fallback(
    component="vector_index",
    primary="LEANN",
    fallback="FAISS",
    reason="ImportError: No module named 'leann'",
)

# Log phase completion with metrics
logger.log_phase(phase="parsing", duration=2.5, files_processed=100, chunks_created=500)

# Log error with context
try:
    raise ValueError("Example error")
except ValueError as e:
    logger.log_error(error=e, context={"file_path": "example.py", "line_number": 42})

print("\nLogs written to .ws-ctx-engine/logs/")
print("Console shows INFO and above")
print("File contains DEBUG and above")
