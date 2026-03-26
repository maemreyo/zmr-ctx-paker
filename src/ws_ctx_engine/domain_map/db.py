"""DomainMapDB - SQLite backend for domain keyword to directory mapping.

Phase 1: Parallel Write - writes to both pickle and SQLite
Phase 2: Shadow Read - validates SQLite against pickle
Phase 3: SQLite Primary - switch to SQLite only
Phase 4: Cleanup - remove pickle code
"""

from __future__ import annotations

import pickle
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..logger import get_logger

logger = get_logger(__name__)


class DomainMapDB:
    """
    SQLite-backed domain keyword to directory mapping.

    Drop-in replacement for pickle-based DomainKeywordMap with:
    - WAL mode for concurrent reads
    - Normalized schema for efficient queries
    - Prefix search capability

    Migration phases:
    1. Parallel Write - write to both pickle and SQLite
    2. Shadow Read - validate SQLite against pickle
    3. SQLite Primary - use SQLite only
    4. Cleanup - remove pickle code
    """

    DB_VERSION = 1

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Lazy connection with WAL mode for concurrent reads."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA cache_size=-64000")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Context manager for transactions."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );

                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY,
                    kw TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    created INTEGER DEFAULT (unixepoch())
                );

                CREATE TABLE IF NOT EXISTS directories (
                    id INTEGER PRIMARY KEY,
                    path TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS keyword_dirs (
                    keyword_id INTEGER NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
                    dir_id INTEGER NOT NULL REFERENCES directories(id) ON DELETE CASCADE,
                    PRIMARY KEY (keyword_id, dir_id)
                );

                CREATE INDEX IF NOT EXISTS idx_kw ON keywords(kw);
                CREATE INDEX IF NOT EXISTS idx_kw_pfx ON keywords(kw COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_kd_kid ON keyword_dirs(keyword_id);
            """
            )

            conn.execute(
                "INSERT OR IGNORE INTO meta VALUES ('version', ?)", (str(self.DB_VERSION),)
            )

    def insert(self, keyword: str, directories: list[str]) -> None:
        """
        Insert or replace a keyword with its directories.

        Args:
            keyword: Domain keyword (e.g., "chunker", "embed")
            directories: List of directory paths associated with keyword
        """
        if not directories:
            return

        with self._transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO keywords(kw) VALUES (?)", (keyword.lower(),))
            kid = conn.execute(
                "SELECT id FROM keywords WHERE kw = ?", (keyword.lower(),)
            ).fetchone()["id"]

            for path in directories:
                normalized_path = str(Path(path))
                conn.execute(
                    "INSERT OR IGNORE INTO directories(path) VALUES (?)", (normalized_path,)
                )
                did = conn.execute(
                    "SELECT id FROM directories WHERE path = ?", (normalized_path,)
                ).fetchone()["id"]
                conn.execute("INSERT OR IGNORE INTO keyword_dirs VALUES (?, ?)", (kid, did))

    def bulk_insert(self, mapping: dict[str, list[str]]) -> None:
        """
        Fast bulk load from existing dict.

        Args:
            mapping: Dict of keyword -> list of directories
        """
        if not mapping:
            return

        with self._transaction() as conn:
            for kw, dirs in mapping.items():
                if not dirs:
                    continue
                conn.execute("INSERT OR IGNORE INTO keywords(kw) VALUES (?)", (kw.lower(),))

            for dirs in mapping.values():
                if not dirs:
                    continue
                for d in dirs:
                    normalized_path = str(Path(d))
                    conn.execute(
                        "INSERT OR IGNORE INTO directories(path) VALUES (?)", (normalized_path,)
                    )

            for kw, dirs in mapping.items():
                if not dirs:
                    continue
                kw_lower = kw.lower()
                kid_row = conn.execute(
                    "SELECT id FROM keywords WHERE kw = ?", (kw_lower,)
                ).fetchone()
                if kid_row is None:
                    continue
                kid = kid_row["id"]
                for d in dirs:
                    normalized_path = str(Path(d))
                    did_row = conn.execute(
                        "SELECT id FROM directories WHERE path = ?", (normalized_path,)
                    ).fetchone()
                    if did_row is None:
                        continue
                    did = did_row["id"]
                    conn.execute("INSERT OR IGNORE INTO keyword_dirs VALUES (?, ?)", (kid, did))

    def get(self, keyword: str) -> list[str]:
        """
        Get directories for a keyword.

        Drop-in replacement for dict.get().

        Args:
            keyword: Keyword to look up

        Returns:
            List of directory paths, empty list if not found
        """
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT d.path
            FROM directories d
            JOIN keyword_dirs kd ON d.id = kd.dir_id
            JOIN keywords k ON k.id = kd.keyword_id
            WHERE k.kw = ?
        """,
            (keyword.lower(),),
        ).fetchall()
        return [r["path"] for r in rows]

    def directories_for(self, keyword: str) -> list[str]:
        """
        Get directories for a keyword (alias for get()).

        Used by RetrievalEngine for domain-based scoring.

        Args:
            keyword: Keyword to look up

        Returns:
            List of directory paths, empty list if not found
        """
        return self.get(keyword)

    def prefix_search(self, prefix: str) -> dict[str, list[str]]:
        """
        Find all keywords starting with prefix.

        Args:
            prefix: Prefix to search for

        Returns:
            Dict of keyword -> list of directories
        """
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT k.kw, d.path
            FROM keywords k
            JOIN keyword_dirs kd ON k.id = kd.keyword_id
            JOIN directories d ON d.id = kd.dir_id
            WHERE k.kw LIKE ?
            ORDER BY k.kw
        """,
            (f"{prefix.lower()}%",),
        ).fetchall()

        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row["kw"], []).append(row["path"])
        return result

    @property
    def keywords(self) -> set[str]:
        """Return all keywords in the database."""
        conn = self._get_conn()
        rows = conn.execute("SELECT kw FROM keywords").fetchall()
        return {r["kw"] for r in rows}

    def stats(self) -> dict:
        """Return database statistics."""
        conn = self._get_conn()
        return {
            "keywords": conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0],
            "directories": conn.execute("SELECT COUNT(*) FROM directories").fetchone()[0],
            "mappings": conn.execute("SELECT COUNT(*) FROM keyword_dirs").fetchone()[0],
            "db_size_kb": self.db_path.stat().st_size // 1024 if self.db_path.exists() else 0,
        }

    def __contains__(self, keyword: str) -> bool:
        """Check if keyword exists."""
        return bool(self.get(keyword))

    def keyword_matches(self, token: str) -> bool:
        """
        Check if token matches any keyword (exact or prefix).

        Used by RetrievalEngine for query classification.

        Args:
            token: Token to check

        Returns:
            True if token matches any keyword exactly or via prefix
        """
        token_lower = token.lower()
        if token_lower in self.keywords:
            return True
        for kw in self.keywords:
            prefix_len = min(5, len(token_lower), len(kw))
            if prefix_len >= 4 and token_lower[:prefix_len] == kw[:prefix_len]:
                return True
        return False

    def close(self) -> None:
        """Close database connection with WAL checkpoint."""
        if self._conn:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._conn.close()
            except Exception:
                pass
        self._conn = None

    def __enter__(self) -> DomainMapDB:
        return self

    def __exit__(self, *_args: object) -> None:
        if self._conn:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._conn.close()
            except Exception:
                pass
        self._conn = None

    @classmethod
    def migrate_from_pickle(cls, pkl_path: str | Path, db_path: str | Path) -> DomainMapDB:
        """
        Migrate from pickle file to SQLite.

        Args:
            pkl_path: Path to existing pickle file
            db_path: Path for new SQLite database

        Returns:
            New DomainMapDB instance with migrated data
        """
        pkl_path = Path(pkl_path)
        if not pkl_path.exists():
            raise FileNotFoundError(f"Pickle file not found: {pkl_path}")

        with open(pkl_path, "rb") as f:
            old_map: dict[str, list[str]] = pickle.load(f)

        db = cls(db_path)
        db.bulk_insert(old_map)
        logger.info(f"Migrated {len(old_map)} keywords from pickle to SQLite")

        return db

    def validate_migration(self, pkl_path: str | Path) -> bool:
        """
        Phase 2: Validate that SQLite data matches pickle data (shadow read).

        Compares all keywords and their directory mappings between
        the SQLite database and the pickle file.

        Args:
            pkl_path: Path to pickle file to compare against

        Returns:
            True if data matches exactly, False otherwise
        """
        pkl_path = Path(pkl_path)
        if not pkl_path.exists():
            return False

        try:
            with open(pkl_path, "rb") as f:
                pickle_data: dict[str, list[str]] = pickle.load(f)
        except Exception:
            return False

        conn = self._get_conn()

        sqlite_keywords = {r["kw"] for r in conn.execute("SELECT kw FROM keywords").fetchall()}
        pickle_keywords = set(pickle_data.keys())

        if sqlite_keywords != pickle_keywords:
            return False

        for kw, pickle_dirs in pickle_data.items():
            sqlite_dirs = self.get(kw)
            sqlite_dirs_set = set(sqlite_dirs)
            pickle_dirs_set = {str(Path(d)) for d in pickle_dirs}
            if sqlite_dirs_set != pickle_dirs_set:
                return False

        return True


class DomainKeywordMap:
    """
    Pickle-based domain keyword map (legacy, for Phase 1-2 compatibility).

    This class is kept for parallel write phase.
    Use DomainMapDB for production after Phase 3.
    """

    NOISE_WORDS: set[str] = {
        "py",
        "js",
        "ts",
        "rs",
        "jsx",
        "tsx",
        "pyc",
        "pyd",
        "src",
        "lib",
        "bin",
        "obj",
        "dist",
        "build",
        "out",
        "test",
        "tests",
        "spec",
        "example",
        "examples",
        "init",
        "main",
        "index",
        "conf",
        "config",
        "utils",
        "helpers",
        "base",
        "common",
        "core",
        "impl",
        "interface",
        "abstract",
        "model",
        "models",
        "schema",
        "controller",
        "service",
        "repository",
        "view",
        "views",
        "template",
        "templates",
        "static",
        "assets",
        "public",
        "private",
        "protected",
        "internal",
        "external",
        "default",
        "unknown",
    }

    def __init__(self) -> None:
        self._keyword_to_dirs: dict[str, set[str]] = {}

    def build(self, chunks: list) -> None:
        """Build keyword→directories map from chunks."""
        from ..models import CodeChunk

        file_paths = {chunk.path for chunk in chunks if isinstance(chunk, CodeChunk)}

        for file_path in file_paths:
            self._add_file(file_path)

    def _add_file(self, file_path: str) -> None:
        """Extract keywords from file path and add to map."""
        from pathlib import Path

        path = Path(file_path)

        for part in path.parts:
            keywords = self._extract_keywords_from_part(part)
            parent = str(path.parent)

            for kw in keywords:
                self._keyword_to_dirs.setdefault(kw, set()).add(parent)

    def _extract_keywords_from_part(self, part: str) -> list[str]:
        """Extract keywords from a path part."""
        import re

        cleaned = re.sub(r"[-_\.]", " ", part)
        tokens = cleaned.split()

        keywords = []
        for token in tokens:
            token_lower = token.lower()
            if len(token_lower) > 2 and token_lower not in self.NOISE_WORDS:
                keywords.append(token_lower)

        return keywords

    @property
    def keywords(self) -> set[str]:
        """Return all registered keywords."""
        return set(self._keyword_to_dirs.keys())

    def directories_for(self, keyword: str) -> list[str]:
        """Return list of directories associated with a keyword."""
        return list(self._keyword_to_dirs.get(keyword.lower(), set()))

    def keyword_matches(self, token: str) -> bool:
        """Check if a token matches any keyword."""
        token_lower = token.lower()
        if token_lower in self._keyword_to_dirs:
            return True

        for kw in self._keyword_to_dirs:
            prefix_len = min(5, len(token_lower), len(kw))
            if prefix_len >= 4 and token_lower[:prefix_len] == kw[:prefix_len]:
                return True

        return False

    def save(self, path: str) -> None:
        """Save map to pickle file."""
        with open(path, "wb") as f:
            pickle.dump(dict(self._keyword_to_dirs), f)

    @classmethod
    def load(cls, path: str) -> DomainKeywordMap:
        """Load map from pickle file."""
        instance = cls()
        if Path(path).exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
                instance._keyword_to_dirs = {k: set(v) for k, v in data.items()}
        return instance

    def __repr__(self) -> str:
        return f"DomainKeywordMap(keywords={len(self.keywords)})"
