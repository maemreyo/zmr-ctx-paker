# ws-ctx-engine

Intelligently package codebases into optimized context for Large Language Models (LLMs). ws-ctx-engine uses hybrid ranking (semantic search + PageRank) to select the most relevant files within your token budget, with comprehensive fallback strategies for production reliability.

## Features

- **Hybrid Ranking**: Combines semantic search with structural analysis (PageRank) to identify the most important code
- **Token Budget Management**: Precise token counting using tiktoken to fit LLM context windows
- **Dual Output Formats**: 
  - XML for one-shot paste workflows (Claude.ai, ChatGPT)
  - ZIP for multi-turn upload workflows (Cursor, Claude Code)
- **Production Ready**: Automatic fallback strategies for every component
- **Incremental Indexing**: Build indexes once, reuse for fast queries
- **Flexible Configuration**: Customize weights, filters, and backends via YAML

## Installation

ws-ctx-engine offers three installation tiers based on your needs:

### Minimal (Core Only)

Basic functionality with regex-based parsing and file size ranking:

```bash
pip install ws-ctx-engine
```

**Includes**: tiktoken, PyYAML, lxml, typer, rich

### All (Recommended)

All features including primary backends for optimal performance:

```bash
pip install "ws-ctx-engine[all]"
```

**Adds**: python-igraph (fast PageRank), sentence-transformers (local embeddings), py-tree-sitter (accurate AST parsing)

### Fast (Fallback-focused)

Core + fallback backends for semantic search and graph analysis:

```bash
pip install "ws-ctx-engine[fast]"
```

**Adds**: faiss-cpu (vector search), networkx (graph analysis)

## Quick Start

### 1. Check Dependencies (Recommended)

```bash
ws-ctx-engine doctor
```

If doctor reports missing optional dependencies:

```bash
pip install "ws-ctx-engine[all]"
```

### 2. Index Your Repository

Build indexes for semantic search and dependency analysis:

```bash
ws-ctx-engine index /path/to/your/repo
```

This creates a `.ws-ctx-engine/` directory with:
- `vector.idx` - Semantic search index
- `graph.pkl` - Dependency graph with PageRank scores
- `metadata.json` - Staleness detection metadata
- `logs/` - Execution logs

### 3. Generate Context Pack

Create an optimized context pack for LLM review:

```bash
# Generate ZIP output (default)
ws-ctx-engine pack /path/to/your/repo

# Generate XML output for paste workflows
ws-ctx-engine pack /path/to/your/repo --format xml

# Specify token budget
ws-ctx-engine pack /path/to/your/repo --budget 50000

# Query with natural language
ws-ctx-engine query "authentication and user management" --format zip
```

### 4. Use the Output

**For XML output**: Copy the generated `repomix-output.xml` and paste into Claude.ai or ChatGPT

**For ZIP output**: Upload `ws-ctx-engine.zip` to Cursor or Claude Code. The archive includes:
- `files/` - Selected source files with preserved directory structure
- `REVIEW_CONTEXT.md` - Manifest with importance scores and reading order

## CLI Commands

### `ws-ctx-engine doctor`

Check optional dependencies and show recommended setup:

```bash
ws-ctx-engine doctor
```

### `ws-ctx-engine index`

Build and save indexes for later queries:

```bash
ws-ctx-engine index <repo_path> [OPTIONS]
```

**Options**:
- `--config PATH` - Custom configuration file (default: `.ws-ctx-engine.yaml`)
- `--verbose` - Enable detailed logging with timing information

### `ws-ctx-engine query`

Search indexed repository and generate output:

```bash
ws-ctx-engine query <query_text> [OPTIONS]
```

**Options**:
- `--format {xml|zip}` - Output format (default: zip)
- `--budget INT` - Token budget (default: 100000)
- `--config PATH` - Custom configuration file
- `--output PATH` - Output directory (default: ./output)
- `--verbose` - Enable detailed logging

### `ws-ctx-engine pack`

Full workflow: index + query + pack:

```bash
ws-ctx-engine pack <repo_path> [OPTIONS]
```

**Options**:
- `--query TEXT` - Natural language query for semantic search
- `--changed-files PATH` - File with list of changed files (one per line)
- `--format {xml|zip}` - Output format (default: zip)
- `--budget INT` - Token budget (default: 100000)
- `--config PATH` - Custom configuration file
- `--output PATH` - Output directory (default: ./output)
- `--verbose` - Enable detailed logging

## Configuration

Create a `.ws-ctx-engine.yaml` file in your repository root to customize behavior:

```yaml
# Output settings
format: zip  # xml | zip
token_budget: 100000
output_path: ./output

# Scoring weights (must sum to 1.0)
semantic_weight: 0.6
pagerank_weight: 0.4

# File filtering
include_tests: false
include_patterns:
  - "**/*.py"
  - "**/*.js"
  - "**/*.ts"
exclude_patterns:
  - "*.min.js"
  - "node_modules/**"
  - "__pycache__/**"
  - ".git/**"

# Backend selection (auto | primary | fallback)
backends:
  vector_index: auto  # auto | leann | faiss
  graph: auto         # auto | igraph | networkx
  embeddings: auto    # auto | local | api

# Embeddings configuration
embeddings:
  model: all-MiniLM-L6-v2
  device: cpu
  batch_size: 32
  api_provider: openai
  api_key_env: OPENAI_API_KEY

# Performance tuning
performance:
  max_workers: 4
  cache_embeddings: true
  incremental_index: true
```

