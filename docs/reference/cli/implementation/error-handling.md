# Error Handling

Error handling patterns and user-friendly error messages.

## Exception Hierarchy

### Base Exceptions

```python
class WsCtxEngineError(Exception):
    """Base exception for all CLI errors"""
    pass

class ConfigError(WsCtxEngineError):
    """Configuration-related errors"""
    pass

class IndexError(WsCtxEngineError):
    """Index-related errors"""
    pass

class QueryError(WsCtxEngineError):
    """Query/search errors"""
    pass
```

## Error Handling Patterns

### Pattern 1: Try-Except with User Message

```python
from typer import Exit
from rich.console import Console

console = Console()

@app.command()
def index(repo_path: str):
    try:
        index_repository(repo_path)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] Repository not found: {repo_path}")
        raise Exit(code=1)
    except PermissionError as e:
        console.print(f"[red]Error:[/red] Permission denied: {e}")
        raise Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise Exit(code=1)
```

### Pattern 2: Validation with Suggestions

```python
@app.command()
def query(query_str: str, repo_path: str = "."):
    # Validate repo exists
    if not Path(repo_path).exists():
        console.print(f"[red]Error:[/red] Repository path does not exist: {repo_path}")
        raise Exit(code=1)
    
    # Validate indexes exist
    if not indexes_exist(repo_path):
        console.print("[red]Error:[/red] Indexes not found")
        console.print("\n[yellow]Suggestion:[/yellow]")
        console.print("Run 'ws-ctx-engine index' first to build indexes")
        raise Exit(code=1)
    
    # Proceed with query
    ...
```

### Pattern 3: Contextual Error Messages

```python
def load_config(path: str):
    try:
        return Config.from_yaml(path)
    except yaml.YAMLError as e:
        raise ConfigError(
            f"Invalid configuration file: {path}\n"
            f"YAML parsing error: {e}"
        )
    except FileNotFoundError:
        raise ConfigError(
            f"Configuration file not found: {path}\n"
            f"Use 'ws-ctx-engine init-config' to create one"
        )
```

## User-Friendly Messages

### Do's ✅

**Clear and actionable:**
```
Error: Indexes not found

Suggestion: Run 'ws-ctx-engine index' first to build indexes
```

**Specific about what went wrong:**
```
Error: Repository path does not exist: /nonexistent/path

The provided path '/nonexistent/path' was not found on this system.
Please check the path and try again.
```

**Include next steps:**
```
Error: Token budget exceeded (150,000 / 100,000 tokens)

Options:
1. Increase budget: --budget 200000
2. Enable compression: --compress
3. Narrow your query scope
```

### Don'ts ❌

**Vague errors:**
```
Error: Failed
```

**Technical jargon without explanation:**
```
Error: VectorIndexNotFoundError: Index not initialized
```

**No actionable guidance:**
```
Error: No results
```

## Recovery Strategies

### Automatic Recovery

```python
def safe_index(repo_path: str):
    """Attempt indexing with automatic recovery"""
    try:
        index_repository(repo_path)
    except PartialIndexError:
        # Try incremental rebuild
        console.print("[yellow]Partial index detected, rebuilding...[/yellow]")
        index_repository(repo_path, incremental=True)
    except CorruptIndexError:
        # Full rebuild required
        console.print("[yellow]Index corrupted, full rebuild needed...[/yellow]")
        index_repository(repo_path, incremental=False)
```

### Graceful Degradation

```python
def get_backend(preferred: str):
    """Try preferred backend, fallback gracefully"""
    try:
        return load_backend(preferred)
    except ImportError:
        fallback = "faiss" if preferred == "leann" else "networkx"
        console.print(
            f"[yellow]{preferred} not available, using {fallback}[/yellow]"
        )
        return load_backend(fallback)
```

## Verbose Mode

```python
@app.command()
def index(
    repo_path: str,
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    try:
        if verbose:
            console.print("[dim]Starting indexing process...[/dim]")
            console.print(f"Repository: {repo_path}")
        
        index_repository(repo_path, verbose=verbose)
        
    except Exception as e:
        if verbose:
            import traceback
            console.print("[red]Full traceback:[/red]")
            console.print(traceback.format_exc())
        else:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Use --verbose for full details[/dim]")
        raise Exit(code=1)
```

## Exit Codes

```python
# Success
raise Exit(code=0)

# General errors
raise Exit(code=1)

# Configuration errors
raise Exit(code=2)

# Index errors
raise Exit(code=3)

# Permission errors
raise Exit(code=4)
```

## Related Documentation

- [Framework](framework.md) - Typer error handling
- [Commands Overview](../commands/README.md) - Command behavior
- [Architecture](architecture.md) - Error propagation
