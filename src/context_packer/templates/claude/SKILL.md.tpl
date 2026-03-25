---
name: ctx-packer
description: >
  Use when user wants to search, index, or pack codebase context for AI.
  Triggers on: "find files about X", "pack context for X", "index the codebase",
  "search codebase for Y", "what files handle Z", "understand this codebase".
user-invocable: true
---

# ctx-packer Skill

ctx-packer indexes your codebase and builds context bundles for AI agents.

## Commands

```bash
ctx-packer index .          # Build/update index for current dir
ctx-packer query "<query>"  # Search indexed codebase
ctx-packer pack . --query "<query>"  # Full workflow: index + query + pack
ctx-packer status           # Show index status
ctx-packer vacuum           # Optimize SQLite database
```

## When to use

- User asks to find files related to a topic
- User wants to understand codebase structure before a change
- User asks "what handles authentication?" or similar navigation queries
- Before making cross-cutting changes to multiple files
- User wants to "package context for LLM" or "generate context bundle"

## Workflow

1. Run `ctx-packer index .` if index is stale or missing (check with `ctx-packer status`)
2. Run `ctx-packer query "<query>"` to find relevant files
3. Use results to inform your next action
4. For full context bundle: `ctx-packer pack . --query "<topic>" --format zip`

## Options

- `--format {xml|zip}` — ZIP for files, XML for pasting
- `--budget N` — Token budget (default: 100000)
- `--changed-files <path>` — For PR context

## Tips

- Index once, reuse many times
- Use natural language for semantic search
- ZIP output uploads to Cursor/Claude Code
- XML output pastes into web interfaces (Claude.ai)
