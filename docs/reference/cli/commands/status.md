# status Command

Show index status and statistics.

## Usage

```bash
ws-ctx-engine status <repo_path> [OPTIONS]
```

## Arguments

| Argument    | Description             | Required |
| ----------- | ----------------------- | -------- |
| `repo_path` | Path to repository root | Yes      |

## Options

| Option         | Short | Description        |
| -------------- | ----- | ------------------ |
| `--config`     | `-c`  | Custom config path |
| `--agent-mode` |       | NDJSON output      |

## Description

The `status` command displays comprehensive information about your indexed repository, including index size, file counts, backend information, and last update time.

## Output Example

### Human Mode (Default)

```
Index Status for: /path/to/repo
Index directory: /path/to/repo/.ws-ctx-engine
Total size: 2.5 MB

Indexed Files: 150
Backend: FAISSIndex+NetworkXRepoMap
Vector index size: 1.8 MB
Graph index size: 0.5 MB
Domain map DB size: 0.2 MB
Domain keywords: 45
Domain directories: 23

Last indexed: 2024-01-15T10:30:00
```

### Agent Mode (--agent-mode)

```json
{
  "type": "status",
  "repo_path": "/path/to/repo",
  "index_directory": "/path/to/repo/.ws-ctx-engine",
  "total_size_bytes": 2621440,
  "indexed_files": 150,
  "backend": "FAISSIndex+NetworkXRepoMap",
  "vector_index_size_bytes": 1887436,
  "graph_index_size_bytes": 524288,
  "domain_map_size_bytes": 209715,
  "domain_keywords": 45,
  "domain_directories": 23,
  "last_indexed": "2024-01-15T10:30:00Z"
}
```

## When to Use

✅ **Use `status` when:**
- Checking if indexes exist
- Verifying index freshness
- Monitoring index size growth
- Debugging indexing issues
- Before running queries

❌ **Don't need to run:**
- Before every command (indexes are auto-checked)
- During normal development flow

## Information Provided

### Basic Information
- **Repository path**: Root directory being indexed
- **Index directory**: Location of index files (`.ws-ctx-engine/`)
- **Total size**: Combined size of all index components

### Index Statistics
- **Indexed files**: Number of source files in index
- **Backend**: Vector and graph backend implementations
- **Vector index size**: Size of embedding index
- **Graph index size**: Size of dependency graph
- **Domain map size**: Size of domain keyword database

### Domain Information
- **Domain keywords**: Number of tracked domain keywords
- **Domain directories**: Number of domain-mapped directories

### Timestamps
- **Last indexed**: When indexes were last built/updated

## Examples

### Basic Status Check

```bash
# Check status of current directory
ws-ctx-engine status .

# Check specific repository
ws-ctx-engine status /path/to/repo
```

### With Custom Configuration

```bash
ws-ctx-engine status /path/to/repo -c custom-config.yaml
```

### Machine-Readable Output

```bash
ws-ctx-engine status /path/to/repo --agent-mode
```

## Interpreting Results

### Healthy Index

```
✓ Indexed Files: >0
✓ Total size: Reasonable for repo size (1-10 MB typical)
✓ Last indexed: Recent timestamp
✓ Backend: Shows active backends
```

### Stale or Missing Index

```
⚠ Indexed Files: 0 (or very low)
⚠ Total size: Very small or 0
⚠ Last indexed: Old timestamp or missing
```

**Action needed:** Run `ws-ctx-engine index /path/to/repo`

### Large Index Size

```
⚠ Total size: >50 MB (for moderate repos)
```

**Possible actions:**
- Run `vacuum` to optimize database
- Review gitignore patterns
- Check for duplicate indexing

## Common Scenarios

### First Time Check

```bash
# New repository - check if indexes exist
ws-ctx-engine status .
# If missing, build indexes
ws-ctx-engine index .
```

### Before Query

```bash
# Verify indexes are fresh
ws-ctx-engine status .
# Then query
ws-ctx-engine query "my feature"
```

### After Major Changes

```bash
# Check if re-indexing needed
ws-ctx-engine status .
# If old, rebuild
ws-ctx-engine index . --incremental
```

### Performance Investigation

```bash
# Check index sizes
ws-ctx-engine status . --verbose
# If large, optimize
ws-ctx-engine vacuum .
```

## Maintenance Recommendations

Based on status output:

**If total size > 50MB:**
```bash
ws-ctx-engine vacuum /path/to/repo
```

**If last indexed > 1 week ago:**
```bash
ws-ctx-engine index . --incremental
```

**If indexed files = 0:**
```bash
ws-ctx-engine index .
```

**If domain keywords = 0:**
```bash
ws-ctx-engine reindex-domain .
```

## Troubleshooting

**"Indexes not found"**
- Run `index` command to build indexes
- Verify repo_path is correct

**"Index directory does not exist"**
- Repository hasn't been indexed yet
- Run `ws-ctx-engine index <repo_path>`

**Unexpectedly small index size**
- Check gitignore patterns in config
- Verify supported file types in repo
- Ensure indexing completed successfully

## Related Commands

- [`index`](index.md) - Build new indexes
- [`vacuum`](maintenance/vacuum.md) - Optimize database
- [`query`](query.md) - Query indexed codebase

## Related Documentation

- [Workflow](../workflow.md) - Indexing process details
- [Vector Index](../vector-index.md) - Vector storage details
- [Graph](../graph.md) - Graph implementation
