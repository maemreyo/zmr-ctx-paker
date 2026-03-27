# Commands Reference

Complete reference for all ws-ctx-engine CLI commands.

## Command Categories

Commands are organized into logical groups based on their functionality:

### Core Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`doctor`](doctor.md) | Check dependencies | Verify installation |
| [`index`](index.md) | Build indexes | Initial setup, incremental updates |
| [`search`](search.md) | Search codebase | Find code by meaning |
| [`query`](query.md) | Query + pack | Generate LLM context |
| [`pack`](pack.md) | Full pipeline | End-to-end workflow |
| [`status`](status.md) | Show index status | Monitor indexes |

### Maintenance Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`vacuum`](maintenance/vacuum.md) | Optimize database | Improve performance |
| [`reindex-domain`](maintenance/reindex-domain.md) | Rebuild domain map | Update domain keywords |

### Configuration Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`init-config`](config/init-config.md) | Generate config | Initial setup |

### Server Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`mcp`](server/mcp.md) | MCP server | AI agent integration |

### Session Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`session clear`](session/session-clear.md) | Clear caches | Cleanup sessions |

## Quick Command Lookup

### Getting Started
1. **First time setup**: [`init-config`](config/init-config.md) → [`doctor`](doctor.md) → [`index`](index.md)
2. **Daily use**: [`search`](search.md) → [`query`](query.md)
3. **Full workflow**: [`pack`](pack.md)

### Common Tasks

**Search for code:**
```bash
ws-ctx-engine search "authentication logic"
```

**Generate context:**
```bash
ws-ctx-engine query "API endpoints" --format xml --budget 50000
```

**Full pipeline:**
```bash
ws-ctx-engine pack . -q "implement feature" --compress --copy
```

**Check status:**
```bash
ws-ctx-engine status /path/to/repo
```

## Command Syntax Conventions

```bash
ws-ctx-engine <command> [ARGUMENTS] [OPTIONS]
```

- `<command>` - Required command name
- `[ARGUMENTS]` - Optional positional arguments (shown in angle brackets)
- `[OPTIONS]` - Optional flags (shown with `--` or `-`)

### Argument Types

- `<repo_path>` - Path to repository root
- `<query>` - Natural language query string

### Option Formats

- Long form: `--verbose`, `--config path`
- Short form: `-v`, `-c path`
- Boolean flags: `--incremental`, `--quiet`
- Value options: `--limit 10`, `--budget 50000`

## Global Options

These options work with all commands:

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-V` | Show version |
| `--agent-mode` | | NDJSON output |
| `--quiet/--no-quiet` | | Suppress logs |

See [Global Options](../global-options.md) for details.

## Examples by Use Case

### Initial Setup
```bash
ws-ctx-engine init-config /path/to/repo
ws-ctx-engine doctor
ws-ctx-engine index /path/to/repo
```

### Development Workflow
```bash
ws-ctx-engine index . --incremental
ws-ctx-engine search "my feature"
ws-ctx-engine query "implement new feature" --copy
```

### CI/CD Integration
```bash
git diff --name-only HEAD~1 > changed.txt
ws-ctx-engine pack . -q "review changes" --changed-files changed.txt --format xml
```

### Agent Integration
```bash
ws-ctx-engine mcp --workspace /path/to/repo
# Or
ws-ctx-engine query "fix bug" --agent-mode --session-id agent-session-1
```

## Related Documentation

- [Architecture](../architecture.md) - CLI design overview
- [Workflows](../workflows/README.md) - Common usage patterns
- [Global Options](../global-options.md) - CLI-wide settings
- [Implementation](../implementation/README.md) - Technical details
