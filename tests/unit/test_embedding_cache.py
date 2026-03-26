"""Unit tests for embedding cache (vector_index/embedding_cache.py)."""

import json

import numpy as np
import pytest

from ws_ctx_engine.vector_index.embedding_cache import EmbeddingCache


class TestEmbeddingCacheContentHash:
    def test_same_text_produces_same_hash(self):
        h1 = EmbeddingCache.content_hash("hello world")
        h2 = EmbeddingCache.content_hash("hello world")
        assert h1 == h2

    def test_different_text_produces_different_hash(self):
        h1 = EmbeddingCache.content_hash("hello")
        h2 = EmbeddingCache.content_hash("world")
        assert h1 != h2

    def test_hash_is_64_char_hex(self):
        h = EmbeddingCache.content_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestEmbeddingCacheStoreAndLookup:
    def test_lookup_miss_returns_none(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        assert cache.lookup("nonexistent") is None

    def test_store_then_lookup(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        h = EmbeddingCache.content_hash("test content")
        cache.store(h, vec)
        result = cache.lookup(h)
        assert result is not None
        np.testing.assert_array_almost_equal(result, vec)

    def test_store_updates_existing_entry(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        h = EmbeddingCache.content_hash("content")
        vec1 = np.array([1.0, 0.0], dtype=np.float32)
        vec2 = np.array([0.0, 1.0], dtype=np.float32)
        cache.store(h, vec1)
        cache.store(h, vec2)
        result = cache.lookup(h)
        np.testing.assert_array_almost_equal(result, vec2)

    def test_size_increments(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        assert cache.size == 0
        cache.store(EmbeddingCache.content_hash("a"), np.array([1.0]))
        assert cache.size == 1
        cache.store(EmbeddingCache.content_hash("b"), np.array([2.0]))
        assert cache.size == 2

    def test_size_stable_on_update(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        h = EmbeddingCache.content_hash("text")
        cache.store(h, np.array([1.0]))
        cache.store(h, np.array([2.0]))  # update, not new entry
        assert cache.size == 1


class TestEmbeddingCachePersistence:
    def test_save_and_load_round_trip(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        h = EmbeddingCache.content_hash("round trip text")
        vec = np.array([0.5, 0.6, 0.7], dtype=np.float32)
        cache.store(h, vec)
        cache.save()

        cache2 = EmbeddingCache(tmp_path)
        cache2.load()
        result = cache2.lookup(h)
        assert result is not None
        np.testing.assert_array_almost_equal(result, vec)

    def test_load_on_empty_dir_is_noop(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        cache.load()  # Should not raise
        assert cache.size == 0

    def test_multiple_entries_persist(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        entries = {
            EmbeddingCache.content_hash(f"text_{i}"): np.array([float(i)], dtype=np.float32)
            for i in range(5)
        }
        for h, v in entries.items():
            cache.store(h, v)
        cache.save()

        cache2 = EmbeddingCache(tmp_path)
        cache2.load()
        assert cache2.size == 5
        for h, v in entries.items():
            result = cache2.lookup(h)
            assert result is not None
            np.testing.assert_array_almost_equal(result, v)

    def test_index_file_is_valid_json(self, tmp_path):
        cache = EmbeddingCache(tmp_path)
        cache.store(EmbeddingCache.content_hash("x"), np.array([1.0]))
        cache.save()
        data = json.loads((tmp_path / "embedding_index.json").read_text())
        assert "hash_to_idx" in data
        assert len(data["hash_to_idx"]) == 1
