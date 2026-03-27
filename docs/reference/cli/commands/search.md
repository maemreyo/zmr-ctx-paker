# search Command

Search the indexed codebase and return ranked file paths.

## Usage

```bash
ws-ctx-engine search <query> [OPTIONS]
```

## Arguments

| Argument | Description                                | Required |
| -------- | ------------------------------------------ | -------- |
| `query`  | Natural language query for semantic search | Yes      |

## Options

| Option            | Short | Default | Description             |
| ----------------- | ----- | ------- | ----------------------- |
| `--repo`          | `-r`  | `.`     | Path to repository root |
| `--limit`         | `-l`  | 10      | Maximum results (1-50)  |
| `--domain-filter` |       | None    | Filter by domain        |
| `--config`        | `-c`  | None    | Path to custom config   |
| `--verbose`       | `-v`  | False   | Enable verbose logging  |
| `--agent-mode`    |       | False   | Emit NDJSON output      |

## Description

The `search` command performs semantic search on your indexed codebase, returning relevant file paths ranked by relevance. It uses vector similarity and graph-based ranking to find code by meaning rather than just text matching.

## Examples

### Basic Search

```bash
# Search current directory
ws-ctx-engine search "authentication logic"

# Search specific repository
ws-ctx-engine search "database queries" --repo /path/to/repo
```

### Limit Results

```bash
# Get top 20 results
ws-ctx-engine search "error handling" --limit 20

# Get only top 5 results
ws-ctx-engine search "API endpoints" -l 5
```

### Domain Filtering

```bash
# Search only in auth domain
ws-ctx-engine search "login flow" --domain-filter auth

# Search in multiple domains (if supported)
ws-ctx-engine search "routing" --domain-filter api,routes
```

### Agent Mode

```bash
# Machine-readable output for agents
ws-ctx-engine search "payment processing" --agent-mode
```

## When to Use

✅ **Use `search` when:**
- Looking for specific functionality in codebase
- Exploring unfamiliar code
- Finding examples of patterns
- Quick code location by concept

❌ **Use `query` instead when:**
- You need full file content (not just paths)
- Preparing context for LLM
- Need formatted output

## Output Format

### Human Mode (Default)

Returns a numbered list of file paths with relevance scores:

```
Search results for: "authentication logic"

1. src/auth/login.py (score: 0.95)
2. src/auth/middleware.py (score: 0.89)
3. src/api/auth.py (score: 0.87)
4. src/utils/security.py (score: 0.82)
5. tests/test_auth.py (score: 0.78)
```

### Agent Mode (--agent-mode)

Returns NDJSON format:

```json
{"type": "search_result", "path": "src/auth/login.py", "score": 0.95}
{"type": "search_result", "path": "src/auth/middleware.py", "score": 0.89}
```

## Search Strategies

### Broad Searches
Use general terms for exploration:
```bash
ws-ctx-engine search "authentication"
ws-ctx-engine search "database"
```

### Specific Searches
Use precise terms for targeted results:
```bash
ws-ctx-engine search "JWT token validation"
ws-ctx-engine search "PostgreSQL connection pooling"
```

### Pattern Searches
Search for patterns or concepts:
```bash
ws-ctx-engine search "retry logic with exponential backoff"
ws-ctx-engine search "singleton pattern"
```

## Tips for Better Results

1. **Use natural language**: "how passwords are hashed" works better than "password hash"

2. **Be specific but not too narrow**: "user authentication" is better than just "auth"

3. **Try synonyms**: If one query doesn't work, try related terms

4. **Adjust limit**: Start with default, increase if needed

5. **Use domain filters**: Narrow search scope for large codebases

## Common Use Cases

### Finding Implementation
```bash
ws-ctx-engine search "file upload handling"
ws-ctx-engine search "email sending"
```

### Understanding Architecture
```bash
ws-ctx-engine search "request routing"
ws-ctx-engine search "middleware chain"
```

### Locating Tests
```bash
ws-ctx-engine search "unit tests for login"
ws-ctx-engine search "integration test API"
```

### Code Review Preparation
```bash
ws-ctx-engine search "recently changed authentication"
ws-ctx-engine search "payment processing logic"
```

## Performance Considerations

- **Search speed**: Typically <100ms for most codebases
- **Index required**: Must run `index` first
- **Result quality**: Depends on index freshness

## Troubleshooting

**No results found:**
- Try broader or different search terms
- Verify index is up-to-date
- Check if domain filter is too restrictive

**Poor results:**
- Re-index with updated code
- Adjust query specificity
- Remove domain filters temporarily

## Related Commands

- [`index`](index.md) - Build indexes needed for search
- [`query`](query.md) - Get full content (not just paths)
- [`pack`](pack.md) - Full pipeline including search

## Related Documentation

- [Retrieval System](../retrieval.md) - Search implementation details
- [Ranking](../ranking.md) - How results are ranked
- [Domain Mapping](../workflow.md#domain-keywords) - Domain filtering
