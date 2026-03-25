# Query Classification & Domain Keyword Map — Design Spec

**Date:** 2026-03-24
**Status:** Approved
**Scope:** Improve retrieval accuracy for conceptual queries (e.g. "chunking logic flow") by adding a three-way query classifier and a discovered-at-index-time domain keyword map.

---

## Problem

The current hybrid retrieval engine (semantic + PageRank + symbol boost + path boost) still misranks conceptual queries that use domain vocabulary without naming a specific class or function. Example:

- Query `"chunking logic flow"` → top result: `vector_index/vector_index.py` (wrong)
- Root cause: the embedding for "flow" is semantically similar to the vector index's data-flow code; no symbol or exact path match pulls `chunker/` files up.

---

## Goals

1. Correctly rank `chunker/` files first for queries containing domain terms like `"chunking"`, `"parser"`, `"resolver"`.
2. Keep existing ranking quality for symbol queries (`"TreeSitterChunker"`) and semantic queries (`"how does PageRank work"`).
3. Work generically across any repo — no hardcoded mappings.

---

## Non-Goals

- Machine-learned query intent classification.
- Per-token learned weights.
- Changing the semantic embedding model.

---

## Architecture

### New Component: `DomainKeywordMap`

A lightweight data object built during indexing that maps domain keywords to the directories that contain them.

```
.ws-ctx-engine/
├── vector.idx        # LEANN embeddings (existing)
├── graph.pkl         # RepoMap dependency graph (existing)
├── metadata.json     # Index metadata (existing)
└── domain_map.pkl    # NEW: keyword → [directory] mapping
```

**Location:** `src/ws_ctx_engine/domain_map/domain_map.py`

**Interface:**
```python
class DomainKeywordMap:
    def build(self, chunks: List[CodeChunk]) -> None
    def save(self, path: str) -> None
    @classmethod
    def load(cls, path: str) -> "DomainKeywordMap"
    @property
    def keywords(self) -> Set[str]
    def directories_for(self, keyword: str) -> List[str]
```

**Build algorithm:**
1. For each unique file path in `chunks`, split on `/`, `_`, `-`, `.`.
2. Filter noise words: `{"py", "js", "ts", "rs", "src", "lib", "test", "tests", "init", "main", "utils", "helpers", "base", "common"}`.
3. For each remaining stem, record the file's parent directory path.
4. Deduplicate: each (keyword, directory) pair stored once.

**Example output for this repo:**
```python
{
  "chunker":   ["chunker/", "chunker/resolvers/"],
  "resolver":  ["chunker/resolvers/"],
  "graph":     ["graph/"],
  "retrieval": ["retrieval/"],
  "vector":    ["vector_index/"],
  "budget":    ["budget/"],
  "workflow":  ["workflow/"],
  "packer":    ["packer/"],
  "markdown":  ["chunker/"],
  "typescript": ["chunker/resolvers/"],
}
```

**Config override** (optional, in `config.yaml`):
```yaml
domain_map:
  enabled: true
  extra_mappings:
    "auth": ["src/middleware/", "src/auth/"]
```

---

## Query Classifier

**Location:** `_classify_query()` method on `RetrievalEngine`

### Three-way classification

| Type | Detection heuristic | Example query |
|---|---|---|
| `symbol` | Contains PascalCase identifier OR token with `_` and len > 4 | `"TreeSitterChunker parses"` |
| `path-dominant` | Any token (or its 5-char prefix stem) matches a domain keyword | `"chunking logic flow"` |
| `semantic-dominant` | Neither of the above | `"explain how dependencies work"` |

**Classification logic:**
```python
def _classify_query(query: str, tokens: Set[str], domain_map: DomainKeywordMap) -> str:
    # 1. Symbol: PascalCase or snake_case
    if re.search(r'\b[A-Z][a-z]+[A-Z]', query):
        return "symbol"
    if any('_' in t and len(t) > 4 for t in tokens):
        return "symbol"

    # 2. Path-dominant: token or its stem matches a domain keyword
    for token in tokens:
        if token in domain_map.keywords:
            return "path-dominant"
        for kw in domain_map.keywords:
            prefix_len = min(5, len(token), len(kw))
            if prefix_len >= 5 and token[:prefix_len] == kw[:prefix_len]:
                return "path-dominant"

    # 3. Default
    return "semantic-dominant"
```

### Effective boost weight matrix

The base `symbol_boost`, `path_boost`, and new `domain_boost` constructor parameters are multiplied by per-type scalars:

| Query type | symbol multiplier | path multiplier | domain multiplier |
|---|---|---|---|
| `symbol` | × 1.5 | × 0.5 | × 0.3 |
| `path-dominant` | × 0.5 | × 1.5 | × 1.0 |
| `semantic-dominant` | × 0.2 | × 0.2 | × 0.2 |

This means semantic-dominant queries get minimal additive noise from path/symbol/domain signals, letting the embedding score dominate.

---

## Domain Score Computation

**New method:** `_compute_domain_scores(tokens, all_files, domain_map)`

Algorithm:
1. For each query token, look up matching domain keywords (exact + 5-char prefix).
2. Collect all directories associated with those keywords.
3. Any indexed file whose path starts with a matched directory gets score `1.0`.
4. Files not in any matched directory get `0.0` (omitted from dict).

