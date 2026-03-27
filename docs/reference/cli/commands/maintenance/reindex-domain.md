# reindex-domain Command

Rebuild only the domain map database (SQLite).

## Usage

```bash
ws-ctx-engine reindex-domain <repo_path> [OPTIONS]
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

The `reindex-domain` command rebuilds only the domain map database without recreating vector or graph indexes. This is useful when you need to update domain keyword mappings but want to avoid the overhead of a full re-index.

## Use Case

Use this command when:
- Domain keywords have changed
- Directory structure has been modified
- You want faster re-indexing than full rebuild
- Only domain mappings need updating

## What Gets Rebuilt

### Domain Map Database
- Keyword-to-domain mappings
- Directory categorizations
- Module classifications

### What Stays Intact
- Vector index (FAISS/LEANN)
- Graph index (NetworkX/igraph)
- File embeddings
- Dependency graphs

## Examples

### Basic Reindex

```bash
# Rebuild domain map for current directory
ws-ctx-engine reindex-domain .

# Rebuild for specific repository
ws-ctx-engine reindex-domain /path/to/repo
```

### With Custom Configuration

```bash
ws-ctx-engine reindex-domain /path/to/repo -c custom-config.yaml
```

### After Restructuring

```bash
# After moving files between modules
git mv src/auth/ src/authentication/
git commit -m "Restructure auth module"
ws-ctx-engine reindex-domain .
```

## When to Use

✅ **Use `reindex-domain` when:**
- Renaming directories/modules
- Adding new domain keywords to config
- Changing domain classification rules
- Domain mappings are stale
- Want faster alternative to full re-index

❌ **Use full `index` instead when:**
- Code content has changed significantly
- New files added (need embeddings)
- Dependencies changed (need graph update)
- Indexes are corrupted or missing

## Performance Comparison

### Full Index
```bash
time ws-ctx-engine index .
# Typical: 30-60 seconds for medium repo
```

### Domain Reindex Only
```bash
time ws-ctx-engine reindex-domain .
# Typical: 2-5 seconds (10x faster!)
```

## Common Scenarios

### Scenario 1: Directory Rename

```bash
# Before: src/api/
# After: src/apiserver/

git mv src/api src/apiserver
git commit -m "Rename api directory"
ws-ctx-engine reindex-domain .
```

### Scenario 2: New Domain Keywords

```yaml
# Updated .ws-ctx-engine.yaml
domains:
  authentication:
    - "auth"
    - "login"
    - "jwt"        # ← New keyword
    - "session"    # ← New keyword
```

After adding keywords:
```bash
ws-ctx-engine reindex-domain .
```

### Scenario 3: Module Reclassification

```bash
# Moving utils into specific domains
mv src/utils/crypto.py src/auth/
mv src/utils/http.py src/api/

ws-ctx-engine reindex-domain .
```

## Workflow Integration

### Quick Maintenance

```bash
# Fast domain refresh
ws-ctx-engine reindex-domain .
ws-ctx-engine status .  # Verify
```

### After Refactoring

```bash
# Major restructuring
git add .
git commit -m "Refactor module structure"
ws-ctx-engine reindex-domain .  # Update domains
ws-ctx-engine index . --incremental  # Update code changes
```

### Selective Updates

```bash
# Only domains changed, code stable
ws-ctx-engine reindex-domain .
# Skip full re-index if code unchanged
```

## Domain Map Details

### What It Contains

**Domain Keywords:**
- Authentication terms → auth domain
- API terms → server domain
- Database terms → data domain

**Directory Mappings:**
- `src/auth/` → authentication domain
- `src/api/` → server domain
- `src/db/` → data domain

**Module Classifications:**
- Python modules categorized by purpose
- JavaScript packages by function
- Rust crates by role

### Size Expectations

Typical domain map sizes:
- Small project: 50-100 KB
- Medium project: 100-300 KB
- Large project: 300 KB - 1 MB

## Troubleshooting

**"No domain keywords found"**
- Check `.ws-ctx-engine.yaml` configuration
- Verify domain section exists
- Ensure keywords are properly formatted

**"Domain map still stale"**
- May need full re-index
- Check file permissions
- Review config for errors

**"Command not recognized"**
- Ensure using latest version
- Check CLI help: `ws-ctx-engine --help`

## Related Commands

- [`index`](index.md) - Full indexing including domains
- [`status`](status.md) - Check domain map status
- [`vacuum`](vacuum.md) - Optimize domain database

## Related Documentation

- [Configuration](../configuration.md) - Domain keyword config
- [Workflow](../workflow.md) - Domain mapping process
- [Retrieval](../retrieval.md) - How domains affect search
