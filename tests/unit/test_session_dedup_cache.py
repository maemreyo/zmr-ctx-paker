"""Unit tests for session deduplication cache (session/dedup_cache.py)."""

import json

from ws_ctx_engine.session.dedup_cache import SessionDeduplicationCache, clear_all_sessions


class TestSessionDeduplicationCache:
    def test_first_call_returns_content(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        is_dup, result = cache.check_and_mark("src/auth.py", "def authenticate(): ...")
        assert is_dup is False
        assert result == "def authenticate(): ..."

    def test_second_call_same_content_returns_marker(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        content = "def authenticate(): ..."
        cache.check_and_mark("src/auth.py", content)
        is_dup, result = cache.check_and_mark("src/auth.py", content)
        assert is_dup is True
        assert "DEDUPLICATED" in result
        assert "src/auth.py" in result

    def test_different_content_not_deduplicated(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        cache.check_and_mark("src/auth.py", "version 1")
        is_dup, _ = cache.check_and_mark("src/auth.py", "version 2")
        assert is_dup is False

    def test_same_content_different_paths(self, tmp_path):
        """Same content at two different paths is still deduplicated (hash-based)."""
        cache = SessionDeduplicationCache("sess1", tmp_path)
        content = "shared content"
        cache.check_and_mark("src/a.py", content)
        is_dup, _ = cache.check_and_mark("src/b.py", content)
        assert is_dup is True

    def test_size_increments(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        assert cache.size == 0
        cache.check_and_mark("src/a.py", "content a")
        assert cache.size == 1
        cache.check_and_mark("src/b.py", "content b")
        assert cache.size == 2

    def test_persistence_across_instances(self, tmp_path):
        """Cache survives creating a new instance with the same session_id."""
        content = "persistent content"
        cache1 = SessionDeduplicationCache("persisted", tmp_path)
        cache1.check_and_mark("src/x.py", content)

        cache2 = SessionDeduplicationCache("persisted", tmp_path)
        is_dup, _ = cache2.check_and_mark("src/x.py", content)
        assert is_dup is True

    def test_clear_resets_state(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        content = "some content"
        cache.check_and_mark("src/a.py", content)
        cache.clear()
        assert cache.size == 0
        assert not (tmp_path / ".ws-ctx-engine-session-sess1.json").exists()

    def test_clear_allows_re_marking(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        content = "some content"
        cache.check_and_mark("src/a.py", content)
        cache.clear()
        is_dup, result = cache.check_and_mark("src/a.py", content)
        assert is_dup is False

    def test_atomic_write_produces_valid_json(self, tmp_path):
        cache = SessionDeduplicationCache("atomic", tmp_path)
        cache.check_and_mark("src/a.py", "hello world")
        cache_file = tmp_path / ".ws-ctx-engine-session-atomic.json"
        data = json.loads(cache_file.read_text())
        assert isinstance(data, dict)
        assert len(data) == 1

    def test_marker_contains_short_hash(self, tmp_path):
        cache = SessionDeduplicationCache("sess1", tmp_path)
        content = "def foo(): pass"
        cache.check_and_mark("src/foo.py", content)
        _, marker = cache.check_and_mark("src/foo.py", content)
        # Marker should include 8-char hex hash
        import hashlib

        short_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
        assert short_hash in marker

    def test_different_session_ids_isolated(self, tmp_path):
        content = "shared content"
        cache_a = SessionDeduplicationCache("session-a", tmp_path)
        cache_b = SessionDeduplicationCache("session-b", tmp_path)
        cache_a.check_and_mark("src/x.py", content)
        is_dup, _ = cache_b.check_and_mark("src/x.py", content)
        assert is_dup is False  # session B hasn't seen this content


class TestClearAllSessions:
    def test_deletes_all_session_files(self, tmp_path):
        for name in ("a", "b", "c"):
            (tmp_path / f".ws-ctx-engine-session-{name}.json").write_text("{}")
        count = clear_all_sessions(tmp_path)
        assert count == 3
        assert list(tmp_path.glob(".ws-ctx-engine-session-*.json")) == []

    def test_ignores_other_files(self, tmp_path):
        (tmp_path / "metadata.json").write_text("{}")
        count = clear_all_sessions(tmp_path)
        assert count == 0
        assert (tmp_path / "metadata.json").exists()

    def test_empty_dir_returns_zero(self, tmp_path):
        assert clear_all_sessions(tmp_path) == 0
