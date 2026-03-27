# Graph-Based RAG — Watch & Integration Roadmap

**Date**: March 27, 2026
**Project**: ws-ctx-engine (MCP Context Packaging)
**Status**: Phase 4 Complete — MCP graph tools (find_callers, impact_analysis, graph_search, call_chain)
**Trigger for activation**: When use case expands to cross-file reasoning / impact analysis
**Last updated**: v1.7 — Phase 4 complete: graph_tools.py, MCPToolService wiring, rate limits, 25 new tests

---

## Why This Matters

Current chunk-based RAG (astchunk + tree-sitter) handles _"find the function that does X"_ well.  
It does not handle:

- _"What breaks if I change this interface?"_
- _"Find all callers of `authenticate()` across the repo"_
- _"Trace why this module is being imported 40 times"_

Graph-based RAG answers those by modeling the codebase as a **knowledge graph** — functions, classes, and files as nodes; `CALLS`, `IMPORTS`, `INHERITS`, `CONTAINS` as edges — then letting the LLM traverse it on demand.

---

## Chosen Stack

| Component         | Choice                           | Reason                                        |
| ----------------- | -------------------------------- | --------------------------------------------- |
| Graph + vector DB | **CozoDB** (MIT, Rust)           | Embedded, no server, ~50MB RAM, HNSW built-in |
| Python binding    | `pycozo`                         | `pip install pycozo`, no native deps          |
| Storage backend   | RocksDB (prod) / in-memory (dev) | Switchable via config                         |
| Edge extraction   | Extended tree-sitter resolvers   | Already own this code                         |
| Query language    | Datalog (Cozo)                   | Simpler than Cypher, declarative              |

**Why not Memgraph / Neo4j**: require Docker daemon — violates local-only constraint.  
**Why not Grafeo**: released 2026, too immature for production dependency.

---

## Architecture — Before vs After

```
CURRENT (chunk RAG)
────────────────────────────────────────────────────────
  File → TreeSitterChunker → chunks → embeddings → vector store
                                                       ↓
                                                  cosine sim → top-K → LLM

FUTURE (chunk RAG + graph RAG, parallel)
────────────────────────────────────────────────────────
  File → TreeSitterChunker → chunks → embeddings → vector store
              ↓                                        ↓
        EdgeExtractor                            cosine sim
              ↓                                        ↓
          CozoDB                              graph traversal
        (nodes + edges)                               ↓
                  ↘                          ↙
                   ContextAssembler (merge)
                            ↓
                        LLM context package
```

The two paths are **additive**, not a replacement. Chunk path stays untouched.

---

## Integration Points

### 0. Bridge Implementation — Symbols to Graph ✅ IMPLEMENTED

**File**: `src/ws_ctx_engine/graph/builder.py` — **DONE**
**Depends on**: `CodeChunk.symbols_defined` — populated by current chunker
**Status**: `chunks_to_graph()` implemented. `Node`, `Edge` dataclasses defined.
Node ID normalization in `graph/node_id.py`. Validation in `graph/validation.py`.

Current state: `TreeSitterChunker` already emits `CodeChunk(symbols_defined=["fibonacci", "Calculator", "add", ...])`.  
Missing piece: transform those symbol lists into `(source, relation, target)` graph tuples.

```python
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Node:
    id: str       # e.g. "src/auth.py#authenticate"
    kind: str     # "file" | "function" | "class" | "method"
    name: str
    file: str
    language: str

@dataclass
class Edge:
    src: str      # node id
    relation: str # "CONTAINS" | "CALLS" | "IMPORTS" | "INHERITS"
    dst: str      # node id

def chunks_to_graph(chunks: list[CodeChunk]) -> tuple[list[Node], list[Edge]]:
    """
    Convert CodeChunk.symbols_defined into graph structure.
    This is the bridge between existing chunker output and CozoDB input.
    """
    nodes, edges = [], []

    for chunk in chunks:
        file_node = Node(
            id=chunk.filepath, kind="file",
            name=Path(chunk.filepath).name,
            file=chunk.filepath, language=chunk.language
        )
        nodes.append(file_node)

        for symbol in chunk.symbols_defined:
            # Heuristic: PascalCase = class, else function/method
            kind = "class" if symbol[0].isupper() else "function"
            sym_node = Node(
                id=f"{chunk.filepath}#{symbol}", kind=kind,
                name=symbol, file=chunk.filepath, language=chunk.language
            )
            nodes.append(sym_node)
            edges.append(Edge(src=file_node.id, relation="CONTAINS", dst=sym_node.id))

    return nodes, edges
```

