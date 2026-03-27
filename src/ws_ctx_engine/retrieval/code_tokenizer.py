"""Code-aware tokeniser for BM25 and hybrid search.

Splits code identifiers at camelCase and snake_case boundaries, strips
punctuation, lowercases, deduplicates, and removes tokens that carry no
semantic signal (very short strings, pure numbers).

Two public functions are provided:

- :func:`tokenize_code` — for indexing chunk content (BM25 corpus documents)
- :func:`tokenize_query` — for tokenising natural language / code queries
  (additionally strips English stop words)
"""

import re

# ---------------------------------------------------------------------------
# Stop words (shared subset with retrieval.py _STOP_WORDS)
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "in", "for", "of", "and", "or", "is", "are",
        "how", "does", "what", "where", "show", "me", "find", "get",
        "use", "uses", "used", "to", "from", "with", "this", "that",
        "it", "its", "by", "be", "do", "did", "has", "have", "not",
        "can", "all", "any", "my", "our", "which", "when", "then",
        "there", "their", "about", "into", "should", "would", "could",
        "will", "may", "might", "was", "were", "been", "being", "just",
        "also", "more", "like", "than", "but", "so", "if", "at", "on",
        "return", "def", "class", "import", "from", "pass", "self",
    }
)

# Split camelCase / PascalCase at transitions: lower→upper or upper→upper+lower
_CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# Minimum token length to index
_MIN_LEN = 2


def _split_identifier(token: str) -> list[str]:
    """Split a single identifier on camelCase and snake_case boundaries."""
    # First split camelCase
    parts = _CAMEL_SPLIT.sub("_", token).split("_")
    return [p.lower() for p in parts if p]


def tokenize_code(text: str) -> list[str]:
    """Tokenise source code content for BM25 indexing.

    Steps:
    1. Extract alphanumeric + underscore tokens (identifier-like fragments).
    2. Split each at camelCase / snake_case boundaries.
    3. Lowercase and filter: drop tokens shorter than ``_MIN_LEN`` or purely
       numeric.

    Args:
        text: Raw source code string.

    Returns:
        Deduplicated list of lowercase token strings.
    """
    raw_tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text)
    seen: dict[str, None] = {}
    for raw in raw_tokens:
        for part in _split_identifier(raw):
            if len(part) >= _MIN_LEN and not part.isdigit():
                seen[part] = None
    return list(seen)


def tokenize_query(text: str) -> list[str]:
    """Tokenise a natural language or code query for BM25 search.

    Same pipeline as :func:`tokenize_code` but additionally removes English
    stop words so they don't dilute BM25 scores.

    Args:
        text: Natural language query or identifier string.

    Returns:
        Deduplicated list of lowercase token strings with stop words removed.
    """
    tokens = tokenize_code(text)
    seen: dict[str, None] = {}
    for t in tokens:
        if t not in _STOP_WORDS:
            seen[t] = None
    return list(seen)
