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
${CTX_CMD_INDEX}

# 2. Query for context
${CTX_CMD_QUERY} --format zip

# 3. Use output in your AI tool
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `${CTX_CMD_INDEX}` | Build semantic, graph, and domain indexes |
| `${CTX_CMD_QUERY} [opts]` | Search and generate output |
| `${CTX_CMD_PACK}` | Full workflow (index + query + pack) |
| `${CTX_CMD_STATUS}` | Show index statistics |
| `${CTX_CMD_VACUUM}` | Optimize SQLite database |
| `${CTX_CMD_REINDEX_DOMAIN}` | Rebuild domain map only |

### Options

- `--format {xml|zip}` — Output format (default: zip)
- `--budget N` — Token budget (default: 100000)
- `--output PATH` — Output directory (default: ./output)
- `--changed-files PATH` — Files changed (for PR context)

## Use Cases

### Code Review
```bash
${CTX_CMD_FULL_ZIP} --budget 50000
```

### Bug Investigation
```bash
${CTX_CMD_FULL_XML} --budget 30000
```

### Feature Development
```bash
${CTX_CMD_QUERY} --format zip --budget 80000
```

### PR Context
```bash
${CTX_CMD_FULL_ZIP} --changed-files changed_files.txt
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
${CTX_CMD_INDEX}

# Query relevant code
${CTX_CMD_QUERY} --format zip

# The ZIP contains relevant files ranked by semantic similarity
```
