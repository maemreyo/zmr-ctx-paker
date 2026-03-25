# ctx-packer for Windsurf

## Purpose
Use ctx-packer to retrieve relevant code context for AI-assisted coding tasks.

## Commands

### Index Repository
```bash
${CTX_CMD_INDEX}
```
Creates vector index, dependency graph, and domain map.

### Query Code
```bash
${CTX_CMD_QUERY} --format zip
${CTX_CMD_QUERY} --format xml
```

### Pack for AI Context
```bash
${CTX_CMD_PACK}
```

### Status Check
```bash
${CTX_CMD_STATUS}
```

## Use Cases

| Task | Command |
|------|---------|
| Code Review | `${CTX_CMD_FULL_ZIP}` |
| Bug Investigation | `${CTX_CMD_FULL_XML}` |
| Feature Context | `${CTX_CMD_FULL_ZIP} --budget 80000` |
| Documentation | `${CTX_CMD_QUERY} --format zip` |

## Tips

- Index once, reuse many times
- Use `--format xml` for pasting into web interfaces
- Adjust `--budget` for context size control
- Check `${CTX_CMD_STATUS}` for index health
