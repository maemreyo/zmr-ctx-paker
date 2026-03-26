"""
Session-level semantic deduplication cache.

Agents frequently call the context tool multiple times within a session,
often receiving the same files each time — wasting tokens and increasing cost.

This module provides a lightweight file-hash cache that persists to disk so
that subsequent calls within the same session can replace already-seen file
content with a small `[DEDUPLICATED]` marker.

Usage
-----
    cache = SessionDeduplicationCache(session_id="my-session", cache_dir=Path(".ws-ctx-engine"))
    is_dup, content_or_marker = cache.check_and_mark("src/auth.py", content)
    if is_dup:
        # content_or_marker is the DEDUPLICATED marker string
        ...

CLI flags surfacing this cache
------------------------------
    --session-id STR    Name of the session (default: "default")
    --no-dedup          Disable deduplication entirely
    wsctx session clear  Delete all session cache files
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


class SessionDeduplicationCache:
    """
    Track file content hashes within an agent session.

    The cache is persisted as a JSON file in *cache_dir* so it survives
    between separate CLI invocations that share the same *session_id*.
    """

    MARKER_TEMPLATE = "[DEDUPLICATED: {path} — already sent in this session. Hash: {short_hash}]"

    def __init__(self, session_id: str, cache_dir: Path) -> None:
        self.session_id = session_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / f".ws-ctx-engine-session-{session_id}.json"
        self.seen_hashes: dict[str, str] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_and_mark(self, file_path: str, content: str) -> tuple[bool, str]:
        """
        Check whether *file_path*'s content has already been sent this session.

        If it has, return ``(True, marker)`` where *marker* is a compact
        placeholder string.  If it hasn't, record the hash, persist the cache,
        and return ``(False, content)``.

        Args:
            file_path: Relative path of the file (used in the marker string).
            content: Raw file content to hash and potentially deduplicate.

        Returns:
            ``(is_duplicate, content_or_marker)``
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in self.seen_hashes:
            marker = self.MARKER_TEMPLATE.format(
                path=file_path,
                short_hash=content_hash[:8],
            )
            return True, marker
        self.seen_hashes[content_hash] = file_path
        self._save()
        return False, content

    def clear(self) -> None:
        """Delete the on-disk cache and reset in-memory state."""
        self.seen_hashes = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    @property
    def size(self) -> int:
        """Number of unique content hashes tracked."""
        return len(self.seen_hashes)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, str]:
        try:
            result = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return dict(result) if isinstance(result, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        try:
            payload = json.dumps(self.seen_hashes, ensure_ascii=False)
            # Atomic write: write to a sibling temp file, then rename to avoid
            # corruption when concurrent agent calls hit the cache simultaneously.
            fd, tmp_path = tempfile.mkstemp(dir=self.cache_file.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(payload)
                os.replace(tmp_path, self.cache_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError:
            pass  # Non-fatal — dedup is best-effort


def clear_all_sessions(cache_dir: Path) -> int:
    """
    Delete all session cache files in *cache_dir*.

    Returns:
        Number of files deleted.
    """
    deleted = 0
    for p in cache_dir.glob(".ws-ctx-engine-session-*.json"):
        try:
            p.unlink()
            deleted += 1
        except OSError:
            pass
    return deleted
