# Getting Started

<cite>
**Referenced Files in This Document**
- [INSTALL.md](file://INSTALL.md)
- [README.md](file://README.md)
- [pyproject.toml](file://pyproject.toml)
- [.ws-ctx-engine.yaml.example](file://.ws-ctx-engine.yaml.example)
- [src/ws_ctx_engine/cli/cli.py](file://src/ws_ctx_engine/cli/cli.py)
- [src/ws_ctx_engine/config/config.py](file://src/ws_ctx_engine/config/config.py)
- [src/ws_ctx_engine/workflow/indexer.py](file://src/ws_ctx_engine/workflow/indexer.py)
- [src/ws_ctx_engine/workflow/query.py](file://src/ws_ctx_engine/workflow/query.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
4. [First-Time Setup](#first-time-setup)
5. [Quick Start](#quick-start)
6. [Doctor Command](#doctor-command)
7. [CLI Commands Overview](#cli-commands-overview)
8. [Configuration Reference](#configuration-reference)
9. [Common Workflows](#common-workflows)
10. [Troubleshooting](#troubleshooting)
11. [Next Steps](#next-steps)

## Introduction
ws-ctx-engine helps you package codebases into optimized context for Large Language Models (LLMs). It intelligently selects the most relevant files using hybrid ranking (semantic search + PageRank), manages token budgets, and supports multiple output formats for paste or upload workflows.

## Prerequisites
- Python 3.11 or newer
- Basic understanding of LLMs and command-line usage
- Familiarity with repository structures and file patterns

**Section sources**
- [pyproject.toml:10](file://pyproject.toml#L10)
- [README.md:16](file://README.md#L16)

## Installation Methods
Choose one of the three dependency tiers below. The “All” tier is recommended for most users.

- Core (Minimal)
  - Purpose: Essential dependencies only (basic functionality)
  - Install: `pip install ws-ctx-engine`
  - Use case: Minimal footprint, basic regex-based parsing and file-size ranking

- All (Recommended)
  - Purpose: Primary backends for optimal performance
  - Install: `pip install "ws-ctx-engine[all]"`
  - Adds: python-igraph, sentence-transformers, py-tree-sitter, tree-sitter grammars, leann

- Fast (Fallback-focused)
  - Purpose: Core + fallback backends for reliability
  - Install: `pip install "ws-ctx-engine[fast]"`
  - Adds: faiss-cpu, networkx, scikit-learn

Development installation:
- `pip install -e ".[dev]"` installs development tools (pytest, black, ruff, mypy)

Verification:
- After installation, verify with: `python -c "import ws_ctx_engine; print(ws_ctx_engine.__version__)"`
- Then run dependency doctor: `ws-ctx-engine doctor`

**Section sources**
- [INSTALL.md:3-47](file://INSTALL.md#L3-L47)
- [INSTALL.md:49-86](file://INSTALL.md#L49-L86)
- [README.md:18-50](file://README.md#L18-L50)
- [pyproject.toml:67-111](file://pyproject.toml#L67-L111)

## First-Time Setup
1. Create a configuration file
   - Copy the example to your repository root: `.ws-ctx-engine.yaml.example` → `.ws-ctx-engine.yaml`
   - Customize output format, token budget, include/exclude patterns, and backend preferences

2. Initialize your repository index
   - Build indexes once: `ws-ctx-engine index /path/to/your/repo`
   - This creates `.ws-ctx-engine/` with vector index, graph, metadata, and logs

3. Generate a context pack
   - ZIP output (default): `ws-ctx-engine pack /path/to/your/repo`
   - XML output for paste workflows: `ws-ctx-engine pack /path/to/your/repo --format xml`
   - Specify token budget: `ws-ctx-engine pack /path/to/your/repo --budget 50000`
   - Query with natural language: `ws-ctx-engine query "authentication and user management" --format zip`

4. Use the output
   - XML: Copy `repomix-output.xml` and paste into Claude.ai or ChatGPT
   - ZIP: Upload `ws-ctx-engine.zip` to Cursor or Claude Code. The archive includes:
     - `files/`: Selected source files with preserved directory structure
     - `REVIEW_CONTEXT.md`: Manifest with importance scores and reading order

**Section sources**
- [README.md:64-117](file://README.md#L64-L117)
- [README.md:186-234](file://README.md#L186-L234)

## Quick Start
Follow these steps to get up and running quickly:

1. Check dependencies
   - `ws-ctx-engine doctor`
   - If recommended dependencies are missing, install the “All” tier: `pip install "ws-ctx-engine[all]"`

2. Index your repository
   - `ws-ctx-engine index /path/to/your/repo`
   - Expect `.ws-ctx-engine/` with vector index, graph, metadata, and logs

3. Generate context pack
   - `ws-ctx-engine pack /path/to/your/repo --format zip --budget 100000`
   - Or for paste workflows: `ws-ctx-engine pack /path/to/your/repo --format xml --budget 50000`

4. Use the output
   - ZIP: Upload `ws-ctx-engine.zip` to Cursor or Claude Code
   - XML: Paste `repomix-output.xml` into Claude.ai or ChatGPT

**Section sources**
- [README.md:64-117](file://README.md#L64-L117)

## Doctor Command
The doctor command checks optional dependencies and recommends the best installation profile.

- Run: `ws-ctx-engine doctor`
- Interpreting results:
  - Green “OK” indicates a dependency is available
  - Yellow “MISSING” indicates a recommended dependency is not installed
  - If any recommended dependencies are missing, install the “All” tier for full feature set

**Section sources**
- [src/ws_ctx_engine/cli/cli.py:329-364](file://src/ws_ctx_engine/cli/cli.py#L329-L364)
- [INSTALL.md:76-86](file://INSTALL.md#L76-L86)

## CLI Commands Overview
Key commands and their typical usage:

- `ws-ctx-engine doctor`
  - Checks optional dependencies and prints recommendations

- `ws-ctx-engine index <repo_path>`
  - Builds and saves indexes for later queries
  - Options: `--config`, `--verbose`, `--incremental`

- `ws-ctx-engine query "<query_text>" [--options]`
  - Searches indexed repository and generates output
  - Options include format, budget, mode, session-id, dedup, stdout, copy, compress, shuffle

- `ws-ctx-engine pack <repo_path> [--options]`
  - Full workflow: index + query + pack
  - Options mirror those of query plus `--query`, `--changed-files`

- `ws-ctx-engine search "<query_text>" [--options]`
  - Returns ranked file paths without packaging

- `ws-ctx-engine mcp [--workspace] [--mcp-config] [--rate-limit]`
  - Runs ws-ctx-engine as an MCP stdio server

- `ws-ctx-engine --version`
  - Prints the installed version

**Section sources**
- [README.md:118-185](file://README.md#L118-L185)
- [src/ws_ctx_engine/cli/cli.py:376-404](file://src/ws_ctx_engine/cli/cli.py#L376-L404)
- [src/ws_ctx_engine/cli/cli.py:405-501](file://src/ws_ctx_engine/cli/cli.py#L405-L501)
- [src/ws_ctx_engine/cli/cli.py:503-644](file://src/ws_ctx_engine/cli/cli.py#L503-L644)
- [src/ws_ctx_engine/cli/cli.py:646-695](file://src/ws_ctx_engine/cli/cli.py#L646-L695)
- [src/ws_ctx_engine/cli/cli.py:697-800](file://src/ws_ctx_engine/cli/cli.py#L697-L800)

## Configuration Reference
Create `.ws-ctx-engine.yaml` in your repository root to customize behavior.

Key sections:
- Output settings: format, token_budget, output_path
- Scoring weights: semantic_weight, pagerank_weight (must sum to 1.0)
- File filtering: include_tests, include_patterns, exclude_patterns, respect_gitignore
- Backend selection: vector_index, graph, embeddings (auto | primary | fallback)
- Embeddings: model, device, batch_size, api_provider, api_key_env
- Performance: cache_embeddings, incremental_index

Example configurations are provided in the example file for PR review, bug investigation, documentation generation, minimal dependencies, and maximum performance.

**Section sources**
- [README.md:186-234](file://README.md#L186-L234)
- [.ws-ctx-engine.yaml.example:1-254](file://.ws-ctx-engine.yaml.example#L1-L254)
- [src/ws_ctx_engine/config/config.py:16-101](file://src/ws_ctx_engine/config/config.py#L16-L101)

## Common Workflows
- Code review workflow
  - Index once: `ws-ctx-engine index ~/projects/myapp`
  - Generate context for PR review: `ws-ctx-engine query "authentication changes" --changed-files changed.txt --format zip --budget 50000`
  - Upload `ws-ctx-engine.zip` to Cursor for review

- Bug investigation
  - Find relevant code: `ws-ctx-engine pack ~/projects/myapp --query "database connection pooling and timeout handling" --format xml --budget 30000`
  - Paste `repomix-output.xml` into Claude.ai

- Documentation generation
  - Select core API files: `ws-ctx-engine pack ~/projects/myapp --query "public API endpoints and data models" --format zip --budget 80000`

**Section sources**
- [README.md:309-345](file://README.md#L309-L345)

## Troubleshooting
- Python version
  - Requires Python 3.11 or newer. Check with `python --version`.

- Permission errors
  - Try installing for the current user: `pip install --user ws-ctx-engine`

- C++ compilation errors (All tier)
  - Some dependencies require a C++ compiler:
    - macOS: `xcode-select --install`
    - Ubuntu/Debian: `sudo apt-get install build-essential`
    - Windows: install Visual Studio Build Tools
  - Alternatively, install the “Fast” tier: `pip install "ws-ctx-engine[fast]"`

- Missing optional dependencies
  - Run `ws-ctx-engine doctor` and install the “All” tier if recommended dependencies are missing

- Index is stale, rebuilding
  - If files have changed since last index, the system automatically rebuilds. To force rebuild: remove `.ws-ctx-engine/` and re-run `ws-ctx-engine index /path/to/repo`

- Local embeddings OOM, falling back to API
  - Reduce batch size or switch to API embeddings
  - Set environment variable for API access (e.g., `OPENAI_API_KEY`)

**Section sources**
- [INSTALL.md:93-120](file://INSTALL.md#L93-L120)
- [README.md:386-427](file://README.md#L386-L427)

## Next Steps
- Explore the example configurations for different use cases
- Experiment with different output formats (XML, ZIP, JSON, YAML, MD)
- Tune token budgets and backend selections for your environment
- Integrate with your LLM workflows and agent pipelines

**Section sources**
- [.ws-ctx-engine.yaml.example:206-254](file://.ws-ctx-engine.yaml.example#L206-L254)
- [README.md:429-457](file://README.md#L429-L457)