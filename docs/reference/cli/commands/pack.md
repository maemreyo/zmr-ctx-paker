# pack Command

Execute full workflow: index, query, and pack in one command.

## Usage

```bash
ws-ctx-engine pack [repo_path] [OPTIONS]
```

## Arguments

| Argument    | Default | Description             |
| ----------- | ------- | ----------------------- |
| `repo_path` | `.`     | Path to repository root |

## Options

| Option                   | Short | Default | Description                        |
| ------------------------ | ----- | ------- | ---------------------------------- |
| `--query`                | `-q`  | None    | Natural language query             |
| `--changed-files`        |       | None    | Path to file listing changed files |
| `--format`               | `-f`  | config  | Output format                      |
| `--budget`               | `-b`  | config  | Token budget                       |
| `--config`               | `-c`  | None    | Custom config path                 |
| `--verbose`              | `-v`  | False   | Verbose logging                    |
| `--secrets-scan`         |       | False   | Enable secret scanning             |
| `--agent-mode`           |       | False   | NDJSON output                      |
| `--stdout`               |       | False   | Output to stdout                   |
| `--copy`                 |       | False   | Copy to clipboard                  |
| `--compress`             |       | False   | Smart compression                  |
| `--shuffle/--no-shuffle` |       | True    | Model recall optimization          |
| `--mode`                 |       | None    | Agent phase mode                   |
| `--session-id`           |       | default | Session for dedup                  |
| `--no-dedup`             |       | False   | Disable deduplication              |

## Description

The `pack` command is the ultimate all-in-one command that combines indexing, searching, and packing into a single operation. It's perfect for automation and CI/CD workflows where you want a single command to generate context.

## Examples

### Full Pipeline with Query

```bash
# Pack entire repository with query
ws-ctx-engine pack /path/to/repo -q "authentication system"

# Pack current directory
ws-ctx-engine pack . -q "API layer"
```

### With Changed Files (PageRank Boost)

Boost relevance of recently changed files:

```bash
# List changed files
echo "src/auth.py" > changed.txt
ws-ctx-engine pack . -q "auth changes" --changed-files changed.txt

# Use git to get changed files
git diff --name-only HEAD~1 > changed.txt
ws-ctx-engine pack . -q "recent changes" --changed-files changed.txt
```

### Production Workflow

```bash
# Full production setup
ws-ctx-engine pack . -q "API layer" --format xml --compress --shuffle
```

### With Multiple Options

```bash
# Comprehensive pack with all features
ws-ctx-engine pack /path/to/repo \
  -q "payment processing" \
  --format yaml \
  --budget 75000 \
  --compress \
  --copy \
  --secrets-scan
```

### Agent Mode Automation

```bash
# Agent mode with session tracking
ws-ctx-engine pack . -q "fix bug" --agent-mode --session-id agent-session-1

# CI/CD pipeline
ws-ctx-engine pack . -q "code review" --agent-mode --format xml
```

## When to Use

✅ **Use `pack` when:**
- Running automated workflows
- CI/CD integration
- Single-command simplicity needed
- Setting up new repositories
- Quick full-repository context

❌ **Use separate commands when:**
- Indexes already exist and are fresh
- You need fine-grained control over each step
- Debugging specific stages

## Workflow Stages

The `pack` command executes these stages automatically:

### Stage 1: Check/Build Indexes
- Verifies indexes exist
- Auto-rebuilds if stale (optional)
- Uses incremental indexing when possible

### Stage 2: Search and Retrieve
- Executes semantic search
- Ranks results by relevance
- Applies PageRank scoring

### Stage 3: Process and Format
- Retrieves full file content
- Applies token budget
- Formats output

### Stage 4: Optimize and Output
- Applies compression (if enabled)
- Scans for secrets (if enabled)
- Writes to destination

## Common Workflows

### Initial Repository Setup

```bash
# First-time setup and pack
ws-ctx-engine pack /path/to/repo -q "system overview"
```

### Daily Development

```bash
# After making changes
ws-ctx-engine pack . -q "my feature" --changed-files <(git diff --name-only) --copy
```

### Code Review Preparation

```bash
# Generate review context
git diff --name-only HEAD~1 > changed.txt
ws-ctx-engine pack . -q "review changes" --changed-files changed.txt --format markdown
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Generate context
  run: |
    git diff --name-only ${{ github.event.before }} > changed.txt
    ws-ctx-engine pack . -q "PR changes" --changed-files changed.txt --format xml
```

### Automated Documentation

```bash
# Generate API documentation
ws-ctx-engine pack . -q "public API endpoints" --format markdown --stdout > docs/api.md
```

## Changed Files Feature

The `--changed-files` option boosts ranking of modified files using PageRank:

**Benefits:**
- Prioritizes recent changes
- Improves relevance for code review
- Helps AI focus on modified areas

**Usage:**
```bash
# Single file
echo "src/auth.py" > changed.txt
ws-ctx-engine pack . -q "auth" --changed-files changed.txt

# Multiple files
cat <<EOF > changed.txt
src/auth.py
src/middleware.py
tests/test_auth.py
EOF
ws-ctx-engine pack . -q "authentication" --changed-files changed.txt

# Git integration
git diff --name-only HEAD~1 > changed.txt
ws-ctx-engine pack . -q "changes" --changed-files changed.txt
```

## Performance Optimization

### Fast Path (Indexes Exist)
```bash
# If indexes are fresh, pack is very fast
ws-ctx-engine pack . -q "quick check"
```

### Full Rebuild Path
```bash
# If indexes missing/stale, auto-rebuilds
ws-ctx-engine pack /path/to/repo -q "full analysis"
```

### Optimized for Size
```bash
# Minimize output size
ws-ctx-engine pack . -q "summary" --compress --budget 30000
```

### Optimized for Completeness
```bash
# Maximum context
ws-ctx-engine pack . -q "comprehensive view" --budget 100000 --no-shuffle
```

## Output Control

### File Output (Default)
Saves to configured output location

### Clipboard
```bash
ws-ctx-engine pack . -q "snippet" --copy
```

### Stdout (for piping)
```bash
ws-ctx-engine pack . -q "config" --stdout | grep pattern
```

### Agent Mode (NDJSON)
```bash
ws-ctx-engine pack . -q "data" --agent-mode
```

## Error Handling

**"Indexes not found"**
- Automatically attempts to build indexes
- May take longer on first run

**"Query returned no results"**
- Try broader query terms
- Check index freshness
- Verify repository structure

**"Token budget exceeded"**
- Increase budget with `--budget`
- Enable `--compress`
- Narrow query scope

## Best Practices

### For Code Reviews
```bash
git diff --name-only HEAD~1 > changed.txt
ws-ctx-engine pack . -q "review these changes" \
  --changed-files changed.txt \
  --format markdown \
  --copy
```

### For Feature Implementation
```bash
ws-ctx-engine pack . -q "existing similar patterns" \
  --format xml \
  --budget 50000
```

### For Bug Fixes
```bash
ws-ctx-engine pack . -q "error handling in affected area" \
  --compress \
  --secrets-scan \
  --copy
```

### For Learning Codebase
```bash
ws-ctx-engine pack . -q "main application flow" \
  --format yaml \
  --budget 75000
```

## Related Commands

- [`index`](index.md) - Build indexes separately
- [`query`](query.md) - Query without indexing
- [`search`](search.md) - Search only

## Related Documentation

- [Workflow](../workflow.md) - Detailed workflow stages
- [CI/CD Guide](../guides/ci-cd.md) - Automation examples
- [Token Budget](../budget.md) - Budget management
- [Compression](../guides/compression.md) - Size optimization
