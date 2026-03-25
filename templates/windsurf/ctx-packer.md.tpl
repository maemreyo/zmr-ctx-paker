# ctx-packer for Windsurf

## Purpose
Use ctx-packer to retrieve relevant code context for AI-assisted coding tasks.

## Commands

### Index Repository
```bash
ctx-packer index .
```
Creates vector index, dependency graph, and domain map.

### Query Code
```bash
ctx-packer query "<search terms>" --format zip
ctx-packer query "<search terms>" --format xml
```

### Pack for AI Context
```bash
ctx-packer pack . --query "<feature or topic>"
```

### Status Check
```bash
ctx-packer status .
```

## Use Cases

| Task | Command |
|------|---------|
| Code Review | `ctx-packer pack . --query "changes" --format zip` |
| Bug Investigation | `ctx-packer pack . --query "error handling" --format xml` |
| Feature Context | `ctx-packer pack . --query "API endpoints" --budget 80000` |
| Documentation | `ctx-packer query "public methods" --format zip` |

## Tips

- Index once, reuse many times
- Use `--format xml` for pasting into web interfaces
- Adjust `--budget` for context size control
- Check `ctx-packer status .` for index health
