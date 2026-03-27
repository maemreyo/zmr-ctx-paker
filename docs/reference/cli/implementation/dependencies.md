# Dependencies

Module dependencies and import structure for the CLI.

## External Dependencies

### Core Framework

```python
import typer                    # CLI framework
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
```

### Configuration

```python
import yaml                     # YAML parsing
from pathlib import Path        # Path manipulation
```

### Type Hints

```python
from typing import Optional, List
```

## Internal Dependencies

### Workflow Module

```python
from ..workflow import (
    index_repository,
    query_and_pack,
    search_codebase,
)
```

### Configuration

```python
from ..config import Config
```

### Logging

```python
from ..logger import get_logger
```

### MCP Server

```python
from ..mcp_server import run_mcp_server
```

## Dependency Hierarchy

```
CLI (cli.py)
    ↓
Workflow Module
    ↓
Core Engine (Retrieval, Graph, Vector Index)
    ↓
Utilities & Helpers
```

## Import Organization

### Standard Library First
```python
import os
import sys
from pathlib import Path
```

### Third-Party Libraries
```python
import typer
import yaml
from rich.console import Console
```

### Internal Modules Last
```python
from ..config import Config
from ..workflow import index_repository
```

## Version Requirements

See `pyproject.toml` for exact versions:

```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
]
```

## Related Documentation

- [Framework](framework.md) - Typer and Rich usage
- [Configuration](configuration.md) - Config module
- [Installation Guide](../../INSTALL.md) - Dependency installation