```python
def _compute_domain_scores(tokens, all_files, domain_map) -> Dict[str, float]:
    matched_dirs = set()
    for token in tokens:
        for kw in domain_map.keywords:
            prefix_len = min(5, len(token), len(kw))
            if token == kw or (prefix_len >= 5 and token[:prefix_len] == kw[:prefix_len]):
                matched_dirs.update(domain_map.directories_for(kw))

    return {
        fp: 1.0
        for fp in all_files
        if any(fp.startswith(d) for d in matched_dirs)
    }
```

---

## Updated `retrieve()` Flow

```
1.  semantic_scores  ← vector_index.search(query, top_k)
2.  pagerank_scores  ← graph.pagerank(changed_files)
3.  merged           ← _normalize(semantic) × semantic_weight
                     + _normalize(pagerank) × pagerank_weight
4.  tokens           ← _extract_query_tokens(query)
5.  query_type       ← _classify_query(query, tokens, domain_map)
6.  eff_symbol, eff_path, eff_domain ← apply multipliers per query_type
7.  symbol_scores    ← _compute_symbol_scores(tokens, file_symbols)
8.  path_scores      ← _compute_path_scores(tokens, all_files)
9.  domain_scores    ← _compute_domain_scores(tokens, all_files, domain_map)
10. merged          += eff_symbol × symbol_scores
                    += eff_path   × path_scores
                    += eff_domain × domain_scores
11. Apply test_penalty multiplicatively for test files
12. Final _normalize(merged) → all scores ∈ [0, 1]
13. Sort descending, return top_k
```

---

## Files Changed

| File | Type | Change |
|---|---|---|
| `src/ws_ctx_engine/domain_map/__init__.py` | New | Export `DomainKeywordMap` |
| `src/ws_ctx_engine/domain_map/domain_map.py` | New | `DomainKeywordMap` class |
| `src/ws_ctx_engine/workflow/indexer.py` | Modified | Phase 6: build + save domain map |
| `src/ws_ctx_engine/workflow/query.py` | Modified | Load `domain_map.pkl` at query time |
| `src/ws_ctx_engine/retrieval/retrieval.py` | Modified | `domain_map` param, classifier, domain scorer, effective weights |
| `tests/unit/test_domain_map.py` | New | Unit tests for keyword extraction and map building |
| `tests/unit/test_retrieval.py` | Modified | Tests for classifier and domain scoring integration |

---

## `RetrievalEngine` Constructor — new parameters

```python
def __init__(
    self,
    vector_index: VectorIndex,
    graph: RepoMapGraph,
    semantic_weight: float = 0.6,
    pagerank_weight: float = 0.4,
    symbol_boost: float = 0.3,
    path_boost: float = 0.2,
    domain_boost: float = 0.4,       # NEW
    test_penalty: float = 0.5,
    domain_map=None,                  # NEW — optional DomainKeywordMap
):
```

`domain_map=None` means the engine degrades gracefully when no domain map has been built — the classifier falls back to `"semantic-dominant"` for all queries.

---

## `load_indexes()` Changes

`workflow/query.py::load_indexes()` (or equivalent) loads all four artifacts:

```python
vector_index = load_vector_index(index_dir / "vector.idx")
graph = load_graph(index_dir / "graph.pkl")
metadata = load_metadata(index_dir / "metadata.json")
domain_map = DomainKeywordMap.load(index_dir / "domain_map.pkl")  # NEW
```

If `domain_map.pkl` does not exist (e.g. old index), `load_indexes()` returns `domain_map=None` and logs a warning suggesting a re-index.

---

## Testing Strategy

### `test_domain_map.py`
- Keyword extraction from a path like `"chunker/resolvers/python.py"` → `{"chunker", "resolvers", "python"}`.
- Noise words filtered (`"py"`, `"init"`, etc.).
- `build()` from a chunk list produces correct keyword→directory mapping.
- `save()` / `load()` round-trip preserves the map.

### `test_retrieval.py` (additions)
- `_classify_query("TreeSitterChunker parses", ...)` → `"symbol"`.
- `_classify_query("chunking logic flow", ...)` → `"path-dominant"` when `"chunker"` is in domain_map.
- `_classify_query("explain dependency graph", ...)` → `"semantic-dominant"` when no domain kw matches.
- `_compute_domain_scores` returns score `1.0` for files under matched directory, `0.0` for others.
- Integration: `retrieve("chunking logic flow")` ranks `chunker/base.py` above `vector_index/vector_index.py`.

---

## Trace: "chunking logic flow" After This Change

```
tokens:       {"chunking", "logic", "flow"}
query_type:   "path-dominant"  ("chunking" prefix "chunk" matches kw "chunker")
eff_domain:   domain_boost × 1.0 = 0.4

domain_scores:
  chunker/base.py          → 1.0  (in chunker/)
  chunker/tree_sitter.py   → 1.0
  chunker/regex.py         → 1.0
  chunker/resolvers/...    → 1.0
  vector_index/...         → 0.0  (no match)

After boost:
  chunker/base.py          base + 0.4 × 1.0 = base + 0.4
  vector_index/...         base + 0.0

After final normalise → chunker files rank above vector_index. ✓
```
