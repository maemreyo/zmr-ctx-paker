# query Command

Search indexes and generate LLM-ready output.

## Usage

```bash
ws-ctx-engine query <query> [OPTIONS]
```

## Arguments

| Argument | Description                                | Required |
| -------- | ------------------------------------------ | -------- |
| `query`  | Natural language query for semantic search | Yes      |

## Options

| Option                   | Short | Default | Description                                   |
| ------------------------ | ----- | ------- | --------------------------------------------- |
| `--repo`                 | `-r`  | `.`     | Path to repository root                       |
| `--format`               | `-f`  | config  | Output format: xml, zip, json, yaml, md, toon |
| `--budget`               | `-b`  | config  | Token budget for context                      |
| `--config`               | `-c`  | None    | Path to custom config                         |
| `--verbose`              | `-v`  | False   | Enable verbose logging                        |
| `--secrets-scan`         |       | False   | Enable secret scanning and redaction          |
| `--agent-mode`           |       | False   | Emit NDJSON output                            |
| `--stdout`               |       | False   | Write output to stdout                        |
| `--copy`                 |       | False   | Copy output to clipboard                      |
| `--compress`             |       | False   | Apply smart compression                       |
| `--shuffle/--no-shuffle` |       | True    | Reorder for model recall                      |
| `--mode`                 |       | None    | Agent phase: discovery, edit, test            |
| `--session-id`           |       | default | Session ID for deduplication                  |
| `--no-dedup`             |       | False   | Disable deduplication                         |

## Description

The `query` command is the primary tool for generating LLM-ready context. It searches your indexed codebase, retrieves relevant code, and packages it in various formats optimized for AI assistants.

## Examples

### Basic Query

```bash
# Simple query with default settings
ws-ctx-engine query "user authentication flow"
```

### Format and Budget Control

```bash
# XML format with specific token budget
ws-ctx-engine query "API endpoints" --format xml --budget 50000

# YAML format
ws-ctx-engine query "database models" --format yaml
```

### Clipboard and Output

```bash
# Copy directly to clipboard
ws-ctx-engine query "error handling" --copy

# Write to stdout for piping
ws-ctx-engine query "logging setup" --stdout

# Save to file (default behavior)
ws-ctx-engine query "config management"
```

### Compression and Optimization

```bash
# Apply smart compression
ws-ctx-engine query "full system overview" --compress

# Disable shuffling for consistent ordering
ws-ctx-engine query "module structure" --no-shuffle
```

### Agent Mode Features

```bash
# Enable agent mode with session tracking
ws-ctx-engine query "database schema" --agent-mode --session-id agent-123

# Disable deduplication
ws-ctx-engine query "all API routes" --no-dedup

# Specify agent phase
ws-ctx-engine query "test coverage" --mode test
```

### Security Features

```bash
# Scan and redact secrets
ws-ctx-engine query "payment processing" --secrets-scan
```

## When to Use

✅ **Use `query` when:**
- Preparing context for LLM chatbots
- Generating documentation
- Code review preparation
- Understanding system components
- Creating knowledge packages

❌ **Use `search` instead when:**
- You only need file paths
- Quick exploration
- Don't need full content

## Output Formats

### XML (Default for many use cases)
Structured markup format, easy to parse:
```xml
<file path="src/auth.py">
  <content>...</content>
</file>
```

### ZIP
Compressed archive with multiple files and metadata.

### JSON
Machine-readable structured data.

### YAML
Human-readable structured data.

### Markdown
Formatted documentation style.

### Toon
Compact format optimized for LLM consumption.

See [Output Formatters](../output-formatters.md) for detailed format specifications.

## Token Budget Management

The `--budget` option controls how much context is included:

```bash
# Small budget for quick lookups
ws-ctx-engine query "auth flow" --budget 10000

# Large budget for comprehensive context
ws-ctx-engine query "entire system" --budget 100000

# Use config default
ws-ctx-engine query "api layer"
```

**Budget Guidelines:**
- 10K tokens: Quick reference
- 30K tokens: Standard context
- 50K+ tokens: Comprehensive analysis
- 100K+ tokens: Full system overview

## Advanced Features

### Secret Scanning

Automatically detect and redact sensitive information:

```bash
ws-ctx-engine query "payment module" --secrets-scan
```

Redacted items include:
- API keys
- Passwords
- Tokens
- Private keys

### Session Deduplication

Track what you've already seen across multiple queries:

```bash
# First query (baseline)
ws-ctx-engine query "auth system" --session-id review-1

# Second query (only new content)
ws-ctx-engine query "auth tests" --session-id review-1
```

### Agent Phase Modes

Optimize output for different AI agent tasks:

```bash
# Discovery phase - broad context
ws-ctx-engine query "system architecture" --mode discovery

# Edit phase - focused on change areas
ws-ctx-engine query "modify login" --mode edit

# Test phase - test-related context
ws-ctx-engine query "add tests" --mode test
```

### Smart Compression

Reduce token count while preserving key information:

```bash
ws-ctx-engine query "full codebase" --compress
```

Compression techniques:
- Remove comments
- Strip docstrings
- Minify whitespace
- Keep only essential code

## Common Workflows

### Code Review
```bash
ws-ctx-engine query "recent changes" --copy --compress
```

### Feature Implementation
```bash
ws-ctx-engine query "existing auth patterns" --format xml --budget 50000
```

### Documentation Generation
```bash
ws-ctx-engine query "API layer" --format markdown --stdout
```

### Bug Investigation
```bash
ws-ctx-engine query "error handling in payment flow" --secrets-scan --copy
```

### Learning New Codebase
```bash
ws-ctx-engine query "main application structure" --format yaml
```

## Output Destinations

### File (Default)
Saves to `./output/repomix-output.{format}`

### Clipboard
```bash
ws-ctx-engine query "code snippets" --copy
```

### Stdout
```bash
ws-ctx-engine query "config" --stdout | grep pattern
```

## Performance Tips

1. **Use appropriate budget**: Don't request 100K tokens for simple queries
2. **Enable compression**: For large contexts, `--compress` saves tokens
3. **Leverage sessions**: Avoid re-reading same content
4. **Choose right format**: XML/YAML for structure, MD for docs

## Troubleshooting

**"No results found":**
- Run `index` first
- Check query specificity
- Verify index freshness

**"Token budget exceeded":**
- Increase budget
- Enable compression
- Narrow query scope

**"Secrets detected and redacted":**
- Expected behavior with `--secrets-scan`
- Review redaction log if needed

## Related Commands

- [`search`](search.md) - Find file paths only
- [`pack`](pack.md) - Full pipeline including indexing
- [`status`](status.md) - Check index status

## Related Documentation

- [Output Formatters](../output-formatters.md) - Format details
- [Compression Guide](../guides/compression.md) - Compression strategies
- [Token Budget](../budget.md) - Budget management
- [Secret Scanner](../secret-scanner.md) - Security features
