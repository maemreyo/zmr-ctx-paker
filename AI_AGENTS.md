# AI AGENTS - ctx-packer

## Quick Start

```bash
# Install
pip install ctx-packer

# Index a repo
context-pack index /path/to/repo

# Query a repo
context-pack query "your question" --repo /path/to/repo
```

## Commands

| Command | Description |
|---------|-------------|
| `context-pack index <repo>` | Build indexes (vector, graph, domain map) |
| `context-pack query "<question>" --repo <repo>` | Search and generate output |
| `context-pack pack <repo> --query "<question>"` | Full workflow: index + query + pack |
| `context-pack status <repo>` | Show index stats |
| `context-pack vacuum <repo>` | Optimize SQLite database |
| `context-pack reindex-domain <repo>` | Rebuild domain_map.db only (fast) |

## Output

- Default output: `output/context-pack.zip`
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
