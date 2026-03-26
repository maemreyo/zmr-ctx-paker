# Ranking Module

> **Module Path**: `src/ws_ctx_engine/ranking/`

## Purpose

The Ranking module ensures that AI rule files — project-level instructions consumed by coding agents — are always included in every context pack, regardless of the user's query. It applies a deterministic score override large enough to outrank any relevance score produced by the retrieval pipeline.

## Architecture

```
ranking/
├── __init__.py      # Public exports
├── ranker.py        # AI rule boost functions and AI_RULE_FILES registry
└── phase_ranker.py  # Phase-aware ranking adjustments (agent phases)
```

## AI Rule Files

The module maintains a canonical set of AI rule file names that agents (Claude Code, Cursor, Windsurf, GitHub Copilot, etc.) rely on for project instructions:

```python
AI_RULE_FILES: frozenset[str] = frozenset({
    ".cursorrules",
    "AI_RULES.md",
    "llm.txt",
    "AGENTS.md",
    ".claude/instructions.md",
    ".github/copilot-instructions.md",
    "CLAUDE.md",
})
```

Matching is done by **filename** (basename) or **normalized path**, so `src/.cursorrules` matches `.cursorrules`.

## Score Override

```python
AI_RULE_BOOST: float = 10.0
```

A boost of `10.0` is added on top of any existing relevance score. Since the retrieval pipeline normalizes final scores to `[0, 1]`, a boost of `10.0` guarantees AI rule files always sort to the top of the ranked list.

## Key Functions

### apply_ai_rule_boost()

```python
def apply_ai_rule_boost(
    file_path: str,
    base_score: float,
    extra_files: list[str] | None = None,
    boost: float = AI_RULE_BOOST,
) -> float:
    """
    Return base_score + boost if file_path matches any AI rule file,
    otherwise return base_score unchanged.
    """
```

**Args:**

| Parameter    | Default          | Description                                    |
| ------------ | ---------------- | ---------------------------------------------- |
| `file_path`  | Required         | Relative path to the file being scored         |
| `base_score` | Required         | Existing relevance score from retrieval engine |
| `extra_files`| None             | Additional user-configured rule file names     |
| `boost`      | `AI_RULE_BOOST`  | Score boost to add (default: 10.0)             |

**Returns:** Boosted score if file matches, else original score unchanged.

### apply_ai_rule_boost_to_ranked()

```python
def apply_ai_rule_boost_to_ranked(
    ranked_files: list[tuple[str, float]],
    extra_files: list[str] | None = None,
    boost: float = AI_RULE_BOOST,
) -> list[tuple[str, float]]:
    """
    Apply AI rule boost to a full ranked list and re-sort descending by score.
    """
```

Convenience function that applies `apply_ai_rule_boost` to every entry in the ranked list and re-sorts the result. This is the primary entry point called by the retrieval workflow.

## Matching Logic

```python
filename = Path(file_path).name        # e.g., "CLAUDE.md"
normalised = str(Path(file_path))      # e.g., "src/CLAUDE.md"

for rule in candidates:
    rule_name = Path(rule).name
    if filename == rule_name:          # basename match
        return base_score + boost
    if normalised == rule or normalised.endswith("/" + rule):  # path match
        return base_score + boost
```

**Examples:**

| `file_path` | Matches rule | Result |
| ----------- | ------------ | ------ |
| `CLAUDE.md` | `CLAUDE.md` | boosted |
| `docs/CLAUDE.md` | `CLAUDE.md` | boosted (basename match) |
| `.claude/instructions.md` | `.claude/instructions.md` | boosted (path match) |
| `src/auth.py` | — | unchanged |

## Configuration

Users can extend the built-in list via the `extra_files` parameter. In the workflow, this is read from the config:

```yaml
# .ws-ctx-engine.yaml
ranking:
  extra_ai_rule_files:
    - "MY_RULES.md"
    - ".windsurf/rules.md"
```

## Code Example

```python
from ws_ctx_engine.ranking.ranker import apply_ai_rule_boost_to_ranked

# After retrieval produces ranked files
ranked = [
    ("src/auth.py", 0.95),
    ("src/user.py", 0.82),
    ("CLAUDE.md", 0.10),     # Low retrieval score — will be boosted
    ("src/db.py", 0.73),
]

boosted = apply_ai_rule_boost_to_ranked(ranked)
# Result:
# [
#   ("CLAUDE.md", 10.10),   # Guaranteed top position
#   ("src/auth.py", 0.95),
#   ("src/user.py", 0.82),
#   ("src/db.py", 0.73),
# ]
```

## Integration with Retrieval Pipeline

The ranking module is applied **after** the retrieval engine scores files and **before** the budget manager selects the final set:

```
RetrievalEngine.retrieve()
    → apply_ai_rule_boost_to_ranked()   ← ranking module
        → BudgetManager.select()
```

This ensures AI rule files are selected by the budget manager even when they have low semantic relevance to the query.

## Related Modules

- [Retrieval](./retrieval.md) — Produces the ranked list that this module post-processes
- [Budget](./budget.md) — Selects files from the boosted ranked list within token limits
- [Workflow](./workflow.md) — Orchestrates the full pipeline
