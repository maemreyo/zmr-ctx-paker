"""DomainKeywordMap - maps domain keywords to directories for query classification."""

import pickle
import re
from collections import defaultdict
from pathlib import Path

from ..models import CodeChunk


class DomainKeywordMap:
    """
    Maps domain keywords to directories for query classification.

    Built during indexing from file paths, then used at query time
    to classify queries and boost relevant directories.
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
        self._keyword_to_dirs: dict[str, set[str]] = defaultdict(set)

    def build(self, chunks: list[CodeChunk]) -> None:
        """Build keyword→directories map from chunks."""
        file_paths = {chunk.path for chunk in chunks}

        for file_path in file_paths:
            self._add_file(file_path)

    def _add_file(self, file_path: str) -> None:
        """Extract keywords from file path and add to map."""
        path = Path(file_path)

        for part in path.parts:
            keywords = self._extract_keywords_from_part(part)
            parent = str(path.parent)

            for kw in keywords:
                self._keyword_to_dirs[kw].add(parent)

    def _extract_keywords_from_part(self, part: str) -> list[str]:
        """Extract keywords from a path part (filename or directory)."""
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
        """Check if a token matches any keyword (exact or prefix)."""
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
    def load(cls, path: str) -> "DomainKeywordMap":
        """Load map from pickle file."""
        instance = cls()
        if Path(path).exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
                instance._keyword_to_dirs = defaultdict(set, {k: set(v) for k, v in data.items()})
        return instance

    def __repr__(self) -> str:
        return f"DomainKeywordMap(keywords={len(self.keywords)})"
