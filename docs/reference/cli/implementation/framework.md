# Framework Implementation

The CLI is built using modern Python frameworks for optimal developer experience.

## Core Frameworks

### Typer

**Purpose:** CLI framework and argument parsing

**Why Typer:**
- Type hint-based interface
- Automatic validation
- Excellent documentation
- Built on top of Click
- Modern Python 3.7+

**Example Usage:**
```python
import typer

app = typer.Typer()

@app.command()
def index(
    repo_path: str,
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Build indexes for repository"""
    pass
```

**Benefits:**
- Automatic `--help` generation
- Type conversion and validation
- Subcommand support
- Shell completion integration

### Rich

**Purpose:** Terminal formatting and output

**Why Rich:**
- Beautiful terminal output
- Tables, panels, progress bars
- Markdown rendering
- Syntax highlighting
- Cross-platform

**Example Usage:**
```python
from rich.console import Console
from rich.panel import Panel

console = Console()

console.print(Panel("Packing repository..."))
console.print("[green]✓[/green] Complete!")
```

**Features Used:**
- Panels for status messages
- Progress bars for long operations
- Tables for structured data
- Syntax highlighting for code
- Colors for emphasis

## Design Decisions

### Why Not Click?

Typer provides:
- Better type safety
- Less boilerplate
- More modern API
- Built-in Rich integration

### Why Not Plain Rich?

Rich alone doesn't provide:
- Argument parsing
- Command routing
- Validation
- Help generation

### Framework Layering

```
User Input
    ↓
Typer (parsing & validation)
    ↓
Command Handler
    ↓
Rich (output formatting)
    ↓
Terminal
```

## Integration Patterns

### Command Structure

```python
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def query(
    query: str,
    budget: int = typer.Option(100000, "--budget", "-b")
):
    """Query codebase and generate context"""
    console.print(f"Querying: {query}")
    # Implementation here
```

### Error Handling

```python
from typer import Exit

@app.command()
def index(repo_path: str):
    try:
        # Index logic
        pass
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise Exit(code=1)
```

### Progress Indicators

```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Indexing...", total=100)
    # Do work
    progress.update(task, advance=10)
```

## Related Documentation

- [Dependencies](dependencies.md) - Full dependency list
- [Architecture](architecture.md) - CLI design overview
- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
