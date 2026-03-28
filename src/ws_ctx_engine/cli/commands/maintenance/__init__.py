"""Maintenance commands."""

import typer

from . import reindex_domain, vacuum

__all__ = ["vacuum", "reindex_domain"]

# Create sub-app and include commands
app = typer.Typer(name="maintenance", help="Maintenance commands.")
app.add_typer(vacuum.app)
app.add_typer(reindex_domain.app)
