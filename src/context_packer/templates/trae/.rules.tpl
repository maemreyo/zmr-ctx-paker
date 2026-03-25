# ctx-packer — Code Packaging for LLMs

## Overview

This project uses ctx-packer to build optimized code context for AI agents.

## Available Commands

| Command | Description |
|---------|-------------|
| `${CTX_CMD_INDEX}` | Build indexes (vector, graph, domain) |
| `${CTX_CMD_SEARCH}` | Search codebase |
| `${CTX_CMD_PACK}` | Full workflow |
| `${CTX_CMD_STATUS}` | Show index stats |

## Usage Examples

```bash
# Index the repo
${CTX_CMD_INDEX}

# Search for context
${CTX_CMD_SEARCH}

# Pack for AI context
${CTX_CMD_PACK}
```

## Notes

- Index location: `.context-pack/`
- Default output: ZIP format
- Default budget: 100k tokens
- Supports XML for pasting into web interfaces
