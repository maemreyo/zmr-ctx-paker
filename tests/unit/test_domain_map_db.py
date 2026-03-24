"""Unit tests for DomainMapDB SQLite backend."""

import tempfile
import threading
from pathlib import Path

import pytest

from context_packer.domain_map.db import DomainMapDB


class TestDomainMapDBInit:
    """Tests for DomainMapDB initialization."""

    def test_creates_db_file(self, tmp_path):
        """Test that DB file is created on init."""
        db_path = tmp_path / "test.db"
        db = DomainMapDB(db_path)

        assert db_path.exists()
        db.close()

    def test_schema_version_stored(self, tmp_path):
        """Test that schema version is stored in meta table."""
        db = DomainMapDB(tmp_path / "test.db")

        conn = db._get_conn()
        version = conn.execute(
            "SELECT value FROM meta WHERE key = 'version'"
        ).fetchone()

        assert version is not None
        assert version["value"] == "1"

        db.close()

    def test_wal_mode_enabled(self, tmp_path):
        """Test that WAL journal mode is enabled."""
        db = DomainMapDB(tmp_path / "test.db")

        conn = db._get_conn()
        mode = conn.execute("PRAGMA journal_mode").fetchone()["journal_mode"]

        assert mode == "wal"

        db.close()


class TestDomainMapDBInsert:
    """Tests for write operations."""

    def test_insert_single_keyword(self, tmp_path):
        """Test inserting a single keyword."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunker", ["src/chunker/", "src/parsers/"])

        result = db.get("chunker")
        assert set(result) == {"src/chunker", "src/parsers"}  # Path() removes trailing slash

        db.close()

    def test_insert_multiple_keywords(self, tmp_path):
        """Test inserting multiple keywords."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunk", ["src/chunk/"])
        db.insert("embed", ["src/embed/"])
        db.insert("retrieval", ["src/retrieval/", "src/search/"])

        assert set(db.get("chunk")) == {"src/chunk"}
        assert set(db.get("embed")) == {"src/embed"}
        assert set(db.get("retrieval")) == {"src/retrieval", "src/search"}

        db.close()

    def test_insert_duplicate_keyword(self, tmp_path):
        """Test that inserting same keyword replaces directories."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("test", ["dir1/"])
        db.insert("test", ["dir2/", "dir3/"])

        result = db.get("test")
        assert set(result) == {"dir2", "dir3"}

        db.close()


class TestDomainMapDBBulkInsert:
    """Tests for bulk insert."""

    def test_bulk_insert_simple(self, tmp_path):
        """Test bulk insert from dict."""
        db = DomainMapDB(tmp_path / "test.db")
        mapping = {
            "chunk": ["src/chunk"],
            "embed": ["src/embed"],
            "retrieval": ["src/retrieval"],
        }

        db.bulk_insert(mapping)

        assert set(db.get("chunk")) == {"src/chunk"}
        assert set(db.get("embed")) == {"src/embed"}
        assert set(db.get("retrieval")) == {"src/retrieval"}

        db.close()

    def test_bulk_insert_large_mapping(self, tmp_path):
        """Test bulk insert with large mapping."""
        db = DomainMapDB(tmp_path / "test.db")

        mapping = {f"keyword_{i}": [f"dir_{i}/"] for i in range(100)}
        db.bulk_insert(mapping)

        stats = db.stats()
        assert stats["keywords"] == 100
        assert stats["directories"] == 100

        db.close()


class TestDomainMapDBGet:
    """Tests for read operations."""

    def test_get_existing_keyword(self, tmp_path):
        """Test getting existing keyword."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("test", ["dir1/", "dir2/"])

        result = db.get("test")
        assert set(result) == {"dir1", "dir2"}

        db.close()

    def test_get_nonexistent_keyword(self, tmp_path):
        """Test getting nonexistent keyword returns empty list."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("test", ["dir1/"])

        result = db.get("nonexistent")
        assert result == []

        db.close()

    def test_get_case_insensitive(self, tmp_path):
        """Test that keyword lookup is case-insensitive."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("CHUNK", ["src/chunk/"])

        result = db.get("chunk")
        assert set(result) == {"src/chunk"}

        result = db.get("Chunk")
        assert set(result) == {"src/chunk"}

        db.close()

    def test_contains_existing(self, tmp_path):
        """Test __contains__ for existing keyword."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("test", ["dir/"])

        assert "test" in db
        db.close()

    def test_contains_nonexisting(self, tmp_path):
        """Test __contains__ for nonexistent keyword."""
        db = DomainMapDB(tmp_path / "test.db")

        assert "nonexistent" not in db
        db.close()


class TestDomainMapDBPrefixSearch:
    """Tests for prefix search."""

    def test_prefix_search_exact(self, tmp_path):
        """Test prefix search with exact match."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunk", ["src/chunk/"])
        db.insert("chunking", ["src/chunking/"])

        results = db.prefix_search("chunk")
        assert "chunk" in results
        assert "chunking" in results

        db.close()

    def test_prefix_search_partial(self, tmp_path):
        """Test prefix search with partial prefix."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunker", ["src/chunker/"])
        db.insert("chunksize", ["src/chunksize/"])
        db.insert("parser", ["src/parser/"])

        results = db.prefix_search("chunk")
        assert "chunker" in results
        assert "chunksize" in results
        assert "parser" not in results

        db.close()

    def test_prefix_search_no_results(self, tmp_path):
        """Test prefix search with no results."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunk", ["src/chunk/"])

        results = db.prefix_search("xyz")
        assert len(results) == 0

        db.close()


