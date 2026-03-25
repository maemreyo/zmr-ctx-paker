---
description: >
  Guide for using ctx-packer to index and search the codebase.
  Apply when navigating unfamiliar code or before cross-file edits.
alwaysApply: false
---

# ctx-packer — Codebase Navigator

Before exploring unfamiliar areas of the codebase, use ctx-packer:

```bash
${CTX_CMD_INDEX}             # Build index (run once or after major changes)
${CTX_CMD_QUERY}             # Find relevant files by topic
${CTX_CMD_STATUS}            # Check if index is fresh
${CTX_CMD_FULL_ZIP}          # Full context bundle
```

## When to Use

- Finding files related to a specific feature or domain
- Understanding code structure before making changes
- Investigating bugs or errors
- Code review with targeted context

## Options

| Flag | Description |
|------|-------------|
| `--format zip` | ZIP output (for Cursor) |
| `--format xml` | XML output (for pasting) |
| `--budget N` | Token budget (default: 100k) |
| `--changed-files <path>` | Files changed in PR |

Prefer ctx-packer search over manual grep/glob for semantic queries.
