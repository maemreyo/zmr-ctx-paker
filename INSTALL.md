# Installation Guide

## Dependency Tiers

ws-ctx-engine offers three installation tiers to balance functionality and dependencies:

### Core (Minimal)
The core tier includes only essential dependencies for basic functionality:
- `tiktoken>=0.5.0` - Token counting for LLM context windows
- `PyYAML>=6.0` - Configuration file parsing
- `lxml>=4.9.0` - Fast XML generation for output

**Install:**
```bash
pip install ws-ctx-engine
```

**Use case:** When you want minimal dependencies and are okay with basic functionality.

### Fast (Recommended)
The fast tier adds fallback backends for improved reliability:
- All core dependencies
- `faiss-cpu>=1.7.4` - Fallback vector index (HNSW algorithm)
- `networkx>=3.0` - Fallback graph library (pure Python)

**Install:**
```bash
pip install ws-ctx-engine[fast]
```

**Use case:** Recommended for most users. Provides good performance with fallback strategies.

### All (Full Features)
The all tier includes primary backends for optimal performance:
- All fast dependencies
- `python-igraph>=0.11.0` - Primary graph library (C++ backend, faster PageRank)
- `sentence-transformers>=2.2.0` - Local embedding model for semantic search
- `py-tree-sitter>=0.20.0` - Primary AST parser for accurate code analysis
- `tree-sitter-python>=0.20.0` - Python grammar for tree-sitter
- `tree-sitter-javascript>=0.20.0` - JavaScript grammar for tree-sitter

**Install:**
```bash
pip install ws-ctx-engine[all]
```

**Use case:** When you need maximum performance and all features.

## Development Installation

For development work, install with dev dependencies:

```bash
pip install -e ".[dev]"
```

This includes:
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-benchmark>=4.0.0` - Performance benchmarking
- `hypothesis>=6.82.0` - Property-based testing
- `black>=23.0.0` - Code formatting
- `ruff>=0.0.280` - Fast linting
- `mypy>=1.4.0` - Type checking

## Verifying Installation

After installation, verify the package is working:

```bash
python -c "import ws_ctx_engine; print(ws_ctx_engine.__version__)"
```

You should see: `0.1.0`

## Requirements

- Python 3.9 or higher
- pip (Python package installer)

## Troubleshooting

### Python Version
If you get an error about Python version, check your Python version:
```bash
python --version
```

ws-ctx-engine requires Python 3.9 or higher.

### Permission Errors
If you get permission errors during installation, try:
```bash
pip install --user ws-ctx-engine
```

### C++ Compilation Errors (All tier)
Some dependencies in the "all" tier require C++ compilation:
- `python-igraph` requires C++ compiler
- `py-tree-sitter` requires C++ compiler

If you encounter compilation errors, you can:
1. Install the "fast" tier instead: `pip install ws-ctx-engine[fast]`
2. Install build tools for your platform:
   - **macOS**: `xcode-select --install`
   - **Ubuntu/Debian**: `sudo apt-get install build-essential`
   - **Windows**: Install Visual Studio Build Tools

## Next Steps

After installation, see the [README.md](README.md) for usage examples and configuration options.
