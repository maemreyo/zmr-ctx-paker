"""Data models for ws-ctx-engine."""

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CodeChunk:
    """Represents a parsed code segment with metadata.

    This class encapsulates a segment of source code along with its metadata,
    including location information, defined and referenced symbols, and language.

    Attributes:
        path: Relative path from repository root
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (inclusive)
        content: Raw source code content
        symbols_defined: Functions/classes defined in this chunk
        symbols_referenced: Imports and function calls
        language: Programming language (python, javascript, etc)
    """

    path: str
    start_line: int
    end_line: int
    content: str
    symbols_defined: list[str]
    symbols_referenced: list[str]
    language: str

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict for incremental index caching."""
        return {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "symbols_defined": self.symbols_defined,
            "symbols_referenced": self.symbols_referenced,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CodeChunk":
        """Deserialise from a dict produced by :meth:`to_dict`."""
        return cls(
            path=data["path"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            content=data["content"],
            symbols_defined=data.get("symbols_defined", []),
            symbols_referenced=data.get("symbols_referenced", []),
            language=data.get("language", ""),
        )

    def token_count(self, encoding: Any) -> int:
        """Count tokens using tiktoken encoding.

        Args:
            encoding: A tiktoken encoding instance (e.g., tiktoken.get_encoding("cl100k_base"))

        Returns:
            Number of tokens in the content

        Example:
            >>> import tiktoken
            >>> encoding = tiktoken.get_encoding("cl100k_base")
            >>> chunk = CodeChunk(
            ...     path="src/main.py",
            ...     start_line=1,
            ...     end_line=10,
            ...     content="def hello():\\n    print('Hello')",
            ...     symbols_defined=["hello"],
            ...     symbols_referenced=[],
            ...     language="python"
            ... )
            >>> chunk.token_count(encoding)
            12
        """
        return len(encoding.encode(self.content))


@dataclass
class IndexMetadata:
    """Metadata stored with indexes for staleness detection.

    This class stores metadata about repository indexes to enable staleness
    detection and automatic rebuilding when files change.

    Attributes:
        created_at: Timestamp when the index was created
        repo_path: Path to the repository root
        file_count: Number of files that were indexed
        backend: Backend used for indexing (e.g., "LEANNIndex+IGraphRepoMap")
        file_hashes: Dictionary mapping file paths to SHA256 content hashes
    """

    created_at: datetime
    repo_path: str
    file_count: int
    backend: str
    file_hashes: dict[str, str]

    def is_stale(self, repo_path: str) -> bool:
        """Check if any files have been modified since index creation.

        Detects staleness by comparing stored file hashes with current file
        content. Returns True if any file is missing or has changed.

        Args:
            repo_path: Path to the repository root to check

        Returns:
            True if any indexed file is missing or modified, False otherwise

        Example:
            >>> from datetime import datetime
            >>> metadata = IndexMetadata(
            ...     created_at=datetime.now(),
            ...     repo_path="/path/to/repo",
            ...     file_count=10,
            ...     backend="LEANNIndex+IGraphRepoMap",
            ...     file_hashes={"src/main.py": "abc123..."}
            ... )
            >>> metadata.is_stale("/path/to/repo")
            False
        """
        for path, old_hash in self.file_hashes.items():
            full_path = os.path.join(repo_path, path)

            # File was deleted
            if not os.path.exists(full_path):
                return True

            # Calculate current hash
            try:
                with open(full_path, "rb") as f:
                    new_hash = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                # If we can't read the file, consider it stale
                return True

            # File content changed
            if new_hash != old_hash:
                return True

        return False