> **Note**: `CALLS` and `IMPORTS` edges are **not** in `symbols_defined` — those require a deeper AST walk (see Integration Point 1 below). Start with `CONTAINS` edges only; already covers the most common graph query pattern.

#### Node ID Normalization Policy

Node IDs must be canonical before insertion — inconsistent path representations (`src/auth.py` vs `./src/auth.py` vs `/Users/me/project/src/auth.py`) silently break graph queries.

```python
import re
import subprocess
from pathlib import Path

def normalize_node_id(filepath: str, symbol: str | None = None) -> str:
    """
    Canonicalize filepath + symbol into a stable, portable node ID.

    Rules:
    1. Resolve to absolute path, then strip repo root → relative path
    2. Forward slashes only (cross-platform)
    3. Sanitize symbol: non-alphanumeric → underscore
       Handles: __init__, <lambda>, anonymous closures

    Examples:
      "./src/auth.py"                        → "src/auth.py"
      "/Users/me/project/src/auth.py"        → "src/auth.py"
      "src/auth.py" + "__init__"             → "src/auth.py#__init__"
      "src/auth.py" + "<lambda>"             → "src/auth.py#_lambda_"
    """
    path = Path(filepath).resolve()
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
        path = path.relative_to(repo_root)
    except (subprocess.CalledProcessError, ValueError):
        pass  # not a git repo — use cwd-relative path
    rel = str(path).replace("\\", "/")
    if symbol:
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", symbol)
        return f"{rel}#{safe}"
    return rel
```

Apply `normalize_node_id()` everywhere a node ID is constructed — in `chunks_to_graph()`, `extract_edges()`, and all `GraphStore` query methods. **Never construct raw f-string IDs outside this function.**

---

### 1. TreeSitterChunker — Edge Extraction Hook

**File**: `src/ws_ctx_engine/chunker/tree_sitter.py`

**Status**: ✅ FULLY IMPLEMENTED — `extract_edges(code, language, filepath)` added

Current implementation in `_extract_top_level_symbol()` covers:

| Coverage                    | Regex                  | Status    |
| --------------------------- | ---------------------- | --------- |
| Python top-level defs       | `_TOP_LEVEL_SYMBOL_RE` | ✅ Done   |
| Python indented methods     | `_INDENT_PYDEF_RE`     | ✅ Done   |
| TypeScript/JS class methods | `_INDENT_TS_METHOD_RE` | ✅ Done   |
| Rust/Go symbols             | custom resolver walk   | ⏳ Needed |

Next step is a thin wrapper that converts the existing `list[str]` output into typed `Edge` tuples — this enables plugging directly into `chunks_to_graph()` from Integration Point 0:

```python
def extract_edges(self, code: str, language: str, filepath: str) -> list[Edge]:
    """
    Thin wrapper over _extract_top_level_symbol().
    Promotes list[str] symbols → list[Edge] for graph ingestion.
    CALLS and IMPORTS extraction is future work (requires AST call-site walk).
    """
    symbols = self._extract_top_level_symbol(code)
    return [
        Edge(src=filepath, relation="CONTAINS", dst=f"{filepath}#{s}")
        for s in symbols
    ]
```

Edge types — current vs future:

| Relation     | Source   | Target           | Status                               |
| ------------ | -------- | ---------------- | ------------------------------------ |
| `CONTAINS`   | file     | function / class | ✅ Extractable now (symbols_defined) |
| `CALLS`      | function | function         | ⏳ Requires AST call-site walk       |
| `IMPORTS`    | file     | file / module    | ⏳ Requires import statement parsing |
| `INHERITS`   | class    | class            | ⏳ Requires class def walk           |
| `IMPLEMENTS` | class    | interface        | ⏳ Java, C#, TS only                 |

