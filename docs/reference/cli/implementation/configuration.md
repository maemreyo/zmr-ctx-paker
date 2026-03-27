# Configuration Loading

How the CLI loads and manages configuration.

## Loading Priority

Configuration is loaded with the following priority (highest to lowest):

1. **Explicit `--config` flag**
2. **Repository `.ws-ctx-engine.yaml`**
3. **Default configuration**

## Implementation

### Load Function

```python
def _load_config(
    config_path: Optional[str],
    repo_path: Optional[str] = None
) -> Config:
    """
    Load configuration from file or use defaults.
    
    Priority:
    1. Explicit config_path
    2. {repo_path}/.ws-ctx-engine.yaml
    3. Defaults
    """
    # 1. Check explicit config path
    if config_path:
        return Config.from_yaml(config_path)
    
    # 2. Check repo path for config
    if repo_path:
        repo_config = Path(repo_path) / ".ws-ctx-engine.yaml"
        if repo_config.exists():
            return Config.from_yaml(repo_config)
    
    # 3. Use defaults
    return Config.default()
```

## Configuration Sources

### Source 1: Explicit Flag

```bash
ws-ctx-engine query "test" --config custom.yaml
```

**Implementation:**
```python
if ctx.params.get('config'):
    config = Config.from_yaml(ctx.params['config'])
```

### Source 2: Repository Config

```bash
ws-ctx-engine query "test"  # Uses .ws-ctx-engine.yaml if exists
```

**Implementation:**
```python
repo_config = Path(repo_path) / ".ws-ctx-engine.yaml"
if repo_config.exists():
    config = Config.from_yaml(repo_config)
```

### Source 3: Defaults

```python
@dataclass
class Config:
    token_budget: int = 100000
    chunk_size: int = 512
    vector_backend: str = "auto"
    graph_backend: str = "auto"
    
    @classmethod
    def default(cls) -> 'Config':
        return cls()
```

## YAML Parsing

### Schema Validation

```python
from pydantic import BaseModel, validator

class ConfigSchema(BaseModel):
    version: int
    index: IndexConfig
    vector_index: VectorConfig
    graph: GraphConfig
    
    @validator('version')
    def check_version(cls, v):
        if v != 1:
            raise ValueError(f"Unsupported version: {v}")
        return v
```

### Error Handling

```python
try:
    config = Config.from_yaml(path)
except yaml.YAMLError as e:
    console.print(f"[red]Invalid YAML:[/red] {e}")
    raise typer.Exit(code=1)
except ValidationError as e:
    console.print(f"[red]Config validation failed:[/red] {e}")
    raise typer.Exit(code=1)
```

## Override Mechanism

### Command-Line Overrides

```python
@app.command()
def query(
    budget: int = typer.Option(None, "--budget", "-b"),
):
    config = _load_config(...)
    
    # Override with CLI flag
    if budget:
        config.token_budget = budget
```

### Environment Variables

```python
import os

# Environment variable override
if os.getenv("WSCTX_TOKEN_BUDGET"):
    config.token_budget = int(os.getenv("WSCTX_TOKEN_BUDGET"))
```

## Configuration Merging

### Deep Merge Strategy

```python
def merge_configs(base: dict, override: dict) -> dict:
    """Deep merge two config dicts"""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result
```

## Default Values

### Built-in Defaults

```python
DEFAULT_CONFIG = {
    "version": 1,
    "index": {
        "token_budget": 100000,
        "chunk_size": 512,
    },
    "vector_index": {
        "backend": "auto",
    },
    "graph": {
        "backend": "auto",
    },
}
```

### Platform-Specific Defaults

```python
import platform

if platform.system() == "Darwin":
    # macOS-specific defaults
    DEFAULT_CONFIG["embeddings"] = {"batch_size": 16}
else:
    DEFAULT_CONFIG["embeddings"] = {"batch_size": 32}
```

## Related Documentation

- [init-config](../commands/config/init-config.md) - Config generation
- [Configuration Management](../configuration.md) - Full config reference
- [Dependencies](dependencies.md) - YAML parsing library
