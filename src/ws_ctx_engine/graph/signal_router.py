"""
SignalRouter — lightweight query intent classifier for graph augmentation.

Detects cross-file questions via regex pattern matching (no LLM).
All functions are pure; no side effects, no module-level state beyond compiled patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphIntent:
    """Frozen result of intent classification."""

    intent_type: str  # "callers_of" | "impact_of" | "none"
    target: str  # extracted identifier, or "" for "none"


# ---------------------------------------------------------------------------
# Compiled patterns (module-level constants, compiled once)
# ---------------------------------------------------------------------------

_CALLERS_OF_RE = re.compile(
    r"\b(callers?\s+of|who\s+calls|what\s+calls|find\s+callers|calls?\s+to)\b",
    re.IGNORECASE,
)

_IMPACT_OF_RE = re.compile(
    r"\b(imports?\s+|who\s+imports|what\s+imports|depends\s+on|dependent|impact\s+of|what\s+breaks|affect|refactor)\b",
    re.IGNORECASE,
)

_DEFINED_AT_RE = re.compile(
    r"\bwhere\s+is\b.+\bdefined\b",
    re.IGNORECASE,
)

# Identifier token pattern for target extraction
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_.]*")

_STOP_WORDS = frozenset(
    {
        "calls",
        "imports",
        "what",
        "who",
        "where",
        "is",
        "of",
        "the",
        "on",
        "if",
        "change",
        "affect",
        "find",
        "callers",
        "caller",
        "import",
        "impacts",
        "impact",
        "breaks",
        "depends",
        "dependent",
        "refactor",
        "defined",
        "how",
        "does",
        "show",
        "me",
        "I",
        "a",
        "an",
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def needs_graph(query: str) -> bool:
    """Return True if the query signals a graph-traversal intent."""
    if not query:
        return False
    return bool(
        _CALLERS_OF_RE.search(query) or _IMPACT_OF_RE.search(query) or _DEFINED_AT_RE.search(query)
    )


def classify_graph_intent(query: str) -> GraphIntent:
    """
    Classify the query intent and extract the primary target identifier.

    Returns a frozen GraphIntent with:
    - intent_type: "callers_of" | "impact_of" | "none"
    - target: first meaningful identifier in the query, or ""
    """
    if not query:
        return GraphIntent(intent_type="none", target="")

    if _CALLERS_OF_RE.search(query) or _DEFINED_AT_RE.search(query):
        return GraphIntent(intent_type="callers_of", target=_extract_target(query))

    if _IMPACT_OF_RE.search(query):
        return GraphIntent(intent_type="impact_of", target=_extract_target(query))

    return GraphIntent(intent_type="none", target="")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _extract_target(query: str) -> str:
    """
    Extract the first non-stop-word identifier token from the query.

    Scans left-to-right, skips stop words, returns the first match or "".
    """
    for token in _IDENT_RE.findall(query):
        if isinstance(token, str) and token.lower() not in _STOP_WORDS:
            return token
    return ""