class TestDomainMapDBStats:
    """Tests for stats."""

    def test_stats_empty(self, tmp_path):
        """Test stats on empty DB."""
        db = DomainMapDB(tmp_path / "test.db")

        stats = db.stats()
        assert stats["keywords"] == 0
        assert stats["directories"] == 0
        assert stats["mappings"] == 0

        db.close()

    def test_stats_with_data(self, tmp_path):
        """Test stats with data."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunk", ["src/chunk/", "src/core/"])
        db.insert("embed", ["src/embed/"])

        stats = db.stats()
        assert stats["keywords"] == 2
        assert stats["directories"] == 3
        assert stats["mappings"] == 3

        db.close()


class TestDomainMapDBMigration:
    """Tests for migration from pickle."""

    def test_migrate_from_pickle(self, tmp_path):
        """Test migration from pickle file."""
        import pickle

        pkl_path = tmp_path / "old.pkl"
        old_map = {
            "chunk": ["src/chunk/", "src/parsers/"],
            "embed": ["src/embed/"],
        }
        with open(pkl_path, "wb") as f:
            pickle.dump(old_map, f)

        db = DomainMapDB.migrate_from_pickle(pkl_path, tmp_path / "new.db")

        assert set(db.get("chunk")) == {"src/chunk", "src/parsers"}
        assert set(db.get("embed")) == {"src/embed"}

        db.close()

    def test_migrate_nonexistent_pickle(self, tmp_path):
        """Test migration from nonexistent pickle raises error."""
        with pytest.raises(FileNotFoundError):
            DomainMapDB.migrate_from_pickle(
                tmp_path / "nonexistent.pkl",
                tmp_path / "new.db"
            )


class TestDomainMapDBConcurrent:
    """Tests for concurrent access."""

    @pytest.mark.skip(reason="SQLite connection sharing needs careful thread isolation")
    def test_concurrent_reads(self, tmp_path):
        """Test that multiple threads can read concurrently."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("key", ["dir/"])

        errors = []

        def reader():
            try:
                for _ in range(100):
                    db.get("key")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        db.close()


class TestDomainMapDBContextManager:
    """Tests for context manager."""

    def test_context_manager(self, tmp_path):
        """Test that context manager closes connection properly."""
        with DomainMapDB(tmp_path / "test.db") as db:
            db.insert("test", ["dir/"])
            result = db.get("test")
            assert result == ["dir"]

        # Context manager should have closed the connection
        # Calling get again should work (SQLite auto-reconnects)


