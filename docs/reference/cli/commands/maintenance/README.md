# Maintenance Commands

Maintenance commands help you manage, optimize, and maintain your ws-ctx-engine indexes.

## Available Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`vacuum`](vacuum.md) | Optimize SQLite database | Improve query performance |
| [`reindex-domain`](reindex-domain.md) | Rebuild domain map | Update domain keywords without full re-index |

## When to Use Maintenance Commands

### Regular Maintenance

**Weekly/Monthly:**
```bash
# Optimize database performance
ws-ctx-engine vacuum /path/to/repo
```

**After Domain Changes:**
```bash
# Update domain mappings
ws-ctx-engine reindex-domain /path/to/repo
```

### Performance Optimization

If you notice slower queries or large index sizes:

```bash
# Check status first
ws-ctx-engine status /path/to/repo

# Optimize if needed
ws-ctx-engine vacuum /path/to/repo
```

### Domain Management

When adding new modules or restructuring codebase:

```bash
# Rebuild domain mappings only (faster than full re-index)
ws-ctx-engine reindex-domain /path/to/repo
```

## Maintenance Schedule

### Light Usage (Small Projects)
- **Vacuum**: Monthly
- **Reindex-domain**: As needed when structure changes

### Heavy Usage (Large Projects)
- **Vacuum**: Weekly
- **Reindex-domain**: After major refactoring

### CI/CD Integration
```yaml
# Periodic maintenance in CI
- name: Maintain indexes
  run: |
    ws-ctx-engine vacuum .
    ws-ctx-engine index . --incremental
```

## Related Documentation

- [`status`](status.md) - Check index health before maintenance
- [`index`](index.md) - Full indexing vs partial re-indexing
- [Workflow](../workflow.md) - Index management workflows
