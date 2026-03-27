# Global Options and Output Modes

This document describes the global options and output modes available across all CLI commands.

## Global Options

These options are available for all commands via the main callback:

| Option               | Short | Default | Description           |
| -------------------- | ----- | ------- | --------------------- |
| `--version`          | `-V`  |         | Show version and exit |
| `--agent-mode`       |       | False   | NDJSON output mode    |
| `--quiet/--no-quiet` |       | True    | Suppress info logs    |

### Usage Examples

```bash
# Show version
ws-ctx-engine --version

# Enable agent mode globally
ws-ctx-engine query "test" --agent-mode

# Suppress info logs
ws-ctx-engine index . --quiet
```

## CLI Output Modes

The CLI supports two distinct output modes to accommodate different use cases.

### Human Mode (Default)

Rich-formatted output with colors, panels, and visual formatting optimized for human readability.

**Example Output:**

```
╭─────────────────────────────────────────────────────────────────╮
│ Packing repository: /path/to/repo                               │
│ Query: authentication logic                                     │
│ Format: XML                                                     │
│ Budget: 100,000 tokens                                          │
╰─────────────────────────────────────────────────────────────────╯

Step 1: Checking indexes...
  → Indexes found (will auto-rebuild if stale)

Step 2: Querying and packing...

✓ Packing complete!
Context packed (78,234 / 100,000 tokens)
Output saved to: ./output/repomix-output.xml
```

**Characteristics:**
- Colorful terminal output
- Progress indicators
- Status messages and checkmarks
- Formatted tables and panels
- Verbose by default

### Agent Mode (--agent-mode)

NDJSON (Newline-delimited JSON) output for programmatic consumption by AI agents and automation tools.

**Example Output:**

```json
{ "type": "status", "command": "pack", "status": "success", "output_path": "./output/repomix-output.xml", "total_tokens": 78234, "generated_at": "2024-01-15T10:30:00Z" }
```

**Characteristics:**
- Machine-readable JSON format
- Structured data output
- Easy to parse programmatically
- Minimal formatting overhead
- Suitable for piping to other tools

**Use Cases:**
- AI agent integration
- CI/CD automation
- Script processing
- API-like interactions

## Command-Specific Options

While global options apply to all commands, each command has its own specific options. See individual command documentation for details:

- [doctor](commands/doctor.md) - No additional global options
- [index](commands/index.md) - Supports `--config`, `--verbose`, `--incremental`
- [search](commands/search.md) - Supports `--repo`, `--limit`, `--domain-filter`, etc.
- [query](commands/query.md) - Full range of output and formatting options
- [pack](commands/pack.md) - Complete pipeline options
- [status](commands/status.md) - Basic status options
- [mcp](commands/server/mcp.md) - Server-specific options
- [session clear](commands/session/session-clear.md) - Session management options

## Best Practices

### When to Use Agent Mode

✅ **Use Agent Mode when:**
- Integrating with AI agents (Claude Desktop, Cursor, etc.)
- Building automation scripts
- Processing output programmatically
- Running in CI/CD pipelines

❌ **Avoid Agent Mode when:**
- Using CLI interactively
- Debugging issues manually
- Learning the tool
- Presenting results to stakeholders

### Combining Options

```bash
# Interactive development (Human mode)
ws-ctx-engine query "authentication flow" --copy

# Agent integration (Agent mode)
ws-ctx-engine query "fix bug" --agent-mode --session-id agent-session-1

# CI/CD automation
ws-ctx-engine pack . -q "review changes" --agent-mode --format xml
```

## Related Documentation

- [Architecture](architecture.md) - Overall CLI design
- [Commands Overview](commands/README.md) - All available commands
- [MCP Server](commands/server/mcp.md) - Agent integration patterns
- [Session Management](commands/session/README.md) - Session deduplication
