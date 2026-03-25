# Package Structure

This document describes the ws-ctx-engine package structure created in Task 1.1.

## Directory Layout

```
ws-ctx-engine/
├── src/
│   └── ws_ctx_engine/          # Main package directory
│       ├── __init__.py           # Package initialization
│       ├── cli.py                # CLI entry point (placeholder)
│       └── py.typed              # PEP 561 type checking marker
├── tests/
│   ├── __init__.py
│   ├── test_package.py           # Basic package tests
│   ├── unit/                     # Unit tests directory
│   │   └── __init__.py
│   ├── property/                 # Property-based tests directory
│   │   └── __init__.py
│   └── integration/              # Integration tests directory
│       └── __init__.py
├── docs/
│   └── PRD.md                    # Product Requirements Document
├── .kiro/
│   └── specs/
│       └── ws-ctx-engine/       # Spec files
│           ├── requirements.md
│           ├── design.md
│           └── tasks.md
├── pyproject.toml                # Package configuration and metadata
├── README.md                     # User documentation
├── INSTALL.md                    # Installation guide
├── STRUCTURE.md                  # This file
├── LICENSE                       # MIT License
├── .gitignore                    # Git ignore patterns
└── .ws-ctx-engine.yaml.example    # Example configuration file
```

## Key Files

### pyproject.toml
The main package configuration file following PEP 621 standards. Defines:
- Package metadata (name, version, description, authors)
- Build system (setuptools)
- Three dependency tiers: core, fast, all
- Development dependencies
- CLI entry point: `ws-ctx-engine`
- Testing configuration (pytest, coverage)
- Code quality tools (black, ruff, mypy)

### src/ws_ctx_engine/__init__.py
Package initialization file that exports the version number.

### src/ws_ctx_engine/cli.py
Placeholder for the CLI implementation (will be implemented in Task 17).

### src/ws_ctx_engine/py.typed
PEP 561 marker file indicating this package supports type checking.

## Dependency Tiers

### Core (Minimal)
```toml
dependencies = [
    "tiktoken>=0.5.0",      # Token counting
    "PyYAML>=6.0",          # Configuration parsing
    "lxml>=4.9.0",          # XML generation
]
```

### Fast (Core + Fallback Backends)
```toml
[project.optional-dependencies]
fast = [
    "faiss-cpu>=1.7.4",     # Fallback vector index
    "networkx>=3.0",        # Fallback graph library
]
```

### All (Fast + Primary Backends)
```toml
all = [
    "faiss-cpu>=1.7.4",
    "networkx>=3.0",
    "python-igraph>=0.11.0",           # Primary graph library
    "sentence-transformers>=2.2.0",    # Local embeddings
    "py-tree-sitter>=0.20.0",          # Primary AST parser
    "tree-sitter-python>=0.20.0",      # Python grammar
    "tree-sitter-javascript>=0.20.0",  # JavaScript grammar
]
```

## Build System

The package uses setuptools as the build backend:
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

## Testing Structure

Tests are organized into three categories:
- **unit/**: Unit tests for individual components
- **property/**: Property-based tests using hypothesis
- **integration/**: End-to-end workflow tests

## CLI Entry Point

The package provides a `ws-ctx-engine` command-line tool:
```toml
[project.scripts]
ws-ctx-engine = "ws_ctx_engine.cli:main"
```

## Code Quality Tools

### Black (Code Formatting)
- Line length: 100
- Target: Python 3.9+

### Ruff (Linting)
- Fast Python linter
- Replaces flake8, isort, pyupgrade

### Mypy (Type Checking)
- Strict type checking enabled
- Ignores missing imports for optional dependencies

## Installation Commands

```bash
# Core tier
pip install ws-ctx-engine

# Fast tier (recommended)
pip install ws-ctx-engine[fast]

# All tier (full features)
pip install ws-ctx-engine[all]

# Development
pip install -e ".[dev]"
```

## Requirements Validation

Task 1.1 requirements have been met:
- ✅ Set up package metadata (name, version, dependencies)
- ✅ Configure build system (setuptools)
- ✅ Define dependency tiers: core, fast, all
- ✅ Requirements 8.1 (configuration management) - structure ready
- ✅ Requirements 11.1 (CLI interface) - entry point defined

## Next Steps

The following tasks will build upon this structure:
- Task 1.2: Configure testing framework (pytest, hypothesis)
- Task 1.3: Set up logging infrastructure
- Task 1.4: Create configuration management system
- Task 2.x: Implement core data models
- Task 3.x: Implement AST Chunker
- And so on...
