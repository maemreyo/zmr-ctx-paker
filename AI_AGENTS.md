# AI AGENTS - ctx-packer

## Quick Start

```bash
# Install
pip install ctx-packer

# Index a repo
ctx-packer index /path/to/repo

# Query a repo
ctx-packer query "your question" --repo /path/to/repo
```

## Commands

| Command | Description |
|---------|-------------|
| `ctx-packer index <repo>` | Build indexes (vector, graph, domain map) |
| `ctx-packer query "<question>" --repo <repo>` | Search and generate output |
| `ctx-packer pack <repo> --query "<question>"` | Full workflow: index + query + pack |
| `ctx-packer status <repo>` | Show index stats |
| `ctx-packer vacuum <repo>` | Optimize SQLite database |
| `ctx-packer reindex-domain <repo>` | Rebuild domain_map.db only (fast) |

## Output

- Default output: `output/ctx-packer.zip`
- Format: XML in ZIP
- Token budget: 100,000 tokens (default)

## Options

```
--format xml|zip    Output format (default: zip)
--budget N          Token budget (default: 100000)
--repo <path>       Repository path
```

## For LLM Context

Use the ZIP/XML output as context for LLM tasks. The output contains:
- Relevant code files ranked by semantic similarity
- Weighted by path, domain, and graph relationships