**Effort**: Near-zero for `CONTAINS` (wrapper only). Medium for `CALLS`/`IMPORTS` (AST walk, Python/TS first, Rust/Go later).

---

### 1.5 Graph Validation — Pre-flight Checks

**File**: `src/ws_ctx_engine/graph/validation.py` _(new)_  
**When**: Run between `chunks_to_graph()` and `GraphStore.upsert_*()` — catch bugs before they corrupt the DB.

```python
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

def validate_graph(nodes: list[Node], edges: list[Edge]) -> ValidationResult:
    """
    Check graph consistency before ingestion.

    Hard errors (block ingestion):
    - Edge endpoints reference non-existent nodes
    - Duplicate node IDs

    Warnings (log, don't block):
    - Orphan non-file nodes (symbol with no CONTAINS parent)
    """
    errors, warnings = [], []
    node_ids = set()

    # Check duplicate IDs
    for node in nodes:
        if node.id in node_ids:
            errors.append(f"Duplicate node ID: {node.id}")
        node_ids.add(node.id)

    # Check edge endpoints exist
    for edge in edges:
        if edge.src not in node_ids:
            errors.append(f"Edge src not found: {edge.src}")
        if edge.dst not in node_ids:
            errors.append(f"Edge dst not found: {edge.dst}")

    # Warn on orphan symbols
    has_parent = {e.dst for e in edges if e.relation == "CONTAINS"}
    for node in nodes:
        if node.kind != "file" and node.id not in has_parent:
            warnings.append(f"Orphan symbol: {node.id} ({node.kind})")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
```

Usage pattern — always validate before ingestion:

```python
nodes, edges = chunks_to_graph(chunks)
result = validate_graph(nodes, edges)
if not result.is_valid:
    raise GraphValidationError(result.errors)
for w in result.warnings:
    logger.warning(w)
graph_store.bulk_upsert(nodes, edges)
```

### 2. New Component — `GraphStore`

**File**: `src/ws_ctx_engine/graph/cozo_store.py` _(new)_

**Core policy**: graph features degrade gracefully — a CozoDB failure must never block the chunk RAG path.

```python
from pycozo.client import Client
import logging

logger = logging.getLogger(__name__)

class GraphStore:
    """
    CozoDB-backed graph storage. Drop-in alongside vector store, not a replacement.
    All public methods return empty results on failure — never raise to caller.
    """

    def __init__(self, storage: str = "mem"):
        # storage = "mem" | "rocksdb:<path>" | "sqlite:<path>"
        try:
            self.db = Client(storage)
            self._init_schema()
            self._healthy = True
        except Exception as e:
            logger.warning(f"CozoDB init failed ({e}). Graph features disabled.")
            self.db = None
            self._healthy = False

    def _init_schema(self):
        self.db.run("""
            :create nodes {
                id: String  =>  kind: String, name: String,
                file: String, language: String, body: String?
            }
            :create edges {
                src: String, relation: String, dst: String  =>
                weight: Float?
            }
        """)
        self.db.run("""
            ::hnsw create nodes:semantic {
                fields: [body], dim: 1536,
                dtype: F32, m: 16, ef: 32
            }
        """)

    def _query(self, datalog: str, params: dict = {}) -> list[dict]:
        """Safe query wrapper — disables self on persistent failure."""
        if not self._healthy:
            return []
        try:
            return self.db.run(datalog, params)
        except TimeoutError:
            logger.warning("CozoDB query timeout")
            return []
        except Exception as e:
            logger.error(f"CozoDB query error: {e}. Disabling graph.")
            self._healthy = False
            return []

    def upsert_node(self, node: Node): ...
    def upsert_edge(self, edge: Edge): ...
    def bulk_upsert(self, nodes: list[Node], edges: list[Edge]): ...

    def callers_of(self, fn_name: str, depth: int = 2) -> list[dict]:
        """Multi-hop: find all functions calling fn_name, up to depth hops."""
        return self._query("""
            callers[src, dst] := *edges{src, relation: "CALLS", dst}
            ?[caller, depth] := callers[caller, $fn], depth = 1
                              | callers[caller, mid], callers[mid, $fn], depth = 2
        """, {"fn": fn_name})

    def impact_of(self, file_path: str) -> list[str]:
        """Files that import or depend on file_path."""
        return self._query("""
            ?[importer] := *edges{src: importer, relation: "IMPORTS", dst: $file}
        """, {"file": file_path})

    def hybrid_search(self, query_vector: list[float], anchor_file: str) -> list[dict]:
        """Vector similarity + graph proximity in one query."""
        return self._query("""
            ?[id, name, dist] :=
                ~nodes:semantic{ id, name | query: $vec, k: 20, ef: 64, bind_distance: dist },
                *edges{ src: $anchor, relation: "IMPORTS", dst: id }
        """, {"vec": query_vector, "anchor": anchor_file})
```