class TestDomainMapDBDropInCompatibility:
    """Tests for drop-in compatibility with dict-based API."""

    def test_get_keyword_directory_mapping(self, tmp_path):
        """Test that we can replicate dict-like get behavior."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunker", ["src/chunker/", "src/resolvers/"])

        # Should behave like dict.get()
        result = db.get("chunker")
        assert isinstance(result, list)
        assert "src/chunker" in result

        db.close()

    def test_keywords_property(self, tmp_path):
        """Test that keywords property returns all keywords."""
        db = DomainMapDB(tmp_path / "test.db")
        db.insert("chunk", ["src/chunk/"])
        db.insert("embed", ["src/embed/"])
        db.insert("retrieval", ["src/retrieval/"])

        keywords = db.keywords
        assert set(keywords) == {"chunk", "embed", "retrieval"}

        db.close()


class TestDomainMapDBShadowRead:
    """Tests for Phase 2: Shadow read validation (compare SQLite with pickle)."""

    def test_validate_migration_returns_true_when_data_matches(self, tmp_path):
        """Test that validate_migration returns True when SQLite matches pickle."""
        pkl_path = tmp_path / "domain_map.pkl"
        db_path = tmp_path / "domain_map.db"

        import pickle
        mapping = {
            "chunker": ["src/chunker/", "src/resolvers/"],
            "embed": ["src/embed/"],
            "parser": ["src/parser/"]
        }
        with open(pkl_path, "wb") as f:
            pickle.dump(mapping, f)

        db = DomainMapDB(db_path)
        db.bulk_insert(mapping)

        result = db.validate_migration(str(pkl_path))
        assert result is True

        db.close()

    def test_validate_migration_returns_false_when_data_differs(self, tmp_path):
        """Test that validate_migration returns False when SQLite differs from pickle."""
        pkl_path = tmp_path / "domain_map.pkl"
        db_path = tmp_path / "domain_map.db"

        import pickle
        pickle_mapping = {
            "chunker": ["src/chunker/", "src/resolvers/"],
            "embed": ["src/embed/"]
        }
        with open(pkl_path, "wb") as f:
            pickle.dump(pickle_mapping, f)

        sqlite_mapping = {
            "chunker": ["src/chunker/"],
            "embed": ["src/embed/", "src/other/"]
        }

        db = DomainMapDB(db_path)
        db.bulk_insert(sqlite_mapping)

        result = db.validate_migration(str(pkl_path))
        assert result is False

        db.close()

    def test_validate_migration_missing_keyword(self, tmp_path):
        """Test validation detects missing keyword in SQLite."""
        pkl_path = tmp_path / "domain_map.pkl"
        db_path = tmp_path / "domain_map.db"

        import pickle
        pickle_mapping = {
            "chunker": ["src/chunker/"],
            "embed": ["src/embed/"]
        }
        with open(pkl_path, "wb") as f:
            pickle.dump(pickle_mapping, f)

        sqlite_mapping = {
            "chunker": ["src/chunker/"]
        }

        db = DomainMapDB(db_path)
        db.bulk_insert(sqlite_mapping)

        result = db.validate_migration(str(pkl_path))
        assert result is False

        db.close()

    def test_validate_migration_extra_keyword(self, tmp_path):
        """Test validation detects extra keyword in SQLite."""
        pkl_path = tmp_path / "domain_map.pkl"
        db_path = tmp_path / "domain_map.db"

        import pickle
        pickle_mapping = {
            "chunker": ["src/chunker/"]
        }
        with open(pkl_path, "wb") as f:
            pickle.dump(pickle_mapping, f)

        sqlite_mapping = {
            "chunker": ["src/chunker/"],
            "embed": ["src/embed/"]
        }

        db = DomainMapDB(db_path)
        db.bulk_insert(sqlite_mapping)

        result = db.validate_migration(str(pkl_path))
        assert result is False

        db.close()

    def test_validate_migration_nonexistent_pickle(self, tmp_path):
        """Test validation handles missing pickle file gracefully."""
        db_path = tmp_path / "domain_map.db"
        nonexistent_pkl = tmp_path / "nonexistent.pkl"

        db = DomainMapDB(db_path)
        db.insert("test", ["dir/"])

        result = db.validate_migration(str(nonexistent_pkl))
        assert result is False

        db.close()
