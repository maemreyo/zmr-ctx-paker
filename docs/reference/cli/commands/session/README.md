# Session Commands

Session commands manage deduplication caches and session state for AI agent workflows.

## Available Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`session clear`](session-clear.md) | Delete session deduplication cache files | Cleanup after agent sessions |

## Overview

Session management is crucial for AI agent workflows where you want to track what content has already been seen across multiple queries.

## How Sessions Work

### Deduplication Cache

When using `--session-id`, ws-ctx-engine tracks:
- Files already returned in previous queries
- Content hashes to detect duplicates
- Query history for context

### Session Lifecycle

1. **Create**: First query with `--session-id` creates cache
2. **Track**: Subsequent queries avoid returning same content
3. **Clear**: Manual cleanup when session ends

## Common Patterns

### Multi-Turn Agent Workflow

```bash
# Turn 1: Initial exploration
ws-ctx-engine query "auth system" --session-id agent-123

# Turn 2: Deep dive (avoids repeating turn 1 content)
ws-ctx-engine query "auth tests" --session-id agent-123

# Turn 3: More specific (avoids turns 1 & 2)
ws-ctx-engine query "auth middleware" --session-id agent-123

# Cleanup when done
ws-ctx-engine session clear --session-id agent-123
```

### Parallel Agent Sessions

```bash
# Session 1: Code review
ws-ctx-engine query "recent changes" --session-id review-session

# Session 2: Bug fix (separate tracking)
ws-ctx-engine query "payment bug" --session-id bugfix-session

# Clean both sessions
ws-ctx-engine session clear
```

## Related Documentation

- [`session clear`](session-clear.md) - Session cleanup command
- [Agent Integration](../../integrations/agent-workflows.md) - Agent workflow patterns
- [Query Command](query.md) - Session usage in queries