---

### 3. ContextAssembler — Merge Layer

**File**: `src/ws_ctx_engine/context/assembler.py` _(new)_

```python
class ContextAssembler:
    """
    Merges chunk-RAG results with graph-RAG results.
    Chunk results = semantic relevance.
    Graph results = structural relevance (callers, imports, impacted files).
    """

    def assemble(
        self,
        query: str,
        chunk_results: list[Chunk],
        graph_results: list[CodeNode],
        token_budget: int,
    ) -> ContextPackage:
        # Dedup by file+line range
        # Priority: graph results for cross-file queries, chunks for semantic
        # Trim to token_budget
        ...
```

**Query routing** — detect which path to activate:

```python
GRAPH_SIGNALS = [
    "callers", "caller", "who calls", "import", "depends on",
    "affect", "impact", "refactor", "interface", "inherits",
    "all uses of", "cross-file",
]

def needs_graph(query: str) -> bool:
    return any(s in query.lower() for s in GRAPH_SIGNALS)
```

> **Quick Win — P0, ~1 day**: Implement signal-based routing + symbol-index keyword fallback _before_ CozoDB is built. This validates whether users actually ask cross-file questions in practice.
>
> Example flow:
>
> - Query: `"find callers of authenticate()"`
> - Router: detects `"callers"` → graph intent flagged
> - Fallback (no graph yet): search `symbols_defined` index for `"authenticate"`, return containing files ranked by match
> - Instrument: log all `needs_graph=True` hits for 1–2 weeks → real data to justify Phase 2 investment

---

### 4. MCP Server — Expose Graph Tools

**File**: `src/ws_ctx_engine/mcp/graph_tools.py` _(new)_

This is the highest-value integration point. Expose graph capabilities as **MCP tools** so Claude can call them autonomously during agentic tasks.

```python
@mcp_tool(name="find_callers")
async def find_callers(fn_name: str, depth: int = 2) -> list[dict]:
    """
    Find all functions that call fn_name, up to `depth` hops.
    Use when user asks: 'what calls X', 'who uses this function'.
    """
    return graph_store.callers_of(fn_name, depth)

@mcp_tool(name="impact_analysis")
async def impact_analysis(file_path: str) -> list[str]:
    """
    Return files affected if file_path is modified.
    Use when user asks: 'what breaks if I change X'.
    """
    return graph_store.impact_of(file_path)

@mcp_tool(name="call_chain")
async def call_chain(entry_fn: str, target_fn: str) -> list[str]:
    """
    Trace the call path from entry_fn to target_fn.
    Use for debugging 'why is function Y being called'.
    """
    ...
```

Alongside existing `chunk_retrieval` MCP tool — the LLM picks which tool fits the query intent.

---

### 5. Indexing Pipeline — Incremental Updates

**Key requirement**: Don't re-index the whole graph on every file change.

```
File change event (fswatch / inotify)
        ↓
  Affected file(s)
        ↓
  Re-chunk + re-extract edges (file scope only)
        ↓
  Delete old nodes/edges for that file in CozoDB
        ↓
  Insert new nodes/edges
        ↓
  Re-embed changed chunks → update vector store
```

