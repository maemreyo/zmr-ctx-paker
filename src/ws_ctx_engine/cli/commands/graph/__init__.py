"""Graph commands."""

import typer

from . import backup

__all__ = ["backup"]

# Create sub-app and include commands
app = typer.Typer(name="graph", help="Graph commands.")
app.add_typer(backup.app)
