# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

**ws-ctx-engine** (`wsctx`) — a CLI tool that intelligently packages codebases into optimized LLM context. It uses hybrid ranking (semantic search + PageRank on dependency graphs) to select the most relevant files within a token budget, then outputs XML or ZIP format.

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest                                    # All tests
pytest tests/unit/                        # Unit tests only
pytest tests/integration/                 # Integration tests only
pytest -m property                        # Property-based tests (hypothesis)
pytest -m benchmark --benchmark-only      # Performance benchmarks
pytest tests/unit/test_foo.py::test_bar   # Single test

# Code quality (all required before commit)
black .                                   # Format (100-char line length)
ruff check .                             # Lint
mypy src/                                # Type check (strict mode)

# CLI commands
wsctx doctor                             # Verify dependencies
wsctx index <repo>                       # Build vector + graph indexes
wsctx query <text>                       # Search indexed repo
wsctx pack <repo>                        # Full pipeline: index + rank + pack
```

## Architecture

The core is a **6-stage pipeline** in `src/ws_ctx_engine/`:

1. **Chunker** (`chunker/`) — AST-parses source into `CodeChunk` objects. Primary: tree-sitter; fallback: regex. Language resolvers in `chunker/resolvers/`.
2. **Vector Index** (`vector_index/`) — Builds embeddings for semantic search. Primary: LEANN; fallback: FAISS.
3. **Graph** (`graph/graph.py`) — Builds dependency graph and computes PageRank scores. Primary: igraph; fallback: NetworkX.
4. **Retrieval Engine** (`retrieval/retrieval.py`) — Merges semantic + PageRank scores with configurable weights (default: 0.6/0.4).
5. **Budget Manager** (`budget/budget.py`) — Greedy knapsack selection to fit files in token budget (80% content, 20% reserved).
6. **Packer** (`packer/`) — Outputs `XMLPacker` (Repomix-style) or `ZIPPacker` (archive with structure).

**Orchestration:** `workflow/indexer.py` (index phase) and `workflow/query.py` (query/pack phase) coordinate the pipeline. `backend_selector/backend_selector.py` auto-detects and selects the best available backends across 6 fallback levels — the tool never fails due to missing optional dependencies.

**Entry points:** `cli/cli.py` (Typer-based) exposes `wsctx`, `ws-ctx-engine`, and two aliases. MCP server in `mcp/` for IDE integration.

## Dependency Tiers

```bash
pip install ws-ctx-engine          # Core: tiktoken, PyYAML, lxml, typer, rich
pip install ws-ctx-engine[fast]    # + faiss-cpu, networkx, scikit-learn
pip install ws-ctx-engine[all]     # + igraph, sentence-transformers, tree-sitter, LEANN
pip install -e ".[dev]"            # Development (includes all + pytest, black, ruff, mypy)
```

## Key Conventions

- **Python 3.11+**, strict mypy, 100-char line length (Black)
- **Data models** live in `models/models.py` (`CodeChunk`, `IndexMetadata`)
- **Config** is YAML (`.ws-ctx-engine.yaml`); see `.ws-ctx-engine.yaml.example`
- **Tests** are split: `tests/unit/`, `tests/integration/`, `tests/property/`
- Pre-commit hooks enforce formatting, linting, type checks, and security (bandit)
