"""Session clear command for clearing deduplication caches."""

from pathlib import Path

import typer

app = typer.Typer()


@app.command("clear")
def session_clear(
    repo_path: str = typer.Argument(
        ".",
        help="Repository root used to locate .ws-ctx-engine/ cache directory.",
    ),
    session_id: str | None = typer.Option(
        None,
        "--session-id",
        help="Clear only this session's cache.  Omit to clear ALL session caches.",
    ),
) -> None:
    """Delete session deduplication cache file(s)."""
    from ...session.dedup_cache import SessionDeduplicationCache, clear_all_sessions
    from ...main import console

    cache_dir = Path(repo_path) / ".ws-ctx-engine"
    if session_id:
        cache = SessionDeduplicationCache(session_id=session_id, cache_dir=cache_dir)
        cache.clear()
        console.print(f"[green]✓[/green] Cleared session cache: {session_id}")
    else:
        deleted = clear_all_sessions(cache_dir)
        console.print(f"[green]✓[/green] Cleared {deleted} session cache file(s) from {cache_dir}")
