# ctx-packer — Code Packaging for LLMs

## Overview

This project uses ctx-packer to build optimized code context for AI agents.

## Available Commands

| Command | Description |
|---------|-------------|
| `ctx-packer index <path>` | Build indexes (vector, graph, domain) |
| `ctx-packer query "<text>"` | Search and output |
| `ctx-packer pack <path> --query "<text>"` | Full workflow |
| `ctx-packer status <path>` | Show index stats |

## Usage Examples

```bash
# Index the repo
ctx-packer index .

# Search for context
ctx-packer query "authentication" --format zip

# Pack for AI context
ctx-packer pack . --query "feature investigation"
```

## Notes

- Index location: `.context-pack/`
- Default output: ZIP format
- Default budget: 100k tokens
- Supports XML for pasting into web interfaces
