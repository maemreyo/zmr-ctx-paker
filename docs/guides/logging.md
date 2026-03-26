# ws-ctx-engine Logging

## Overview

The ws-ctx-engine uses a structured logging system with dual output (console + file) to provide comprehensive visibility into operations while keeping console output clean.

## Features

- **Dual Output**: 
  - Console: INFO and above (clean, user-facing)
  - File: DEBUG and above (comprehensive, for debugging)
  
- **Structured Format**: `timestamp | level | name | message`

- **Log Levels**: DEBUG, INFO, WARNING, ERROR

- **Log Directory**: `.ws-ctx-engine/logs/`

- **Specialized Methods**:
  - `log_fallback()`: Log backend fallback events
  - `log_phase()`: Log phase completion with metrics
  - `log_error()`: Log errors with context and stack traces

## Usage

### Basic Logging

```python
from ws_ctx_engine import get_logger

logger = get_logger()

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

### Backend Fallback Logging

```python
logger.log_fallback(
    component="vector_index",
    primary="LEANN",
    fallback="FAISS",
    reason="ImportError: No module named 'leann'"
)
```

### Phase Completion Logging

```python
logger.log_phase(
    phase="parsing",
    duration=2.5,
    files_processed=100,
    chunks_created=500
)
```

### Error Logging with Context

```python
try:
    # Some operation
    raise ValueError("Something went wrong")
except ValueError as e:
    logger.log_error(
        error=e,
        context={"file_path": "example.py", "line_number": 42}
    )
```

## Log File Format

Log files are created with timestamps in the filename:
```
.ws-ctx-engine/logs/ws-ctx-engine-20260323-230037.log
```

Each log entry follows the structured format:
```
2026-03-23 23:00:37 | INFO     | ws_ctx_engine | Starting ws-ctx-engine
2026-03-23 23:00:37 | DEBUG    | ws_ctx_engine | Debug information
2026-03-23 23:00:37 | WARNING  | ws_ctx_engine | This is a warning
2026-03-23 23:00:37 | ERROR    | ws_ctx_engine | Error occurred
Traceback (most recent call last):
  ...
```

## Requirements Satisfied

- **12.1**: Comprehensive error logging with file path, line number, and stack trace
- **12.4**: Log level filtering (DEBUG < INFO < WARNING < ERROR)
- **12.6**: Dual output logging (console + file)

## Example

See `examples/logger_demo.py` for a complete demonstration of all logging features.
