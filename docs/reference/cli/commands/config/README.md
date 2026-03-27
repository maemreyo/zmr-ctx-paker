# Configuration Commands

Configuration commands help you set up and manage ws-ctx-engine settings.

## Available Commands

| Command | Description | Use Case |
|---------|-------------|----------|
| [`init-config`](init-config.md) | Generate smart configuration | Initial repository setup |

## Configuration Overview

ws-ctx-engine uses a YAML configuration file (`.ws-ctx-engine.yaml`) to control:

- **Backend Selection**: Vector index, graph, embeddings backends
- **Index Settings**: Token budgets, chunk sizes
- **Domain Mappings**: Keyword-to-domain associations
- **Gitignore Integration**: File exclusion patterns
- **Output Preferences**: Default formats, compression

## Configuration Priority

Settings are loaded with this priority:

1. **Explicit `--config` flag** (highest)
2. **Repository `.ws-ctx-engine.yaml`**
3. **Default configuration** (lowest)

```bash
# Uses custom config
ws-ctx-engine query "test" --config custom.yaml

# Uses repo config (if exists)
ws-ctx-engine query "test"

# Uses defaults
ws-ctx-engine query "test"  # No config found
```

## Quick Start

### First-Time Setup

```bash
# 1. Generate configuration
ws-ctx-engine init-config /path/to/repo

# 2. Review generated config
cat /path/to/repo/.ws-ctx-engine.yaml

# 3. Build indexes
ws-ctx-engine index /path/to/repo
```

### Custom Backend Selection

```bash
# Generate with specific backends
ws-ctx-engine init-config --vector-index faiss --graph networkx
```

## Common Configurations

### Minimal Config

For simple projects:
```yaml
# .ws-ctx-engine.yaml
version: 1
index:
  token_budget: 100000
```

### Full Config

For complex projects:
```yaml
version: 1
index:
  token_budget: 100000
  chunk_size: 512
  
vector_index:
  backend: faiss
  
graph:
  backend: igraph
  
domains:
  authentication:
    - auth
    - login
    - jwt
```

## Related Documentation

- [`init-config`](init-config.md) - Configuration generation
- [Configuration Management](../configuration.md) - Detailed config reference
- [Backend Selection](../backend-selection.md) - Backend options
