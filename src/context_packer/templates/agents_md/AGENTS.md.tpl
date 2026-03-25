# AI Agent Context — ctx-packer

> Installed: ${CTX_DATE} | Version: ${CTX_PACKER_VERSION}

## What is ctx-packer?

**ctx-packer** intelligently packages codebases into optimized context for Large Language Models. It provides:
- Semantic code search using vector embeddings
- Dependency graph analysis
- Domain keyword mapping
- ZIP/XML output for AI tools

## Installation

```bash
pip install ctx-packer
# or for all features (recommended):
pip install "ctx-packer[all]"
```

## Quick Start

```bash
# 1. Index the repository (one time)
ctx-packer index .

# 2. Query for context
ctx-packer query "your search terms" --format zip

# 3. Use output in your AI tool
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `ctx-packer index <path>` | Build semantic, graph, and domain indexes |
| `ctx-packer query "<text>" [opts]` | Search and generate output |
| `ctx-packer pack <path> --query "<text>"` | Full workflow (index + query + pack) |
| `ctx-packer status <path>` | Show index statistics |
| `ctx-packer vacuum <path>` | Optimize SQLite database |
| `ctx-packer reindex-domain <path>` | Rebuild domain map only |

### Options

- `--format {xml|zip}` — Output format (default: zip)
- `--budget N` — Token budget (default: 100000)
- `--output PATH` — Output directory (default: ./output)
- `--changed-files PATH` — Files changed (for PR context)

## Use Cases

### Code Review
```bash
ctx-packer pack . --query "authentication changes" --format zip --budget 50000
```

### Bug Investigation
```bash
ctx-packer pack . --query "database connection handling" --format xml --budget 30000
```

### Feature Development
```bash
ctx-packer query "public API endpoints" --format zip --budget 80000
```

### PR Context
```bash
ctx-packer pack . --changed-files changed_files.txt --format zip
```

## Output

- **ZIP**: Code files + metadata, upload to Cursor/Claude Code
- **XML**: Structured format for pasting into web interfaces

## Configuration

- Config file: `.ctx-pack.yaml` (optional)
- Index directory: `.context-pack/`
- Default budget: 100,000 tokens

## For AI Agents

When working in this repository, you can use ctx-packer to:
1. Find relevant code for any task
2. Generate context for code reviews
3. Investigate bugs with targeted search
4. Package code for context in LLM conversations

Example workflow:
```bash
# Index (if not done)
ctx-packer index .

# Query relevant code
ctx-packer query "the feature or bug you're working on" --format zip

# The ZIP contains relevant files ranked by semantic similarity
```
