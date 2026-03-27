# session clear Command

Delete session deduplication cache files.

## Usage

```bash
ws-ctx-engine session clear [repo_path] [OPTIONS]
```

## Arguments

| Argument    | Default | Description     |
| ----------- | ------- | --------------- |
| `repo_path` | `.`     | Repository root |

## Options

| Option         | Description                     |
| -------------- | ------------------------------- |
| `--session-id` | Clear only this session's cache |

## Description

The `session clear` command removes deduplication cache files created during agent sessions. This helps manage disk space and clean up after completed workflows.

## When to Use

✅ **Run `session clear` when:**
- Agent session has completed
- Disk space needs reclaiming
- Troubleshooting session issues
- Starting fresh session

❌ **Don't need to run:**
- After every single query
- During active multi-turn sessions
- If planning to continue session

## Examples

### Clear All Sessions

```bash
# Remove all session caches for current repo
ws-ctx-engine session clear

# Remove for specific repo
ws-ctx-engine session clear /path/to/repo
```

### Clear Specific Session

```bash
# Remove only one session's cache
ws-ctx-engine session clear --session-id agent-123

# With repo path
ws-ctx-engine session clear /path/to/repo --session-id review-session
```

### Workflow Example

```bash
# Start agent workflow
ws-ctx-engine query "initial exploration" --session-id agent-123

# Continue with deduplication
ws-ctx-engine query "deeper dive" --session-id agent-123

# More queries...
ws-ctx-engine query "specific area" --session-id agent-123

# Cleanup when done
ws-ctx-engine session clear --session-id agent-123
```

## Cache Location

Session caches are stored in:
```
.ws-ctx-engine/sessions/{session_id}/
```

Cache contents:
- File hashes seen during session
- Query history
- Content fingerprints
- Metadata (timestamps, sizes)

## Cache Size

Typical session cache sizes:
- Small session: 10-50 KB
- Medium session: 50-200 KB
- Large session: 200 KB - 1 MB

**Regular cleanup recommended** to prevent accumulation.

## Common Scenarios

### Scenario 1: Daily Cleanup

```bash
# End of day cleanup
ws-ctx-engine session clear
```

### Scenario 2: Failed Session

```bash
# Session got corrupted or stuck
ws-ctx-engine session clear --session-id failed-session
# Start fresh
ws-ctx-engine query "retry" --session-id new-session
```

### Scenario 3: Multiple Agents

```bash
# Clean specific agent's old sessions
ws-ctx-engine session clear --session-id claude-old-session

# Keep other sessions intact
```

### Scenario 4: CI/CD Pipeline

```yaml
# GitHub Actions
- name: Cleanup sessions
  run: |
    ws-ctx-engine session clear
    
- name: Run agent
  run: |
    ws-ctx-engine query "review PR" --session-id ci-run
```

## Deduplication Behavior

### With Session Tracking

```bash
# Query 1: Returns files A, B, C
ws-ctx-engine query "auth system" --session-id s1

# Query 2: Returns files D, E (excludes A, B, C)
ws-ctx-engine query "auth tests" --session-id s1

# Query 3: Returns files F (excludes A, B, C, D, E)
ws-ctx-engine query "auth middleware" --session-id s1
```

### Without Session Tracking

```bash
# Each query independent, may return same files
ws-ctx-engine query "auth system"
ws-ctx-engine query "auth tests"      # May include files from query 1
ws-ctx-engine query "auth middleware" # May include files from both
```

## Performance Impact

**Benefits of regular cleanup:**
- Reduced disk usage
- Faster session initialization
- Cleaner state management

**No impact on:**
- Query performance
- Index performance
- Other sessions

## Troubleshooting

**"No sessions to clear"**
- No active session caches exist
- Already cleaned up
- Never used sessions

**"Session not found"**
- Invalid session-id provided
- Session already expired
- Typo in session name

**"Clear failed"**
- Check file permissions
- Ensure no process using cache
- Verify disk space

## Best Practices

### Session Naming

Use descriptive names:
```bash
# Good
--session-id code-review-2024-01-15
--session-id feature-auth-implementation
--session-id bugfix-payment-issue-123

# Avoid
--session-id test
--session-id abc123
```

### Cleanup Frequency

**Individual developers:**
- End of each work session
- When switching contexts
- Daily at minimum

**Teams/CI:**
- After each pipeline run
- Nightly automated cleanup
- Per-build sessions

### Session Lifecycle Management

```bash
# 1. Start with clear purpose
ws-ctx-engine query "PR #456 changes" --session-id pr-456-review

# 2. Use throughout workflow
ws-ctx-engine query "related tests" --session-id pr-456-review

# 3. Clean when done
ws-ctx-engine session clear --session-id pr-456-review
```

## Related Commands

- [`query`](query.md) - Uses session tracking
- [`pack`](pack.md) - Also supports sessions
- [`status`](status.md) - Can show session info

## Related Documentation

- [Agent Workflows](../../integrations/agent-workflows.md) - Session usage patterns
- [Query Command](query.md) - Session options
- [MCP Server](server/mcp.md) - Session management in server mode
