# Initial Setup Workflow

Complete guide for first-time ws-ctx-engine setup.

## Prerequisites

Before starting, ensure you have:
- Python 3.11+ installed
- Git repository to index
- ~5 minutes for initial setup

## Step-by-Step Guide

### Step 1: Install ws-ctx-engine

```bash
# Install with all recommended dependencies
pip install "ws-ctx-engine[all]"

# Or minimal installation
pip install ws-ctx-engine
```

### Step 2: Initialize Configuration

Navigate to your repository and generate configuration:

```bash
cd /path/to/your/repo
ws-ctx-engine init-config
```

This creates `.ws-ctx-engine.yaml` with intelligent defaults based on your project structure.

**What it does:**
- Detects programming languages
- Chooses optimal backends
- Sets up domain mappings
- Integrates gitignore patterns

### Step 3: Verify Dependencies

Check that all optional dependencies are available:

```bash
ws-ctx-engine doctor
```

**Expected output:**
```
Dependency Doctor
- faiss-cpu                 OK
- igraph                    OK
- networkx                  OK
- sentence-transformers     OK
- tree-sitter               OK
- tree-sitter-python        OK

All dependencies installed!
```

**If missing:**
```bash
# Install recommended dependencies
pip install "ws-ctx-engine[all]"
```

### Step 4: Build Indexes

Create semantic indexes for your codebase:

```bash
ws-ctx-engine index .
```

**First-time indexing:**
- Takes 30-60 seconds for medium projects
- Processes all source files
- Builds vector embeddings
- Creates dependency graph

**Progress output:**
```
Step 1: Discovering files...
  → Found 150 files

Step 2: Chunking code...
  → Created 450 chunks

Step 3: Generating embeddings...
  → [████████████] 100%

Step 4: Building graph...
  → Mapped 320 symbols

✓ Indexing complete!
```

### Step 5: Verify Setup

Check that indexes were created successfully:

```bash
ws-ctx-engine status .
```

**Expected output:**
```
Index Status for: /path/to/repo
Total size: 2.5 MB
Indexed Files: 150
Backend: FAISSIndex+NetworkXRepoMap
Last indexed: 2024-01-15T10:30:00
```

### Step 6: Test Search

Try a semantic search:

```bash
ws-ctx-engine search "authentication logic"
```

**Expected results:**
```
1. src/auth/login.py (score: 0.95)
2. src/auth/middleware.py (score: 0.89)
3. src/api/auth.py (score: 0.87)
```

### Step 7: Generate First Context

Test full query capability:

```bash
ws-ctx-engine query "user authentication flow" --copy
```

Context is now copied to clipboard, ready to paste into LLM chat.

## Quick Reference Card

```bash
# Complete setup sequence
cd /path/to/repo
pip install "ws-ctx-engine[all]"
ws-ctx-engine init-config
ws-ctx-engine doctor
ws-ctx-engine index .
ws-ctx-engine status .

# Test it works
ws-ctx-engine search "your query"
ws-ctx-engine query "your query" --copy
```

## Troubleshooting

### "Command not found"

**Problem:** ws-ctx-engine not in PATH

**Solution:**
```bash
# Reinstall with --user flag
pip install --user "ws-ctx-engine[all]"

# Or use full path
~/.local/bin/ws-ctx-engine init-config
```

### "No module named..."

**Problem:** Missing dependencies

**Solution:**
```bash
pip install --upgrade "ws-ctx-engine[all]"
```

### "Index build failed"

**Possible causes:**
- Insufficient disk space (need ~10MB per 1000 files)
- No write permissions in repo
- Unsupported file types

**Solutions:**
```bash
# Check disk space
df -h .

# Verify permissions
ls -la

# Review verbose output
ws-ctx-engine index . --verbose
```

### "No files to index"

**Causes:**
- Empty repository
- All files in gitignore
- Wrong directory

**Solutions:**
```bash
# Check for source files
find . -name "*.py" -o -name "*.js" -o -name "*.rs"

# Review gitignore
cat .gitignore

# Check .ws-ctx-engine.yaml exclude patterns
```

## Next Steps

After successful setup:

1. **Learn daily workflow**: See [Development Workflow](development.md)
2. **Explore commands**: See [Commands Overview](../commands/README.md)
3. **Set up AI agents**: See [Agent Integration](agent-integration.md)
4. **Configure CI/CD**: See [CI/CD Integration](ci-cd.md)

## Custom Configuration

After initial setup, you may want to customize `.ws-ctx-engine.yaml`:

```yaml
# Add custom domain keywords
domains:
  my_feature:
    - feature_keyword
    - related_term

# Adjust token budget
index:
  token_budget: 150000  # Increase from default 100000

# Change backends if needed
vector_index:
  backend: faiss  # or leann
```

## Related Workflows

- [Development Workflow](development.md) - Daily usage
- [CI/CD Integration](ci-cd.md) - Automation setup
- [Agent Integration](agent-integration.md) - AI agent workflows
