

---

## Code Packaging — ctx-packer

This project uses **ctx-packer** for intelligent code context packaging.

### Quick Commands

```bash
# Index this repository (first time only)
ctx-packer index .

# Query for context
ctx-packer query "your search" --format zip

# Full workflow
ctx-packer pack . --query "your search"
```

### When to Rebuild Index

If you see "Index is stale, rebuilding", the index will rebuild automatically. You can also manually rebuild:
```bash
rm -rf .context-pack/
ctx-packer index .
```

### Output Location

- Index: `.context-pack/`
- Query output: `output/` directory
