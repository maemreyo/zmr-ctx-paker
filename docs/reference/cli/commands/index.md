# index Command

Build and save indexes for a repository.

## Usage

```bash
ws-ctx-engine index <repo_path> [OPTIONS]
```

## Arguments

| Argument    | Description                           | Required |
| ----------- | ------------------------------------- | -------- |
| `repo_path` | Path to the repository root directory | Yes      |

## Options

| Option          | Short | Default | Description                       |
| --------------- | ----- | ------- | --------------------------------- |
| `--config`      | `-c`  | None    | Path to custom configuration file |
| `--verbose`     | `-v`  | False   | Enable verbose logging            |
| `--incremental` |       | False   | Only re-index changed files (M6)  |

## Description

The `index` command builds semantic indexes for your codebase, enabling fast and accurate code search. It processes your repository to create:

1. **Vector Index** - Semantic embeddings for code chunks
2. **Graph Index** - Dependency relationships between code elements
3. **Domain Map** - Keyword-to-domain mappings for filtering

## Examples

### Basic Indexing

```bash
# Index current directory
ws-ctx-engine index .

# Index specific repository
ws-ctx-engine index /path/to/repo
```

### Incremental Indexing

After making code changes, use incremental mode to only re-index modified files:

```bash
ws-ctx-engine index /path/to/repo --incremental
```

This is significantly faster than full re-indexing and preserves existing index data.

### With Custom Configuration

```bash
ws-ctx-engine index /path/to/repo -c custom-config.yaml
```

### Verbose Output

```bash
ws-ctx-engine index /path/to/repo --verbose
```

## When to Use

✅ **Run `index` when:**
- Setting up a new repository
- After significant code changes (without `--incremental`)
- After minor changes (with `--incremental`)
- When indexes become stale or corrupted

❌ **Don't need to run:**
- Before every search (indexes are reused)
- For read-only queries on stable codebases

## Index Components

### Vector Index
- Stores semantic embeddings of code chunks
- Enables similarity search
- Size: Typically 1-5 MB per 1000 files

### Graph Index
- Represents code dependencies
- Enables PageRank-based ranking
- Built using AST analysis

### Domain Map
- Maps keywords to code domains/modules
- Enables domain filtering
- Stored in SQLite database

## Performance Tips

**Initial indexing:**
- First-time indexing takes longest
- Expect ~1-2 seconds per file
- Run without `--incremental`

**Subsequent indexing:**
- Use `--incremental` for speed
- Only processes changed files
- Much faster than full rebuild

**Optimization:**
- Run `vacuum` periodically to optimize database
- Use `status` to monitor index health

## Common Workflows

### Initial Setup
```bash
ws-ctx-engine init-config /path/to/repo
ws-ctx-engine doctor
ws-ctx-engine index /path/to/repo
```

### After Code Changes
```bash
# Make your changes
git add .
ws-ctx-engine index . --incremental
```

### Full Rebuild
```bash
# When indexes are stale or corrupted
ws-ctx-engine index /path/to/repo
```

## Error Messages

**"Indexes not found"**
- Run `index` command first
- Check that repo_path is correct

**"No files to index"**
- Verify repository has supported file types
- Check gitignore patterns in config

**"Index build failed"**
- Check disk space
- Verify write permissions
- Review verbose output for details

## Related Commands

- [`status`](status.md) - Check index status and statistics
- [`search`](search.md) - Search indexed codebase
- [`query`](query.md) - Query and generate context
- [`vacuum`](maintenance/vacuum.md) - Optimize index database

## Related Documentation

- [Workflow](../workflow.md) - Indexing workflow details
- [Vector Index](../vector-index.md) - Vector index implementation
- [Graph](../graph.md) - Graph index implementation
- [Chunker](../chunker.md) - Code chunking process
