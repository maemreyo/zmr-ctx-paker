---
name: ctx-packer
description: >
  Use when user wants to search, index, or pack codebase context for AI.
  Triggers on: "find files about X", "pack context for X", "index the codebase",
  "search codebase for Y", "what files handle Z".
user-invocable: true
---

# ctx-packer Skill

ctx-packer indexes your codebase and builds context bundles for AI agents.

## Commands

```bash
${CTX_CMD_INDEX}          # Build/update index for current dir
${CTX_CMD_SEARCH} # Search indexed codebase
${CTX_CMD_PACK}  # Full workflow: index + query + pack
${CTX_CMD_STATUS}           # Show index status
```

## When to use

- User asks to find files related to a topic
- User wants to understand codebase structure before a change
- User asks "what handles X?" or similar navigation queries
- Before making cross-cutting changes to multiple files

## Workflow

1. Run `${CTX_CMD_INDEX}` if index is stale (check with `${CTX_CMD_STATUS}`)
2. Run `${CTX_CMD_SEARCH}` to find relevant files
3. For full context: `${CTX_CMD_FULL_ZIP}`

## Options

- `--format {xml|zip}` — ZIP for files, XML for pasting
- `--budget N` — Token budget (default: 100000)