CozoDB supports atomic upserts — file-scoped re-index is safe and fast (~ms per file for typical source files).

---

## Prototype Plan

### Phase 0 — Validate CozoDB Fit ✅ COMPLETE

**Script**: `scripts/phase0_cozo_validation.py`

Results against ws-ctx-engine repo (1102 chunks, 181 files, 3361 nodes, 3432 edges):

| Query                                          | Results | p50    | p95    | p99   | Target | Status |
| ---------------------------------------------- | ------- | ------ | ------ | ----- | ------ | ------ |
| `contains_of` (file → symbols, single-hop)     | 69      | 0.24ms | 0.35ms | 2.0ms | <10ms  | ✅     |
| `impact_of` (co-language files, single-hop)    | 175     | 4.96ms | 5.50ms | 7.1ms | <10ms  | ✅     |
| `find_path` (shared-symbol depth-2, multi-hop) | 0\*     | 3.56ms | 4.28ms | 6.9ms | <50ms  | ✅     |

\*`find_path` returns 0 results with CONTAINS-only edges — expected. With CALLS/IMPORTS edges (Phase 2), this becomes meaningful. Latency is already well under target.

**Insertion**: 3361 nodes + 3432 edges in 317ms (one-time, in-memory).

**Verdict: 🟢 GO** — CozoDB fit confirmed. Ready for Phase 2 (GraphStore).

---

### Phase 0.5 — Query Routing Instrumentation (1 day, can run now)

- Implement `needs_graph()` signal router
- Log all `needs_graph=True` hits in production for 1–2 weeks
- No CozoDB required — fallback to symbol-index keyword search
- **Output**: real usage data showing how often users ask cross-file questions → justifies or kills Phase 1

---

### Phase 1 — Bridge + `CONTAINS` Edges ✅ COMPLETE

- `chunks_to_graph()` implemented in `src/ws_ctx_engine/graph/builder.py`
- `extract_edges()` added on `TreeSitterChunker`
- `validate_graph()` in `src/ws_ctx_engine/graph/validation.py`
- Node ID normalization in `src/ws_ctx_engine/graph/node_id.py`
- Unit tests: 31 new tests in `tests/unit/test_graph_bridge.py` — all passing
- **Next step**: Wire into CozoDB via `GraphStore.upsert_edge()` (Phase 2)

---

### Phase 2 — GraphStore + `CALLS`/`IMPORTS` Edges (1.5 weeks) — COMPLETE

- [x] `graph/symbol_index.py` — `SymbolIndex.build()` + `resolve_symbol()` + `resolve_module()`
- [x] `chunks_to_full_graph()` in `graph/builder.py` — emits CALLS and IMPORTS edges
- [x] `graph/cozo_store.py` — `GraphStore` with RocksDB/mem/sqlite backends
- [x] `graph/store_protocol.py` — `GraphStoreProtocol` (runtime_checkable)
- [x] Validation extended: warns on CALLS→file and IMPORTS→non-file targets
- [x] `config.py` — `graph_store_enabled`, `graph_store_storage`, `graph_store_path` fields
- [x] `workflow/indexer.py` Phase 3.5 — wired into pipeline (non-fatal, additive)
- [x] `pyproject.toml` — `graph-store` optional group, mypy overrides for pycozo
- [x] Integration tests: `tests/integration/test_graph_store_indexer.py`
- [x] Benchmark: `scripts/phase2_graphstore_benchmark.py`
- [x] 98 total unit/integration tests passing

---

### Phase 3 — ContextAssembler + Query Routing (1 week) ✅ COMPLETE

- [x] `graph/signal_router.py` — `GraphIntent`, `needs_graph()`, `classify_graph_intent()` (regex, no LLM)
- [x] `graph/context_assembler.py` — `AssemblyResult`, `ContextAssembler` with dedup + score merge
- [x] `config.py` — `context_assembler_enabled: bool = True`, `graph_query_weight: float = 0.3` with `__post_init__` validation
- [x] `graph/__init__.py` — exports all 5 new symbols
- [x] `workflow/query.py` — `_load_graph_store()` helper, Phase 2.5 graph augmentation block in both `search_codebase()` and `query_and_pack()`
- [x] Unit tests: 15 tests in `tests/unit/test_signal_router.py`, 8 tests in `tests/unit/test_context_assembler.py`, 6 new tests in `tests/unit/test_config_graph_store.py`
- [x] Integration tests: 21 tests in `tests/integration/test_graph_query_pipeline.py`
- [x] 884 total unit tests passing (up from 854)

