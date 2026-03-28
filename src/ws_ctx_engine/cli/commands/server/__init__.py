"""Server commands."""

import typer

from . import mcp

__all__ = ["mcp"]

# Create sub-app and include commands
app = typer.Typer(name="server", help="Server commands.")
app.add_typer(mcp.app)
