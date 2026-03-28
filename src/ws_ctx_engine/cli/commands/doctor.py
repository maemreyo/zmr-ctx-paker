"""Doctor command for checking dependencies."""

import typer

from ..utils import _doctor_dependency_report

app = typer.Typer(name="doctor", help="Check optional dependencies and recommend setup profile.")


@app.command()
def doctor() -> None:
    """Check optional dependencies and recommend setup profile."""
    from ...main import console

    report = _doctor_dependency_report()

    recommended_all = [
        "leann",
        "igraph",
        "sentence-transformers",
        "tree-sitter",
        "tree-sitter-python",
        "tree-sitter-javascript",
        "tree-sitter-typescript",
        "tree-sitter-rust",
    ]

    console.print("[bold]Dependency Doctor[/bold]")
    for name in sorted(report.keys()):
        status = "[green]OK[/green]" if report[name] else "[yellow]MISSING[/yellow]"
        console.print(f"- {name:<24} {status}")

    missing_all = [name for name in recommended_all if not report.get(name, False)]

    if not missing_all:
        console.print(
            "\n[bold green]✓ Ready for full feature set (all backends available).[/bold green]"
        )
        raise typer.Exit(code=0)

    console.print(
        "\n[yellow]Some recommended dependencies are missing for full feature set.[/yellow]"
    )
    typer.echo('Recommended install: pip install "ws-ctx-engine[all]"')
    console.print("[yellow]Missing:[/yellow] " + ", ".join(missing_all))
    raise typer.Exit(code=1)
