# Example: Context Packer on zmr-koe Repository

This example demonstrates how to use Context Packer to analyze and package the [zmr-koe](https://github.com/maemreyo/zmr-koe) repository.

## Repository Information

- **Name**: zmr-koe
- **Description**: A TypeScript/JavaScript project
- **Source**: https://github.com/maemreyo/zmr-koe
- **Cloned to**: `source/`

## Directory Structure

```
examples/zmr-koe/
├── README.md           # This file
├── config.yaml         # Custom configuration for this example
├── source/             # Cloned zmr-koe repository
└── output/             # Generated context packs (after running)
```

## Running the Example

### Prerequisites

Make sure Context Packer is installed:

```bash
# From the root of zmr-ctx-paker repository
pip install -e ".[all]"
```

### Index the Repository

```bash
# Index the zmr-koe repository
context-pack index examples/zmr-koe/source --config examples/zmr-koe/config.yaml
```

This will create indexes in `examples/zmr-koe/source/.context-pack/`:
- `vector.idx` - Semantic search index
- `graph.pkl` - Dependency graph with PageRank scores
- `metadata.json` - Staleness detection metadata

### Generate Context Pack (XML Format)

```bash
# Generate XML output for paste workflows
context-pack pack examples/zmr-koe/source \
  --config examples/zmr-koe/config.yaml \
  --format xml \
  --output examples/zmr-koe/output
```

Output: `examples/zmr-koe/output/repomix-output.xml`

### Generate Context Pack (ZIP Format)

```bash
# Generate ZIP output for upload workflows
context-pack pack examples/zmr-koe/source \
  --config examples/zmr-koe/config.yaml \
  --format zip \
  --output examples/zmr-koe/output
```

Output: `examples/zmr-koe/output/context-pack.zip`

### Query with Natural Language

```bash
# Find files related to specific functionality
context-pack query "authentication and user management" \
  --config examples/zmr-koe/config.yaml \
  --format zip \
  --output examples/zmr-koe/output
```

## Configuration

The `config.yaml` file contains custom settings for this example:

- Token budget: 50,000 (smaller for demonstration)
- Semantic weight: 0.7 (prioritize semantic search)
- PageRank weight: 0.3
- Include patterns: TypeScript, JavaScript, JSON files
- Exclude patterns: node_modules, build artifacts

## Expected Output

After running the commands above, you should see:

```
examples/zmr-koe/output/
├── repomix-output.xml      # XML format output
├── context-pack.zip        # ZIP format output
└── REVIEW_CONTEXT.md       # Manifest (extracted from ZIP)
```

### XML Output Structure

```xml
<repository>
  <metadata>
    <name>zmr-koe</name>
    <file_count>42</file_count>
    <total_tokens>48500</total_tokens>
  </metadata>
  <files>
    <file path="src/main.ts" tokens="1234">
      <content><![CDATA[...]]></content>
    </file>
    ...
  </files>
</repository>
```

### ZIP Output Structure

```
context-pack.zip
├── files/
│   ├── src/
│   │   ├── main.ts
│   │   ├── auth/
│   │   └── ...
│   └── package.json
└── REVIEW_CONTEXT.md
```

## Use Cases

### 1. Code Review

```bash
# Generate context for PR review
context-pack pack examples/zmr-koe/source \
  --changed-files changed.txt \
  --format zip \
  --budget 30000
```

### 2. Bug Investigation

```bash
# Find relevant code for a bug
context-pack query "error handling in API requests" \
  --format xml \
  --budget 20000
```

### 3. Documentation Generation

```bash
# Extract core API files
context-pack query "public API and interfaces" \
  --format zip \
  --budget 40000
```

## Performance Metrics

Expected performance on zmr-koe repository:

- **Indexing time**: ~30 seconds (with primary backends)
- **Query time**: <2 seconds
- **Repository size**: ~1,050 files
- **Selected files**: ~40-50 files (within 50k token budget)
- **Index size**: ~5 MB (LEANN) or ~150 MB (FAISS)

## Troubleshooting

### "LEANN not available"

Install all dependencies:
```bash
pip install -e ".[all]"
```

Or use FAISS fallback by setting in config:
```yaml
backends:
  vector_index: faiss
```

### "Index is stale"

Rebuild the index:
```bash
rm -rf examples/zmr-koe/source/.context-pack/
context-pack index examples/zmr-koe/source
```

### "Token budget exceeded"

Reduce the budget or adjust weights:
```bash
context-pack pack examples/zmr-koe/source --budget 30000
```

## Next Steps

- Modify `config.yaml` to experiment with different settings
- Try different queries to see how semantic search works
- Compare XML vs ZIP output formats
- Test with changed files for PR review workflow

## Notes

- The `source/` directory contains the full zmr-koe repository
- Indexes are stored in `source/.context-pack/` (gitignored)
- Output files are generated in `output/` directory
- This example uses a smaller token budget (50k) for demonstration