---

### Phase 4 — MCP Tool Exposure (3–4 days) ✅ COMPLETE

- [x] `mcp/graph_tools.py` — pure handler functions: `handle_find_callers`, `handle_impact_analysis`, `handle_graph_search`, `handle_call_chain`
- [x] `MCPToolService.tool_schemas()` — four new schemas with "Use when..." descriptions for LLM tool selection
- [x] `MCPToolService.call_tool()` — dispatch for `find_callers`, `impact_analysis`, `graph_search`, `call_chain`
- [x] `MCPToolService._get_graph_store()` — lazy-loaded, cached GraphStore (respects `graph_store_enabled`, degrades gracefully)
- [x] `mcp/config.py` — `find_callers: 60`, `impact_analysis: 60`, `graph_search: 60`, `call_chain: 30` rate limits
- [x] Unit tests: 19 tests in `tests/unit/test_mcp_graph_tools.py` — all passing (validation, error paths, schema assertions, rate limit assertions)
- [x] Integration tests: 6 tests in `tests/integration/test_mcp_graph_tools_integration.py` — all passing (real in-memory CozoDB, real data fixtures)
- [x] 905 total unit tests passing (up from 884)

#### Phase 4 Test Plan

**Unit Tests** (`tests/unit/test_mcp_graph_tools.py`)

| Test class | Cases | What it verifies |
|---|---|---|
| `TestFindCallers` | 6 | Happy path, empty fn_name, missing fn_name, unhealthy store, None store, empty result |
| `TestImpactAnalysis` | 5 | Happy path, empty file_path, missing file_path, unhealthy store, empty result |
| `TestGraphSearch` | 3 | Happy path, empty file_id, None store |
| `TestCallChain` | 2 | NOT_IMPLEMENTED stub, missing args INVALID_ARGUMENT |
| `TestMCPToolServiceSchemas` | 2 | All 4 tools in schemas, descriptions contain "Use when" |
| `TestRateLimits` | 1 | All 4 tools in DEFAULT_RATE_LIMITS, call_chain <= find_callers |

**Integration Tests** (`tests/integration/test_mcp_graph_tools_integration.py`)

| Test class | Cases | What it verifies |
|---|---|---|
| `TestFindCallersIntegration` | 2 | Real callers returned, nonexistent function returns empty |
| `TestImpactAnalysisIntegration` | 2 | Real importers returned, file with no importers returns empty |
| `TestGraphSearchIntegration` | 2 | Real symbols returned, file with no symbols returns empty |

**Manual E2E steps**

1. Run `wsctx index <repo>` on a Python repo with pycozo installed
2. Start MCP server: `wsctx mcp`
3. In Claude Code, ask: "what calls authenticate?" — verify `find_callers` tool is invoked
4. Ask: "what breaks if I change auth.py?" — verify `impact_analysis` tool is invoked
5. Ask: "what functions are in src/auth.py?" — verify `graph_search` tool is invoked
6. Verify graceful degradation: stop CozoDB, repeat queries — should return GRAPH_UNAVAILABLE not crash

---

## Risk Register

| Risk                                                          | Likelihood | Mitigation                                                          |
| ------------------------------------------------------------- | ---------- | ------------------------------------------------------------------- |
| Edge extraction accuracy low for Rust/Go                      | Medium     | Ship Python/TS first, gate Rust/Go on resolver quality              |
| CozoDB API breaking changes                                   | Low        | Pin version, MIT license means fork is always option                |
| Index size grows unexpectedly                                 | Low        | Benchmark Phase 2 — file-scoped nodes keep growth linear            |
| Graph results conflict with chunk results in ContextAssembler | Medium     | Start conservative: graph supplements, never replaces chunk results |
| Cozo query language learning curve                            | Low        | Datalog is simpler than Cypher; good docs at cozodb.org             |

