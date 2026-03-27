# Workflow Patterns

Common workflows and usage patterns for ws-ctx-engine.

## Quick Reference

| Workflow | Use Case | Commands |
|----------|----------|----------|
| [Initial Setup](initial-setup.md) | First-time configuration | `init-config` → `doctor` → `index` |
| [Development](development.md) | Daily development | `index --incremental` → `search` → `query` |
| [CI/CD Integration](ci-cd.md) | Automation pipelines | `pack` with changed files |
| [Agent Integration](agent-integration.md) | AI agent workflows | `mcp` or `query --agent-mode` |

## Workflow Categories

### 1. Setup Workflows
Getting started with ws-ctx-engine:
- Repository initialization
- Configuration generation
- Dependency verification
- Initial indexing

### 2. Development Workflows
Daily usage during coding:
- Incremental updates
- Quick searches
- Context generation
- Code exploration

### 3. Automation Workflows
CI/CD and scripting:
- Automated code review
- PR analysis
- Documentation generation
- Quality checks

### 4. Agent Workflows
AI-powered development:
- Multi-turn conversations
- Session management
- MCP server mode
- Deduplication tracking

## Choosing the Right Workflow

### For Individuals

**Learning a codebase:**
```bash
ws-ctx-engine init-config .
ws-ctx-engine index .
ws-ctx-engine search "main components"
ws-ctx-engine query "architecture overview" --copy
```

**Daily development:**
```bash
# After making changes
ws-ctx-engine index . --incremental
ws-ctx-engine query "my feature" --copy
```

### For Teams

**Code review process:**
```bash
git diff --name-only HEAD~1 > changed.txt
ws-ctx-engine pack . -q "review changes" \
  --changed-files changed.txt \
  --format markdown \
  --copy
```

**Onboarding new developers:**
```bash
ws-ctx-engine query "getting started guide" --format markdown
ws-ctx-engine query "main application flow" --budget 75000
```

### For CI/CD

**Automated PR review:**
```yaml
- name: Generate PR context
  run: |
    git diff --name-only ${{ github.event.before }} > changed.txt
    ws-ctx-engine pack . \
      -q "PR changes review" \
      --changed-files changed.txt \
      --format xml \
      --agent-mode
```

## Best Practices

### Index Management

**Build indexes:**
- Initial: Full index
- After major changes: Full index
- After minor changes: Incremental
- Before important queries: Verify freshness

**Maintain indexes:**
```bash
# Weekly maintenance
ws-ctx-engine vacuum .
ws-ctx-engine status .
```

### Query Optimization

**Token budgets:**
- Quick lookup: 10K tokens
- Standard context: 30K tokens
- Comprehensive: 50K+ tokens
- Full system: 100K+ tokens

**Format selection:**
- XML: Structured, parseable
- YAML: Human-readable
- Markdown: Documentation
- JSON: Machine processing

### Session Management

**Multi-turn workflows:**
```bash
# Turn 1
ws-ctx-engine query "exploration" --session-id session-1

# Turn 2 (deduplicated)
ws-ctx-engine query "deep dive" --session-id session-1

# Cleanup
ws-ctx-engine session clear --session-id session-1
```

## Performance Tips

### Fast Path
```bash
# Already indexed, quick query
ws-ctx-engine query "test" --copy
# Time: <1 second
```

### Optimized Path
```bash
# Incremental update first
ws-ctx-engine index . --incremental
ws-ctx-engine query "test"
# Time: ~2-5 seconds total
```

### Complete Path
```bash
# Fresh start
ws-ctx-engine init-config .
ws-ctx-engine doctor
ws-ctx-engine index .
ws-ctx-engine query "test"
# Time: ~30-60 seconds total
```

## Common Pitfalls

### ❌ Not Building Indexes First

```bash
# Wrong: Query without indexes
ws-ctx-engine query "test"
# Error: Indexes not found

# Right: Build indexes first
ws-ctx-engine index .
ws-ctx-engine query "test"
```

### ❌ Using Wrong Command

```bash
# Wrong: Using pack for simple search
ws-ctx-engine pack . -q "find auth code"

# Right: Use search for paths only
ws-ctx-engine search "auth code"

# Or query for full content
ws-ctx-engine query "auth code" --copy
```

### ❌ Ignoring Sessions

```bash
# Wrong: Repeating same content
ws-ctx-engine query "part 1"
ws-ctx-engine query "part 2"  # May include part 1 again

# Right: Track sessions
ws-ctx-engine query "part 1" --session-id s1
ws-ctx-engine query "part 2" --session-id s1  # Excludes part 1
```

## Related Documentation

- [Commands Overview](commands/README.md) - All available commands
- [Global Options](global-options.md) - CLI-wide settings
- [Examples](../../examples/README.md) - Practical examples
- [Integrations](../../integrations/README.md) - Tool integrations
