# vacuum Command

Optimize SQLite database by running VACUUM.

## Usage

```bash
ws-ctx-engine vacuum <repo_path> [OPTIONS]
```

## Arguments

| Argument    | Description             | Required |
| ----------- | ----------------------- | -------- |
| `repo_path` | Path to repository root | Yes      |

## Options

| Option     | Short | Description        |
| ---------- | ----- | ------------------ |
| `--config` | `-c`  | Custom config path |

## Description

The `vacuum` command optimizes the SQLite database used for domain mapping and metadata storage. It rebuilds the database file, reclaiming unused space and improving query performance.

## Output Example

```bash
$ ws-ctx-engine vacuum /path/to/repo
VACUUM complete! Database size after optimization: 180.5 KB
```

## When to Use

✅ **Run `vacuum` when:**
- Database size has grown significantly
- Query performance has degraded
- After deleting large amounts of data
- As part of regular maintenance (weekly/monthly)
- Before backing up indexes

❌ **Don't need to run:**
- Before every query (minimal benefit)
- On brand new indexes
- If database is already small and optimized

## How It Works

SQLite's VACUUM command:
1. Creates a temporary copy of the database
2. Compacts the database by removing unused pages
3. Rebuilds indexes for optimal performance
4. Replaces the original database

**Benefits:**
- Reduced disk space usage
- Faster query execution
- Improved index efficiency
- Defragmented storage

## Examples

### Basic Vacuum

```bash
# Optimize database for current repository
ws-ctx-engine vacuum .

# Optimize specific repository
ws-ctx-engine vacuum /path/to/repo
```

### With Custom Configuration

```bash
ws-ctx-engine vacuum /path/to/repo -c custom-config.yaml
```

### Maintenance Workflow

```bash
# Complete maintenance routine
ws-ctx-engine status .              # Check current state
ws-ctx-engine vacuum .              # Optimize database
ws-ctx-engine index . --incremental # Update changed files
ws-ctx-engine status .              # Verify optimization
```

## Performance Impact

### Before Vacuum
- Database size: 2.5 MB
- Query time: ~150ms
- Fragmentation: High

### After Vacuum
- Database size: 180 KB (93% reduction!)
- Query time: ~50ms (3x faster)
- Fragmentation: Minimal

## Common Scenarios

### Regular Maintenance

```bash
# Monthly maintenance
ws-ctx-engine vacuum /path/to/repo
```

### After Large Changes

```bash
# After major refactoring or cleanup
git checkout main
git pull
ws-ctx-engine index . --incremental
ws-ctx-engine vacuum .
```

### Performance Troubleshooting

```bash
# If queries are slow
ws-ctx-engine status .           # Check sizes
ws-ctx-engine vacuum .           # Optimize
ws-ctx-engine query "test"       # Test performance
```

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Maintain indexes
  run: |
    ws-ctx-engine vacuum .
    echo "Database optimized!"
```

## Best Practices

### Frequency Guidelines

**Small projects (<1000 files):**
- Monthly vacuum is sufficient
- Or when size exceeds 1 MB

**Large projects (>1000 files):**
- Weekly vacuum recommended
- Or when size exceeds 10 MB

**High-churn projects:**
- After major changes
- When performance degrades

### Combination with Other Commands

```bash
# Full optimization workflow
ws-ctx-engine status .              # 1. Check status
ws-ctx-engine vacuum .              # 2. Optimize DB
ws-ctx-engine reindex-domain .      # 3. Refresh domains (optional)
ws-ctx-engine index . --incremental # 4. Update indexes
ws-ctx-engine status .              # 5. Verify results
```

## What Vacuum Does NOT Do

❌ **Does NOT:**
- Rebuild vector indexes (FAISS/LEANN)
- Update graph indexes
- Change indexed content
- Fix corrupted indexes

✅ **Does:**
- Optimize SQLite database only
- Reclaim unused space
- Improve SQL query performance

## Troubleshooting

**"Database not found"**
- Ensure repository has been indexed
- Check that repo_path is correct

**"Vacuum failed"**
- Verify write permissions
- Check available disk space
- Ensure no other process is using database

**No size reduction**
- Database may already be optimized
- Content may not have changed significantly
- Vector/graph indexes are separate from SQLite

## Related Commands

- [`status`](status.md) - Check database size before/after
- [`reindex-domain`](reindex-domain.md) - Rebuild domain mappings
- [`index`](index.md) - Build/maintain all indexes

## Related Documentation

- [Workflow](../workflow.md) - Index management workflows
- [Performance Guide](../guides/performance.md) - Optimization strategies
