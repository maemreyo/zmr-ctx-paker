# init-config Command

Generate a smart `.ws-ctx-engine.yaml` configuration file for a repository.

## Usage

```bash
ws-ctx-engine init-config [repo_path] [OPTIONS]
```

## Arguments

| Argument    | Default | Description       |
| ----------- | ------- | ----------------- |
| `repo_path` | `.`     | Target repository |

## Options

| Option                                       | Default | Description                                      |
| -------------------------------------------- | ------- | ------------------------------------------------ |
| `--force`                                    | False   | Overwrite existing config                        |
| `--include-gitignore/--no-include-gitignore` | True    | Include .gitignore patterns                      |
| `--vector-index`                             | auto    | Vector backend: auto, native-leann, leann, faiss |
| `--graph`                                    | auto    | Graph backend: auto, igraph, networkx            |
| `--embeddings`                               | auto    | Embeddings: auto, local, api                     |

## Description

The `init-config` command analyzes your repository and generates an intelligent default configuration file (`.ws-ctx-engine.yaml`). It detects project structure, programming languages, and optimal backend choices.

## Examples

### Basic Initialization

```bash
# Initialize for current directory
ws-ctx-engine init-config

# Initialize for specific repository
ws-ctx-engine init-config /path/to/repo
```

### Force Overwrite

```bash
# Overwrite existing config
ws-ctx-engine init-config --force
```

### Custom Backend Selection

```bash
# Specify vector backend
ws-ctx-engine init-config --vector-index faiss

# Specify graph backend
ws-ctx-engine init-config --graph igraph

# Specify both
ws-ctx-engine init-config --vector-index faiss --graph networkx
```

### Gitignore Integration

```bash
# Include gitignore patterns (default)
ws-ctx-engine init-config --include-gitignore

# Exclude gitignore patterns
ws-ctx-engine init-config --no-include-gitignore
```

### Embeddings Configuration

```bash
# Auto-detect best embeddings
ws-ctx-engine init-config --embeddings auto

# Use local models only
ws-ctx-engine init-config --embeddings local

# Use API-based embeddings
ws-ctx-engine init-config --embeddings api
```

## Generated Configuration

The command creates a `.ws-ctx-engine.yaml` file with:

### 1. Version Information
```yaml
version: 1
generated_at: "2024-01-15T10:30:00Z"
```

### 2. Index Settings
```yaml
index:
  token_budget: 100000  # Default budget
  chunk_size: 512      # Optimal for most codebases
```

### 3. Backend Selection
```yaml
vector_index:
  backend: faiss       # or leann, or auto-detected
  
graph:
  backend: igraph      # or networkx, or auto-detected
```

### 4. Domain Mappings
```yaml
domains:
  authentication:
    - auth
    - login
    - jwt
  api:
    - routes
    - endpoints
    - handlers
```

### 5. Gitignore Patterns
```yaml
exclude_patterns:
  - node_modules/
  - __pycache__/
  - "*.pyc"
  - ".git/"
```

## When to Use

✅ **Run `init-config` when:**
- Setting up ws-ctx-engine for first time
- Migrating from old config version
- Repository structure changed significantly
- Want to regenerate with new defaults

❌ **Don't need to run:**
- Every time you use the CLI
- For minor config tweaks (edit manually)
- If happy with current config

## Backend Selection Guide

### Vector Index Backends

**`auto`** (Recommended):
- Automatically selects best available backend
- Prefers `native-leann` → `leann` → `faiss`
- Falls back gracefully

**`native-leann`**:
- Rust-based LEANN implementation
- Fastest performance
- Requires Rust extension

**`leann`**:
- Python LEANN implementation
- Good performance
- More features than FAISS

**`faiss`**:
- Facebook AI Similarity Search
- Most stable
- Widely tested

### Graph Backends

**`auto`** (Recommended):
- Prefers `igraph` → `networkx`
- Based on availability

**`igraph`**:
- Faster graph operations
- Better for large graphs
- Recommended for >1000 files

**`networkx`**:
- Pure Python
- Easier to debug
- Good for small projects

### Embeddings Sources

**`auto`** (Recommended):
- Tries local first, then API
- Graceful fallback

**`local`**:
- Runs sentence-transformers locally
- No API costs
- Requires more RAM

**`api`**:
- Uses OpenAI/embedding APIs
- Higher quality
- Costs money

## Common Workflows

### First-Time Setup

```bash
# 1. Generate config
ws-ctx-engine init-config /path/to/repo

# 2. Review generated config
cat /path/to/repo/.ws-ctx-engine.yaml

# 3. Check dependencies
ws-ctx-engine doctor

# 4. Build indexes
ws-ctx-engine index /path/to/repo
```

### Config Regeneration

```bash
# After major version upgrade
ws-ctx-engine init-config --force

# With custom backends
ws-ctx-engine init-config --vector-index faiss --graph networkx --force
```

### Multi-Project Setup

```bash
# Set up multiple projects
for repo in repos/*; do
  ws-ctx-engine init-config "$repo"
  ws-ctx-engine index "$repo"
done
```

## Configuration Validation

After generating config, verify it works:

```bash
# Generate
ws-ctx-engine init-config

# Validate
ws-ctx-engine doctor

# Test indexing
ws-ctx-engine index . --verbose
```

## Manual Configuration Edits

After `init-config`, you can manually edit `.ws-ctx-engine.yaml`:

```yaml
# Add custom domain keywords
domains:
  my_custom_domain:
    - keyword1
    - keyword2
    
# Adjust token budget
index:
  token_budget: 150000  # Increase from default
```

## Troubleshooting

**"Config already exists"**
- Use `--force` to overwrite
- Or manually edit existing config

**"Backend not available"**
- Install required dependency
- Or choose different backend

**"Invalid configuration"**
- Check YAML syntax
- Verify backend names
- Review schema documentation

## Best Practices

### Start Simple
```bash
# Begin with auto-detection
ws-ctx-engine init-config

# Let it choose optimal settings
```

### Customize Later
```bash
# Edit manually for fine-tuning
vim .ws-ctx-engine.yaml
```

### Version Control
```bash
# Commit config to git
git add .ws-ctx-engine.yaml
git commit -m "Add ws-ctx-engine config"
```

### Document Changes
```yaml
# Add comments for custom settings
index:
  token_budget: 150000  # Increased for large codebase
```

## Related Commands

- [`doctor`](doctor.md) - Verify dependencies after setup
- [`index`](index.md) - Build indexes with new config
- [`query`](query.md) - Test configuration

## Related Documentation

- [Configuration Management](../configuration.md) - Complete config reference
- [Backend Selection](../backend-selection.md) - Backend details
- [Installation Guide](../../INSTALL.md) - Setup prerequisites
