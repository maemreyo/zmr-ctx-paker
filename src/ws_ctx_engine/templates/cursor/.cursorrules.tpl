# ws-ctx-engine — Codebase Navigator

Use `ws-ctx-engine` before broad code exploration or cross-file changes.

## Commands

```bash
${CTX_CMD_INDEX}             # Build index (run once or after major changes)
${CTX_CMD_SEARCH}            # Find relevant files by topic
${CTX_CMD_STATUS}            # Check index freshness
${CTX_CMD_FULL_ZIP}          # Full context bundle
```

## When to use

- Locating files for a feature/domain quickly
- Understanding unfamiliar architecture before edits
- Investigating multi-file bugs or regressions

Prefer semantic search via `ws-ctx-engine search` over manual grep/glob for intent-driven discovery.