---

## Watch List

These are things to track before committing to Phase 1:

- **Grafeo** (`pip install grafeo`) — Rust-native, fastest LDBC benchmark, HNSW+SIMD. Born March 2026, watch for stability signal over next 2–3 months. Could replace CozoDB if it matures.
- **Code-Graph-RAG** (Memgraph-based) — if it ships a local embedded mode, the MCP server + Cypher query interface is already built.
- **tree-sitter-graph** — DSL for writing graph extraction rules on tree-sitter ASTs. Could simplify Phase 1 edge extractor significantly.
- **astchunk v2+** — if CMU extends to Rust/Go, edge extraction becomes trivial.

---

## Decision Checklist (When to Actually Start)

Revisit this roadmap when **any two** of these are true:

- [ ] Users report ws-ctx-engine missing cross-file context in LLM responses
- [ ] A ws-ctx-engine use case explicitly requires impact analysis or call graph
- [ ] Grafeo reaches 6+ months of stable releases
- [ ] Team has capacity for 4-week prototype sprint
- [ ] CozoDB 0.8+ ships (watch for HNSW improvements)

Until then: **current chunk hybrid strategy remains the right call.**

---

## Appendix A: Benchmarking Suite

Cụ thể hóa target metrics từ Phase 2 thành runnable benchmark — tránh "nhanh" mơ hồ.

### Test Datasets

| Dataset | Files | Symbols | Edges | Purpose           |
| ------- | ----- | ------- | ----- | ----------------- |
| Small   | 50    | ~200    | ~300  | Dev / CI gate     |
| Medium  | 500   | ~2K     | ~3K   | Phase 2 baseline  |
| Large   | 5K    | ~20K    | ~30K  | Stress / pre-prod |

### Benchmark Queries

```python
BENCHMARK_QUERIES = [
    # Single-hop
    ("callers_of",   {"fn_name": "authenticate",  "depth": 1}),
    ("impact_of",    {"file_path": "src/models.py"}),
    # Multi-hop
    ("callers_of",   {"fn_name": "authenticate",  "depth": 3}),
    ("hybrid_search",{"query": "password validation", "anchor_file": "src/auth.py"}),
]
```

### Metrics Targets

```python
import time, statistics

def run_benchmark(store: GraphStore, n: int = 100) -> dict:
    results = {}
    for name, kwargs in BENCHMARK_QUERIES:
        latencies = []
        for _ in range(n):
            t0 = time.perf_counter()
            getattr(store, name)(**kwargs)
            latencies.append(time.perf_counter() - t0)
        results[name] = {
            "p50_ms":  round(statistics.median(latencies) * 1000, 2),
            "p95_ms":  round(sorted(latencies)[int(n * 0.95)] * 1000, 2),
            "p99_ms":  round(sorted(latencies)[int(n * 0.99)] * 1000, 2),
        }
    return results
```

| Metric                      | Target | Fail threshold |
| --------------------------- | ------ | -------------- |
| Single-hop p95              | <10ms  | >25ms          |
| Multi-hop depth=3 p95       | <50ms  | >100ms         |
| Full index — Medium dataset | <5min  | >15min         |
| Disk size per 1K files      | <5MB   | >20MB          |
| Peak RAM — Medium dataset   | <150MB | >500MB         |

Run benchmarks at end of Phase 2 and again after Phase 3 (ContextAssembler adds overhead). Regressions >20% block merge.

---

## Appendix B: Migration Path — Prototype → Production

### Phase 5 — Hardening (1 week, post Phase 4)

Roadmap currently ends at MCP tool exposure. Before treating graph RAG as production-grade:

**Persistence & backup**

```bash
# RocksDB checkpoint (atomic snapshot, no downtime)
# Add to existing ws-ctx-engine backup job
cp -r ~/.ws-ctx-engine/graph.rocksdb ~/.ws-ctx-engine/graph.rocksdb.bak
```

