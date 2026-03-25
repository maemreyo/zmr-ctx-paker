

---

## Code Packaging — ws-ctx-engine

This project uses **ws-ctx-engine** for intelligent code context packaging.

### Quick Commands

```bash
# Index this repository (first time only)
${CTX_CMD_INDEX}

# Query for context
${CTX_CMD_SEARCH}

# Full workflow
${CTX_CMD_PACK}
```

### When to Rebuild Index

If you see "Index is stale, rebuilding", the index will rebuild automatically. You can also manually rebuild:
```bash
rm -rf .ws-ctx-engine/
${CTX_CMD_INDEX}
```

### Output Location

- Index: `.ws-ctx-engine/`
- Query output: `output/` directory
