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
ctx-packer index .          # Build/update index for current dir
ctx-packer query "<query>" # Search indexed codebase
ctx-packer pack . --query "<query>"  # Full workflow: index + query + pack
ctx-packer status           # Show index status
```

## When to use

- User asks to find files related to a topic
- User wants to understand codebase structure before a change
- User asks "what handles X?" or similar navigation queries
- Before making cross-cutting changes to multiple files

## Workflow

1. Run `ctx-packer index .` if index is stale (check with `ctx-packer status`)
2. Run `ctx-packer query "<query>"` to find relevant files
3. For full context: `ctx-packer pack . --query "<topic>" --format zip`

## Options

- `--format {xml|zip}` — ZIP for files, XML for pasting
- `--budget N` — Token budget (default: 100000)
