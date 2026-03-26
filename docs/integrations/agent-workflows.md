# Agent Workflow Integration Guide

ws-ctx-engine is designed as a first-class context engine for code agents
(Claude Code, Windsurf, Cursor, Pulse, and similar tools).

---

## Phase-Aware Context Selection (`--mode`)

Agents work in cycles. Pass `--mode` to tune ranking for the current phase:

| Mode | Best for | Ranking strategy |
|------|----------|-----------------|
| `discovery` | Exploring an unfamiliar codebase | Directory trees + signatures; low token density |
| `edit` | Implementing a specific change | Full verbatim code; high token density |
| `test` | Writing or debugging tests | Test files + mocks boosted 2x |

```bash
# Discovery phase — lightweight overview
wsctx pack . --query "what does this codebase do" --mode discovery

# Edit phase — deep context for a specific bug
wsctx pack . --query "fix the auth bug" --mode edit

# Test phase — boost test files and mocks
wsctx pack . --query "write tests for login" --mode test
```

---

## Semantic Deduplication (`--session-id`)

Agents call the context tool multiple times within a session.  Sending the
same file twice wastes tokens.  Use `--session-id` to enable deduplication:

```bash
# First call — full content for all files
wsctx pack . --query "auth" --session-id my-session

# Second call — [DEDUPLICATED] markers replace already-seen files
wsctx pack . --query "auth" --session-id my-session

# Token report line in terminal output:
# ✓ Context packed (12,400 tokens) — 3 files deduplicated (saved ~9,200 tokens)
```

### Session management

```bash
# Clear a specific session
wsctx session clear --session-id my-session

# Clear ALL session caches in the repo
wsctx session clear .
```

### Disable deduplication

```bash
wsctx pack . --query "auth" --no-dedup
```

---

## AI Rule Persistence

Rule files like `.cursorrules`, `AI_RULES.md`, `AGENTS.md`, and
`.claude/instructions.md` are **always included** in every pack regardless
of the query, because they provide essential project context for agents.

This is automatic — no flags required.  To add custom rule files:

```yaml
# .ws-ctx-engine.yaml
ai_rules:
  auto_detect: true
  extra_files:
    - MY_RULES.md
    - .team-conventions.md
  boost: 10.0
```

---

## Combined Agent-Optimised Workflow

```bash
wsctx pack . \
  --query "fix the payment flow" \
  --mode edit \
  --session-id payment-fix-session \
  --compress \
  --agent-mode
```

This single command:
1. Retrieves files most relevant to "fix the payment flow"
2. Applies edit-phase weight overrides (verbatim code)
3. Deduplicates against previous calls in this session
4. Smart-compresses supporting files
5. Shuffles output for optimal model recall
6. Emits NDJSON to stdout (for agent consumption)
