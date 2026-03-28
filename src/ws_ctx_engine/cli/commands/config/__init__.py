"""Configuration commands."""

import typer

from . import init_config

__all__ = ["init_config"]

# Create sub-app and include commands
app = typer.Typer(name="config", help="Configuration commands.")
app.add_typer(init_config.app)