CozoDB RocksDB stores are plain directories — standard file backup works. Schedule daily checkpoint alongside vector store backup.

**Monitoring**

Add to existing metrics pipeline:

```python
# Emit on every GraphStore._query() call
metrics.gauge("graph.healthy",         1 if self._healthy else 0)
metrics.histogram("graph.query_ms",    latency_ms, tags=["method"])
metrics.counter("graph.query_errors",  1, tags=["error_type"])
metrics.gauge("graph.nodes_total",     node_count)
metrics.gauge("graph.edges_total",     edge_count)
```

Alert threshold: `graph.healthy = 0` for >2 minutes → PagerDuty / Slack.

**Version compatibility**

```toml
# pyproject.toml — pin minor, allow patch
pycozo = ">=0.7.5,<0.8.0"
```

Before upgrading CozoDB minor version: run full benchmark suite, check schema migration notes in Cozo changelog. RocksDB format is stable across patch versions.

**Go/No-go for production label**

- [ ] Benchmark suite passes all targets on Medium dataset
- [ ] `graph.healthy` alert firing correctly in staging
- [ ] Backup/restore tested end-to-end (restore from checkpoint, run queries)
- [ ] `GraphStore` failure tested: kill DB mid-query, confirm chunk RAG unaffected
- [ ] CozoDB version pinned in `pyproject.toml`

---

## References

- CozoDB docs: https://docs.cozodb.org
- CozoDB GitHub: https://github.com/cozodb/cozo (MIT, 3.8k stars)
- Code-Graph-RAG: https://github.com/vitali87/code-graph-rag
- CodexGraph paper (NAACL 2025): graph schema reference for CONTAINS/CALLS/INHERITS
- Grafeo: https://github.com/grafeo-dev/grafeo
- tree-sitter-graph: https://github.com/tree-sitter/tree-sitter-graph

---

| Version | Date       | Changes                                                                                                                                                                            |
| ------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | 2026-03-27 | Initial roadmap                                                                                                                                                                    |
| 1.1     | 2026-03-27 | Gap analysis: added Integration Point 0 (bridge builder), updated Point 1 to reflect partial symbol extraction impl, added Quick Win query routing note, rescoped Phase 1 timeline |
| 1.2     | 2026-03-27 | Gap analysis: Node ID normalization policy, graph pre-flight validation, GraphStore resilient error handling, Appendix A benchmarking suite, Appendix B production migration path  |
| 1.3     | 2026-03-27 | Integration Points 0 and 1 implemented: `graph/builder.py`, `graph/node_id.py`, `graph/validation.py`, `TreeSitterChunker.extract_edges()` — all 31 tests passing                  |
| 1.4     | 2026-03-27 | Phase 0 complete: `scripts/phase0_cozo_validation.py` — CozoDB fit confirmed. 3361 nodes/3432 edges, single-hop p95=5.5ms, multi-hop p95=4.3ms. GO for Phase 2                  |
| 1.5     | 2026-03-27 | Phase 2 complete: `graph/symbol_index.py` (SymbolIndex), `chunks_to_full_graph()` in builder, `graph/cozo_store.py` (GraphStore), `graph/store_protocol.py` (GraphStoreProtocol), config fields, indexer wiring, integration tests, benchmark script. 98 tests passing. |
| 1.6     | 2026-03-27 | Phase 3 complete: `graph/signal_router.py` (GraphIntent, needs_graph, classify_graph_intent), `graph/context_assembler.py` (AssemblyResult, ContextAssembler), `context_assembler_enabled`/`graph_query_weight` config fields, Phase 2.5 graph augmentation in query.py, 50 new tests (15 signal_router + 8 context_assembler + 6 config + 21 integration). 884 unit tests passing. |
| 1.7     | 2026-03-27 | Phase 4 complete: `mcp/graph_tools.py` (handle_find_callers, handle_impact_analysis, handle_graph_search, handle_call_chain), MCPToolService wiring (_get_graph_store lazy cache, 4 new schemas, call_tool dispatch), rate limits in DEFAULT_RATE_LIMITS. 25 new tests (19 unit + 6 integration). 905 unit tests passing. |