See `.ws-ctx-engine.yaml.example` for detailed documentation of all options.

## How It Works

ws-ctx-engine uses a multi-stage pipeline to select the most relevant code:

### 1. AST Parsing

Parse source code into structured chunks with metadata:
- **Primary**: py-tree-sitter (accurate, 40+ languages)
- **Fallback**: Regex patterns (Python, JavaScript, TypeScript)

### 2. Semantic Indexing

Build vector embeddings for semantic search:
- **Primary**: LEANN (97% storage savings, graph-based)
- **Fallback**: FAISS (battle-tested HNSW index)
- **Embeddings**: sentence-transformers (local) or OpenAI API (fallback)

### 3. Dependency Graph

Analyze code structure and compute PageRank:
- **Primary**: python-igraph (C++ backend, <1s for 10k files)
- **Fallback**: NetworkX (pure Python, <10s for 10k files)

### 4. Hybrid Ranking

Merge semantic and structural scores:
```
importance_score = semantic_weight × semantic_score + pagerank_weight × pagerank_score
```

### 5. Budget Selection

Greedy knapsack algorithm to maximize importance within token budget:
- 80% budget for file content
- 20% reserved for metadata and manifest

### 6. Output Generation

Package selected files in chosen format:
- **XML**: Single file with Repomix-style structure
- **ZIP**: Preserved directory structure + manifest

## Fallback Strategy

ws-ctx-engine never fails due to missing dependencies. Each component has automatic fallbacks:

```
Level 1: igraph + LEANN + local embeddings (optimal)
  ↓ igraph fails
Level 2: NetworkX + LEANN + local embeddings
  ↓ LEANN fails
Level 3: NetworkX + FAISS + local embeddings
  ↓ local embeddings OOM
Level 4: NetworkX + FAISS + API embeddings
  ↓ API fails
Level 5: NetworkX + TF-IDF (no embeddings)
  ↓ NetworkX too slow
Level 6: File size ranking only (no graph)
```

All fallback transitions are logged with actionable suggestions.

## Performance

Performance targets with primary backends:

- **Indexing**: <5 minutes for 10,000 files
- **Query**: <10 seconds for 10,000 files
- **Parsing**: <5 seconds per 1,000 lines of code
- **Token Counting**: ±2% accuracy vs actual LLM count

Fallback backends maintain functionality within 2x of primary performance.

## Examples

### Code Review Workflow

```bash
# Index your repository once
ws-ctx-engine index ~/projects/myapp

# Generate context for PR review
ws-ctx-engine query "authentication changes" \
  --changed-files changed.txt \
  --format zip \
  --budget 50000

# Upload ws-ctx-engine.zip to Cursor for review
```

### Bug Investigation

```bash
# Find relevant code for a bug
ws-ctx-engine pack ~/projects/myapp \
  --query "database connection pooling and timeout handling" \
  --format xml \
  --budget 30000

# Paste repomix-output.xml into Claude.ai
```

### Documentation Generation

```bash
# Select core API files
ws-ctx-engine pack ~/projects/myapp \
  --query "public API endpoints and data models" \
  --format zip \
  --budget 80000
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev,all]"

# Run all tests
pytest

# Run with coverage
pytest --cov=ws_ctx_engine --cov-report=html

# Run property-based tests only
pytest -m property

# Run integration tests
pytest -m integration

# Run benchmarks
pytest -m benchmark --benchmark-only
```

### Test Profiles

Hypothesis property tests support multiple profiles:

```bash
# CI profile: 100 examples, verbose output
pytest --hypothesis-profile=ci

# Dev profile: 20 examples, quick feedback
pytest --hypothesis-profile=dev

# Debug profile: 10 examples, maximum verbosity
pytest --hypothesis-profile=debug
```

## Troubleshooting

### "LEANN not available, using FAISS fallback"

LEANN is an optional primary backend. Install with:
```bash
pip install "ws-ctx-engine[all]"
```

### "igraph not available, using NetworkX fallback"

python-igraph requires C++ compilation. Install with:
```bash
pip install "ws-ctx-engine[all]"
```

Or force NetworkX backend in config:
```yaml
backends:
  graph: networkx
```

### "Local embeddings OOM, falling back to API"

Reduce batch size or use API embeddings:
```yaml
embeddings:
  batch_size: 16  # Reduce from default 32
  # Or use API
backends:
  embeddings: api
```

Set `OPENAI_API_KEY` environment variable for API access.

### "Index is stale, rebuilding"

Files have changed since last index. This is automatic. To force rebuild:
```bash
rm -rf .ws-ctx-engine/
ws-ctx-engine index /path/to/repo
```

## License

GPL-3.0-or-later - see LICENSE file for details.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This ensures that any derivative work must also be open source under GPL-3.0.

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## AI Agents

See [AI_AGENTS.md](AI_AGENTS.md) for guidelines on how AI agents should use this tool.

## Citation

If you use ws-ctx-engine in research, please cite:

```bibtex
@software{ws_ctx_engine,
  title = {ws-ctx-engine: Intelligent Codebase Packaging for LLMs},
  author = {zamery},
  year = {2024},
  url = {https://github.com/maemreyo/zmr-ctx-paker}
}
```
