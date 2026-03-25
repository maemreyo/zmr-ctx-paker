# AI AGENTS - ws-ctx-engine

## Quick Start

```bash
# Install
pip install ws-ctx-engine

# Index a repo
ws-ctx-engine index /path/to/repo

# Query a repo
ws-ctx-engine query "your question" --repo /path/to/repo
```

## Commands

| Command | Description |
|---------|-------------|
| `ws-ctx-engine index <repo>` | Build indexes (vector, graph, domain map) |
| `ws-ctx-engine query "<question>" --repo <repo>` | Search and generate output |
| `ws-ctx-engine pack <repo> --query "<question>"` | Full workflow: index + query + pack |
| `ws-ctx-engine status <repo>` | Show index stats |
| `ws-ctx-engine vacuum <repo>` | Optimize SQLite database |
| `ws-ctx-engine reindex-domain <repo>` | Rebuild domain_map.db only (fast) |

## Output

- Default output: `output/ws-ctx-engine.zip`
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