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
${CTX_CMD_INDEX}          # Build/update index for current dir
${CTX_CMD_QUERY}          # Search indexed codebase
${CTX_CMD_PACK}           # Full workflow: index + query + pack
${CTX_CMD_STATUS}         # Show index status
${CTX_CMD_VACUUM}         # Optimize SQLite database
```

## When to use

- User asks to find files related to a topic
- User wants to understand codebase structure before a change
- User asks "what handles authentication?" or similar navigation queries
- Before making cross-cutting changes to multiple files
- User wants to "package context for LLM" or "generate context bundle"

## Workflow

1. Run `${CTX_CMD_INDEX}` if index is stale or missing (check with `${CTX_CMD_STATUS}`)
2. Run `${CTX_CMD_QUERY}` to find relevant files
3. Use results to inform your next action
4. For full context bundle: `${CTX_CMD_FULL_ZIP}`

## Options

- `--format {xml|zip}` — ZIP for files, XML for pasting
- `--budget N` — Token budget (default: 100000)
- `--changed-files <path>` — For PR context

## Tips

- Index once, reuse many times
- Use natural language for semantic search
- ZIP output uploads to Cursor/Claude Code
- XML output pastes into web interfaces (Claude.ai)
