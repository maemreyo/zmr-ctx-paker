"""
AI Rule Persistence — always include agent rule files at rank 10.0.

Files like .cursorrules, AI_RULES.md, AGENTS.md, and similar are essential
project context that agents (Claude Code, Windsurf, Cursor, etc.) rely upon.
They should appear in every pack regardless of the user's query.
"""

from pathlib import Path

# Canonical set of AI rule file names/paths that should always be included.
AI_RULE_FILES: frozenset[str] = frozenset(
    {
        ".cursorrules",
        "AI_RULES.md",
        "llm.txt",
        "AGENTS.md",
        ".claude/instructions.md",
        ".github/copilot-instructions.md",
        "CLAUDE.md",
    }
)

# Score override — large enough to always outrank any relevance score.
AI_RULE_BOOST: float = 10.0


def apply_ai_rule_boost(
    file_path: str,
    base_score: float,
    extra_files: list[str] | None = None,
    boost: float = AI_RULE_BOOST,
) -> float:
    """
    Return *base_score + boost* if *file_path* matches any AI rule file,
    otherwise return *base_score* unchanged.

    Args:
        file_path: Relative path to the file being scored.
        base_score: The existing relevance score for this file.
        extra_files: Additional user-configured rule file names/paths.
        boost: Score boost to apply (default: AI_RULE_BOOST = 10.0).

    Returns:
        Boosted score if the file is an AI rule file, else unchanged score.
    """
    candidates = set(AI_RULE_FILES)
    if extra_files:
        candidates.update(extra_files)

    filename = Path(file_path).name
    normalised = str(Path(file_path))

    for rule in candidates:
        rule_name = Path(rule).name
        if filename == rule_name:
            return base_score + boost
        if normalised == rule or normalised.endswith("/" + rule):
            return base_score + boost

    return base_score


def apply_ai_rule_boost_to_ranked(
    ranked_files: list[tuple[str, float]],
    extra_files: list[str] | None = None,
    boost: float = AI_RULE_BOOST,
) -> list[tuple[str, float]]:
    """
    Apply AI rule boost to a full ranked list and re-sort descending by score.

    Args:
        ranked_files: List of (file_path, score) tuples sorted descending.
        extra_files: Additional user-configured rule file names.
        boost: Score boost to apply.

    Returns:
        Re-sorted list with AI rule files pushed to the top.
    """
    boosted = [
        (path, apply_ai_rule_boost(path, score, extra_files=extra_files, boost=boost))
        for path, score in ranked_files
    ]
    boosted.sort(key=lambda x: x[1], reverse=True)
    return boosted
