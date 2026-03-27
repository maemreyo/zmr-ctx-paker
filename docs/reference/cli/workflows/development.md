# Development Workflow

Daily development workflow for using ws-ctx-engine while coding.

## Typical Day in the Life

### Morning: Start Coding

```bash
# 1. Pull latest changes
git pull origin main

# 2. Quick incremental index (if needed)
ws-ctx-engine index . --incremental
```

### During Development

#### Finding Existing Code

**When you need to find something:**
```bash
# Search by concept
ws-ctx-engine search "how errors are handled"

# Get top results
ws-ctx-engine search "database connection pooling" -l 5
```

#### Understanding Context

**When implementing a feature:**
```bash
# Get relevant context
ws-ctx-engine query "similar authentication patterns" --copy

# Paste into LLM chat for assistance
```

#### Quick Exploration

**When exploring unfamiliar code:**
```bash
# Broad search
ws-ctx-engine search "routing mechanism"

# Then specific
ws-ctx-engine query "API route handlers" --format yaml
```

### After Making Changes

#### Update Indexes

```bash
# Fast incremental update
ws-ctx-engine index . --incremental

# Takes seconds, not minutes
```

#### Prepare for Review

```bash
# Generate review context
ws-ctx-engine query "my changes area" --compress --copy
```

## Common Scenarios

### Scenario 1: Bug Fix

```bash
# 1. Understand the bug
ws-ctx-engine search "payment processing error"

# 2. Find related code
ws-ctx-engine query "payment validation logic" --copy

# 3. After fixing
ws-ctx-engine index . --incremental

# 4. Verify fix context
ws-ctx-engine query "payment error handling" --copy
```

### Scenario 2: Feature Implementation

```bash
# 1. Explore existing patterns
ws-ctx-engine search "similar features"

# 2. Get implementation context
ws-ctx-engine query "authentication middleware examples" --budget 50000

# 3. Implement feature
# ... coding ...

# 4. Update indexes
ws-ctx-engine index . --incremental

# 5. Generate test context
ws-ctx-engine query "testing authentication" --mode test
```

### Scenario 3: Code Review

```bash
# 1. List your changes
git diff --name-only HEAD~1 > changed.txt

# 2. Generate review package
ws-ctx-engine pack . \
  -q "review these changes" \
  --changed-files changed.txt \
  --format markdown \
  --copy

# 3. Send to reviewer or LLM
```

### Scenario 4: Learning New Codebase

```bash
# Week 1: High-level understanding
ws-ctx-engine query "main application structure" --budget 75000
ws-ctx-engine query "core architecture" --format yaml

# Week 2: Specific areas
ws-ctx-engine search "authentication system"
ws-ctx-engine query "login flow implementation"

# Week 3: Deep dives
ws-ctx-engine query "auth middleware details" --compress
```

## Efficiency Tips

### Keep Indexes Fresh

**Quick check:**
```bash
ws-ctx-engine status .
```

**Incremental update (fast):**
```bash
ws-ctx-engine index . --incremental
# Time: ~2-5 seconds
```

**Full rebuild (when needed):**
```bash
ws-ctx-engine index .
# Time: ~30-60 seconds
```

### Use Sessions for Multi-Turn Work

```bash
# Start session
ws-ctx-engine query "explore auth system" --session-id dev-session

# Continue without repetition
ws-ctx-engine query "show me the middleware" --session-id dev-session

# More queries...
ws-ctx-engine query "what about tests?" --session-id dev-session

# End of day cleanup
ws-ctx-engine session clear --session-id dev-session
```

### Clipboard Integration

```bash
# Copy directly to clipboard
ws-ctx-engine query "my feature" --copy

# Or output to stdout for piping
ws-ctx-engine query "config" --stdout | grep pattern
```

### Format Selection by Use Case

**LLM Chat (XML):**
```bash
ws-ctx-engine query "implement feature" --format xml --copy
```

**Documentation (Markdown):**
```bash
ws-ctx-engine query "API docs" --format markdown --stdout > docs.md
```

**Machine Processing (JSON):**
```bash
ws-ctx-engine query "data models" --format json --agent-mode
```

## Keyboard Shortcuts & Aliases

### Useful Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Quick commands
alias wsidx='ws-ctx-engine index . --incremental'
alias wsq='ws-ctx-engine query'
alias wss='ws-ctx-engine search'
alias wsstatus='ws-ctx-engine status .'

# Full workflow
alias wspack='ws-ctx-engine pack . -q'
```

### Git Integration

```bash
# Function to review last commit
review_commit() {
  git diff --name-only HEAD~1 > /tmp/changed.txt
  ws-ctx-engine pack . -q "review changes" --changed-files /tmp/changed.txt --copy
}
```

## Best Practices

### Do's ✅

- Run incremental index after significant changes
- Use sessions for extended work on one topic
- Copy to clipboard for quick LLM integration
- Use appropriate token budgets
- Compress large contexts

### Don'ts ❌

- Don't full re-index every time (use `--incremental`)
- Don't skip index updates after major changes
- Don't use huge budgets for simple queries
- Don't forget to clean up sessions
- Don't ignore compression for large contexts

## Performance Optimization

### Fast Path (<1 second)

```bash
# Already indexed, just query
ws-ctx-engine query "quick check" --copy
```

### Standard Path (~2-5 seconds)

```bash
# Incremental update + query
ws-ctx-engine index . --incremental
ws-ctx-engine query "my feature" --copy
```

### Complete Path (~30-60 seconds)

```bash
# Full refresh
ws-ctx-engine index .
ws-ctx-engine query "comprehensive view" --budget 75000
```

## Troubleshooting

### "Query returns stale code"

**Solution:**
```bash
ws-ctx-engine index . --incremental
```

### "No results found"

**Try:**
```bash
# Broader search
ws-ctx-engine search "more general term"

# Check index
ws-ctx-engine status .

# Rebuild if needed
ws-ctx-engine index . --incremental
```

### "Too many results"

**Narrow down:**
```bash
# Limit results
ws-ctx-engine search "specific term" -l 5

# Use domain filter
ws-ctx-engine search "term" --domain-filter auth

# More specific query
ws-ctx-engine query "very specific aspect" --budget 20000
```

## Related Workflows

- [Initial Setup](initial-setup.md) - Getting started
- [CI/CD Integration](ci-cd.md) - Automation workflows
- [Agent Integration](agent-integration.md) - AI-powered development
