# Architecture Summary: ws-ctx-engine

**Version**: v0.2.0a0 (Final)  
**Last Updated**: March 29, 2026  
**Status**: Archived - Open Source Reference

---

## Overview

ws-ctx-engine is a production-grade codebase packaging system that intelligently selects and formats source code for Large Language Model (LLM) consumption. The system uses **hybrid ranking** (semantic search + PageRank) and **token budget management** to maximize context quality within LLM window constraints.

### Design Philosophy

1. **Never Fail**: 6-level fallback hierarchy ensures graceful degradation
2. **Token-Aware**: Precise counting with tiktoken (±2% accuracy)
3. **Modular**: Each component independently testable and replaceable
4. **Production-First**: Rust acceleration, incremental indexing, staleness detection
5. **Agent-Ready**: MCP server, session deduplication, phase-aware ranking

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface                             │
│   wsctx index/query/pack/status/vacuum/reindex-domain           │
│   - Typer framework with Rich output                             │
│   - Configurable via .ws-ctx-engine.yaml                         │
│   - Multiple entry points: wsctx, ws-ctx-engine                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                   Workflow Orchestrator                          │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ indexer.py   │    │  query.py    │    │ workflow.py  │     │
│   │ (build)      │    │ (retrieval)  │    │ (full pipe)  │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
┌───────▼───────┐ ┌───▼────────┐ ┌──▼──────────┐ ┌─▼──────────┐
│   Chunking    │ │  Retrieval │ │   Ranking   │ │  Backend   │
│   Module      │ │  Engine    │ │   Module    │ │  Selector  │
│               │ │            │ │             │ │            │
│ • AST Parser  │ │ • LEANN    │ │ • Phase     │ │ • Auto-detect│
│ • Regex Fallback│ • FAISS   │ │   Weighting │ │ • Fallback  │
│ • Python/JS/  │ │ • Domain   │ │ • PageRank  │ │ • Logging   │
│   TS/Rust     │ │   Mapping  │ │ • Domain    │ │             │
└───────────────┘ └────────────┘ └─────────────┘ └──────────────┘
                                              │
┌─────────────────────────────────────────────▼──────────────────┐
│                    Budget & Packing                              │
│                                                                  │
│   ┌──────────────────┐         ┌──────────────────┐            │
│   │ Budget Manager   │         │ Output Packers   │            │
│   │                  │         │                  │            │
│   │ • Greedy Knapsack│         │ • XMLPacker      │            │
│   │ • tiktoken Count │         │ • ZIPPacker      │            │
│   │ • 80/20 Split    │         │ • JSON/YAML/MD   │            │
│   └──────────────────┘         └──────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                     Storage Layer                                │
│                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Vector Index │  │ Graph Store  │  │ Domain Map   │         │
│   │              │  │              │  │              │         │
│   │ • LEANN idx  │  │ • graph.pkl  │  │ • domain_map │         │
│   │ • FAISS idx  │  │ • CozoDB opt │  │   .db (SQLite)│        │
│   │ • embeddings │  │ • pagerank   │  │ • keywords   │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. CLI Interface (`cli/`)

**Entry Points**:
- `wsctx` (short alias)
- `ws-ctx-engine` (full name)
- `ws-ctx-engine-init` (setup tool)

**Commands**:
```bash
wsctx doctor              # Check dependencies
wsctx index <repo>        # Build indexes
wsctx query <text>        # Search + rank + output
wsctx pack <repo>         # Full workflow
wsctx status              # Show index stats
wsctx vacuum              # Optimize SQLite DB
wsctx reindex-domain      # Rebuild domain map only
```

**Key Features**:
- Rich console output (colors, progress bars)
- Verbose logging with timing information
- Multiple output formats (--format xml|zip|json|yaml|md)
- Token budget control (--budget N)
- Agent phase awareness (--mode discovery|edit|test)
- Session management (--session-id, --no-dedup)

**Files**:
- `cli/cli.py` - Main command definitions
- `cli/cli_init.py` - Initialization logic
- `cli/templates/` - Pre-configured templates

---

### 2. Chunking Module (`chunker/`)

**Purpose**: Parse source code into semantically meaningful chunks with metadata.

**Architecture**:
```
CodeChunker (Base Class)
    ├── TreeSitterChunker (Primary)
    │   ├── PythonResolver
    │   ├── JavaScriptResolver
    │   ├── TypeScriptResolver
    │   └── RustResolver
    └── RegexChunker (Fallback)
        ├── PythonRegexChunker
        ├── JavaScriptRegexChunker
        └── MarkdownChunker
```

**Chunk Types**:
- **Functions**: Method definitions with signatures
- **Classes**: Class declarations with methods
- **Imports**: Import statements and dependencies
- **Constants**: Global variables and configuration

**Example Output**:
```python
CodeChunk(
    file_path="src/auth.py",
    content="def authenticate(user, password):\n    ...",
    chunk_type="function",
    symbols_defined=["authenticate"],
    imports=["hashlib", "bcrypt"],
    line_start=42,
    line_end=58,
    token_count=156
)
```

**Key Features**:
- Round-trip validation (chunks reconstruct original file)
- Symbol extraction for graph building
- Import tracking for dependency analysis
- Line number preservation for error reporting

**Files**:
- `chunker/chunker.py` - Base class and interfaces
- `chunker/tree_sitter_chunker.py` - AST-based parser
- `chunker/resolvers/` - Language-specific implementations
- `chunker/fallback_chunker.py` - Regex-based parsers

---

### 3. Retrieval Engine (`retrieval/`)

**Purpose**: Find relevant code chunks using hybrid search strategy.

**Search Modes**:
1. **Semantic Search**: Cosine similarity on embeddings
2. **BM25**: Keyword-based sparse retrieval
3. **Domain-Boosted**: Adaptive weighting based on query classification

**Hybrid Scoring Formula**:
```python
final_score = (
    semantic_weight × semantic_score +
    pagerank_weight × pagerank_score +
    domain_weight × domain_boost_score
)
```

**Query Classifier**:
```python
# Conceptual query → boost domain matches
query: "authentication logic" → domain_boost = 0.25

# Path-based query → boost path matches
query: "src/auth.py login" → domain_boost = 0.0
```

**Backend Hierarchy**:
```
Level 1: LEANN (primary, 97% storage savings)
  ↓ LEANN unavailable
Level 2: FAISS (fallback, battle-tested HNSW)
  ↓ FAISS unavailable
Level 3: TF-IDF (sparse retrieval, no embeddings)
```

**Files**:
- `retrieval/retrieval.py` - Hybrid engine core
- `retrieval/query_classifier.py` - Query type detection
- `retrieval/domain_map.py` - SQLite keyword mapping
- `retrieval/bm25_index.py` - BM25 implementation

---

### 4. Ranking Module (`ranking/`)

**Purpose**: Combine multiple signals into final importance score.

**Ranking Signals**:
1. **Semantic Similarity** (0.6 weight): Query-chunk cosine similarity
2. **PageRank Score** (0.4 weight): Dependency graph centrality
3. **Domain Boost** (0.25 multiplier): Keyword match amplification
4. **Changed File Boost** (optional): PR review prioritization

**Phase-Aware Weighting**:
```python
PHASE_WEIGHTS = {
    "discovery": {"semantic": 0.7, "pagerank": 0.3},  # Explore broadly
    "edit": {"semantic": 0.5, "pagerank": 0.5},       # Balanced view
    "test": {"semantic": 0.4, "pagerank": 0.6},       # Dependencies matter
}
```

**Session-Level Deduplication**:
```python
# Semantic similarity cache prevents redundant results
if chunk.embedding in session_cache:
    chunk.score *= 0.3  # Downweight duplicates
```

**Files**:
- `ranking/ranker.py` - Score merging logic
- `ranking/phase_ranker.py` - Agent phase adjustments
- `ranking/merging.py` - Result list consolidation

---

### 5. Budget Manager (`budget/`)

**Purpose**: Select optimal subset of chunks within token limit.

**Algorithm**: Greedy Knapsack with Importance Density

```python
def select_chunks(chunks, budget):
    # Sort by importance/token_ratio
    sorted_chunks = sorted(
        chunks,
        key=lambda c: c.importance_score / c.token_count,
        reverse=True
    )
    
    selected = []
    total_tokens = 0
    reserved = budget * 0.2  # 20% for metadata
    
    for chunk in sorted_chunks:
        if total_tokens + chunk.token_count <= budget * 0.8:
            selected.append(chunk)
            total_tokens += chunk.token_count
    
    return selected, reserved
```

**Token Counting**:
- **Backend**: tiktoken (OpenAI's tokenizer)
- **Accuracy**: ±2% vs actual LLM tokenization
- **Models Supported**: GPT-4, GPT-3.5-turbo, Claude, Llama

**Budget Allocation**:
- **80%**: File content (actual code)
- **20% Reserved**: Manifest, comments, formatting overhead

**Files**:
- `budget/budget.py` - Knapsack implementation
- `budget/token_counter.py` - tiktoken wrapper

---

### 6. Output Packers (`packer/`, `formatters/`)

**Purpose**: Format selected chunks for LLM consumption.

#### XML Packer (Repomix-style)
```xml
<file path="src/auth.py">
  <!-- Importance: 0.87 | Tokens: 156 -->
  def authenticate(user, password):
      ...
</file>
```

#### ZIP Packer (Multi-turn upload)
```
ws-ctx-engine.zip
├── files/
│   ├── src/
│   │   └── auth.py
│   └── tests/
│       └── test_auth.py
└── REVIEW_CONTEXT.md
    ├── Selected: 47 files
    ├── Total Tokens: 98,432
    ├── Budget: 100,000
    └── Reading Order: [sorted by importance]
```

#### Additional Formatters
- **JSON**: Structured data for programmatic access
- **YAML**: Human-readable configuration style
- **Markdown**: Documentation-friendly format

**Compression Strategy**:
```python
if relevance_score < 0.3:
    output = compress_to_signature(chunk)
    # Shows only function signatures, not bodies
else:
    output = render_full_chunk(chunk)
```

**Files**:
- `packer/packer.py` - Base packer interface
- `packer/xml_packer.py` - Repomix-style XML
- `packer/zip_packer.py` - Archive with manifest
- `formatters/` - JSON/YAML/MD formatters

---

### 7. Vector Index (`vector_index/`)

**Purpose**: Store and retrieve chunk embeddings efficiently.

#### LEANN Backend (Primary)
- **Storage**: 97% smaller than FAISS
- **Algorithm**: Graph-based approximate nearest neighbors
- **Recall@10**: 94% (vs 96% for FAISS)
- **Index Files**: `leann_index.index`, `leann_index.passages.jsonl`

#### FAISS Backend (Fallback)
- **Storage**: HNSW index (Hierarchical Navigable Small World)
- **Speed**: Sub-millisecond queries
- **Index Files**: `vector.idx`, `vector.idx.faiss`

#### Embedding Generation
```python
EmbeddingStrategy:
    ├── LocalEmbeddings (Primary)
    │   ├── sentence-transformers (all-MiniLM-L6-v2)
    │   └── ONNX Runtime (1.4-3× speedup)
    └── APIEmbeddings (Fallback)
        ├── OpenAI (text-embedding-ada-002)
        └── Azure OpenAI
```

**Memory Optimization**:
```python
if RAM < 8GB:
    batch_size = 16  # Reduce from 32
    device = "cpu"   # Avoid CUDA OOM
elif RAM < 4GB:
    strategy = "api"  # Use OpenAI API instead
```

**Files**:
- `vector_index/vector_index.py` - Base interface
- `vector_index/leann_index.py` - LEANN wrapper
- `vector_index/faiss_index.py` - FAISS wrapper
- `vector_index/embedding_generator.py` - Embedding creation
- `vector_index/model_registry.py` - Model download caching

---

### 8. Graph Engine (`graph/`)

**Purpose**: Analyze code structure and compute importance via PageRank.

**Current Implementation** (v0.2.0a0):
```python
DependencyGraph:
    Nodes: Files
    Edges: IMPORTS relationships
    Algorithm: PageRank (damping=0.85, max_iter=100)
```

**Planned Graph RAG** (Phase 4 - Incomplete):
```python
KnowledgeGraph (CozoDB):
    Nodes: files, functions, classes, methods, symbols
    Edges:
        - CONTAINS (file → function)
        - CALLS (function → function)
        - IMPORTS (file → file)
        - INHERITS (class → class)
        - IMPLEMENTS (class → interface)
```

**Graph Construction Pipeline**:
```python
files → AST parsing → symbol extraction → edge detection → graph building
```

**Edge Detection Example**:
```python
# src/auth.py imports hashlib
Edge(src="src/auth.py", relation="IMPORTS", dst="hashlib")

# authenticate() calls hash_password()
Edge(src="auth.py#authenticate", relation="CALLS", dst="auth.py#hash_password")
```

**Files**:
- `graph/graph.py` - Graph construction
- `graph/builder.py` - Node/edge extraction
- `graph/node_id.py` - Node ID normalization
- `graph/validation.py` - Graph integrity checks
- `graph/graph_tools.py` - MCP tools (find_callers, impact_analysis)

---

### 9. Backend Selector (`backend_selector/`)

**Purpose**: Automatically detect and select best available backends.

**Detection Algorithm**:
```python
def auto_select_backend():
    try:
        import igraph
        backend = "igraph"
    except ImportError:
        try:
            import networkx
            backend = "networkx"
        except ImportError:
            backend = "file_size_only"
    
    log.info(f"Using {backend} for graph analysis")
    return backend
```

**Fallback Hierarchy**:
```
Level 1: igraph + LEANN + sentence-transformers (optimal)
  ↓ igraph import fails
Level 2: networkx + LEANN + sentence-transformers
  ↓ LEANN import fails
Level 3: networkx + FAISS + sentence-transformers
  ↓ torch OOM (Out Of Memory)
Level 4: networkx + FAISS + OpenAI API
  ↓ OpenAI API unavailable
Level 5: networkx + TF-IDF (no embeddings)
  ↓ networkx too slow for >10k files
Level 6: File size ranking only (no graph)
```

**Logging Example**:
```
[INFO] BackendSelector: Detected igraph (C++ backend)
[INFO] BackendSelector: Detected LEANN vector index
[INFO] BackendSelector: Using Level 1 configuration (optimal)
[INFO] BackendSelector: Expected performance: <5min indexing for 10k files
```

**Files**:
- `backend_selector/backend_selector.py` - Detection logic
- `backend_selector/config.py` - Backend configuration

---

### 10. Rust Extension (`_rust/`)

**Purpose**: Accelerate hot-path operations with native code.

**Implemented Functions**:
```rust
#[pyfunction]
fn walk_files(root: &str, patterns: Vec<String>) -> PyResult<Vec<String>> {
    // 36× faster than os.walk()
    // Ignores .git/, node_modules/, __pycache__/
    // Returns sorted list of file paths
}
```

**Performance Comparison**:
| Operation | Python | Rust | Speedup |
|-----------|--------|------|---------|
| walk_files (10k files) | 2.1s | 0.058s | 36× |
| hash_content (1MB) | 0.12s | 0.008s | 15× |
| count_tokens (10k tokens) | 0.045s | 0.002s | 22× |

**Build Process**:
```bash
pip install maturin
cd _rust && maturin develop --release
```

**Auto-Fallback**:
```python
try:
    from ws_ctx_engine._rust import walk_files
except ImportError:
    walk_files = python_walk_files  # Pure Python fallback
```

**Files**:
- `_rust/Cargo.toml` - Rust dependencies
- `_rust/src/lib.rs` - PyO3 bindings
- `_rust/src/walker.rs` - File walking implementation

---

### 11. MCP Server (`mcp/`)

**Purpose**: Expose retrieval capabilities via Model Context Protocol.

**Exposed Tools**:
```python
@server.tool("wsctx_query")
def query(query_text: str, repo: str = None, budget: int = 100000):
    """Search indexed repository and return context pack"""

@server.tool("wsctx_find_symbol")
def find_symbol(symbol_name: str, repo: str = None):
    """Find all occurrences of a symbol across codebase"""

@server.tool("wsctx_list_repos")
def list_repos():
    """List all indexed repositories"""

@server.tool("wsctx_status")
def status(repo: str = None):
    """Show index statistics and backend info"""
```

**Resources**:
```python
@server.resource("wsctx://repos")
def get_repos():
    """Return list of indexed repos"""

@server.resource("wsctx://repo/{name}/status")
def get_repo_status(name: str):
    """Return index metadata for specific repo"""
```

**Integration Pattern**:
```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "wsctx": {
      "command": "wsctx",
      "args": ["mcp", "serve"]
    }
  }
}
```

**Files**:
- `mcp/server.py` - MCP server implementation
- `mcp/tools.py` - Tool definitions
- `mcp/resources.py` - Resource endpoints

---

## Data Models

### Core Data Structures

```python
@dataclass
class CodeChunk:
    """Represents a parsed code unit with metadata"""
    file_path: str
    content: str
    chunk_type: str  # "function", "class", "import", etc.
    symbols_defined: List[str]
    imports: List[str]
    line_start: int
    line_end: int
    token_count: int
    embedding: Optional[np.ndarray] = None
    pagerank_score: float = 0.0
    semantic_score: float = 0.0
    final_score: float = 0.0

@dataclass
class IndexMetadata:
    """Tracks index state for staleness detection"""
    repo_path: str
    indexed_at: datetime
    file_count: int
    total_tokens: int
    backends: Dict[str, str]
    git_commit: Optional[str] = None
    config_hash: Optional[str] = None

@dataclass
class RankedChunk:
    """CodeChunk with scoring and ranking metadata"""
    chunk: CodeChunk
    semantic_score: float
    pagerank_score: float
    domain_boost: float
    final_score: float
    rank: int
```

---

## Configuration System

### `.ws-ctx-engine.yaml`

```yaml
# Output settings
format: zip  # xml | zip | json | yaml | md
token_budget: 100000
output_path: ./output

# Scoring weights (must sum to 1.0)
semantic_weight: 0.6
pagerank_weight: 0.4
domain_weight: 0.25

# File filtering
include_tests: false
include_patterns:
  - "**/*.py"
  - "**/*.js"
  - "**/*.ts"
exclude_patterns:
  - "*.min.js"
  - "node_modules/**"
  - "__pycache__/**"

# Backend selection
backends:
  vector_index: auto  # auto | leann | faiss
  graph: auto         # auto | igraph | networkx
  embeddings: auto    # auto | local | api

# Embeddings configuration
embeddings:
  model: all-MiniLM-L6-v2
  device: cpu
  batch_size: 32
  api_provider: openai
  api_key_env: OPENAI_API_KEY

# Performance tuning
performance:
  max_workers: 4
  cache_embeddings: true
  incremental_index: true
```

---

## Testing Strategy

### Test Pyramid

```
        ┌─────────┐
        │   E2E   │  ← 10% (full workflow tests)
       ─┼─────────┼─
      │ Integration │ ← 30% (component interaction)
     ─┼─────────────┼─
    │    Unit Tests   │ ← 60% (individual functions)
   └─────────────────┘
```

### Test Categories

**Unit Tests** (`tests/unit/`):
- Test individual functions in isolation
- Mock external dependencies
- Fast execution (<3s total)

**Property-Based Tests** (`tests/property/`):
- Hypothesis-driven testing
- Generate random inputs
- Verify invariants hold

**Integration Tests** (`tests/integration/`):
- Test component interactions
- Use real (mocked) backends
- Validate end-to-end workflows

**Benchmarks** (`tests/test_performance_benchmarks.py`):
- pytest-benchmark suite
- Track performance regressions
- Compare backend speeds

### Coverage Targets
- **Unit Tests**: 85% line coverage
- **Integration Tests**: 70% workflow coverage
- **Critical Paths**: 100% coverage (budget, packing)

---

## Performance Characteristics

### Indexing Performance (10k files)

| Backend Combination | Time | Storage | RAM Usage |
|---------------------|------|---------|-----------|
| igraph + LEANN + local | 4m 30s | 120 MB | 2.1 GB |
| NetworkX + LEANN + local | 5m 15s | 120 MB | 1.8 GB |
| NetworkX + FAISS + local | 6m 45s | 2.1 GB | 2.3 GB |
| NetworkX + FAISS + API | 8m 20s | 2.1 GB | 0.8 GB |
| File-size-only | 0m 45s | 0 MB | 0.1 GB |

### Query Latency (p95, 10k files)

| Query Type | Latency | Components |
|------------|---------|------------|
| Semantic only | 0.8s | LEANN/FAISS query |
| PageRank only | 0.3s | Graph traversal |
| Hybrid (default) | 1.2s | Semantic + graph merge |
| With domain boost | 1.5s | + SQLite keyword lookup |
| Full pipeline | 2.1s | + budget selection + packing |

### Memory Footprint

| Component | Peak RAM | Notes |
|-----------|----------|-------|
| sentence-transformers | 1.2 GB | Batch encoding |
| LEANN index | 0.1 GB | Compressed graph |
| FAISS index | 1.8 GB | HNSW full index |
| igraph | 0.2 GB | C library efficient |
| NetworkX | 0.8 GB | Pure Python overhead |

---

## Error Handling

### Graceful Degradation Pattern

```python
try:
    index = build_leann_index(embeddings)
except (ImportError, MemoryError) as e:
    log.warning(f"LEANN failed: {e}, falling back to FAISS")
    try:
        index = build_faiss_index(embeddings)
    except (ImportError, MemoryError) as e2:
        log.error(f"FAISS also failed: {e2}, using TF-IDF only")
        index = None  # Fall back to sparse retrieval
```

### User-Facing Errors

```python
# Bad: Technical jargon
"ImportError: No module named 'igraph'"

# Good: Actionable guidance
"python-igraph not found. Install with:
  pip install ws-ctx-engine[all]
Or configure fallback in .ws-ctx-engine.yaml:
  backends:
    graph: networkx"
```

---

## Security Considerations

### Secret Scanning

```python
# Before packing, scan for secrets
from ws_ctx_engine.secret_scanner import scan_for_secrets

secrets = scan_for_secrets(selected_chunks)
if secrets:
    log.warning(f"Found {len(secrets)} potential secrets")
    if config.redact_secrets:
        chunks = redact_secrets(chunks, secrets)
```

### Path Traversal Prevention

```python
# Ensure files are within repo root
def is_safe_path(repo_root: Path, file_path: Path) -> bool:
    try:
        file_path.relative_to(repo_root)
        return True
    except ValueError:
        return False  # Attempted path traversal
```

---

## Future Roadmap (Incomplete)

### Phase 4: Graph RAG (Research Complete, Implementation Partial)
- ✅ Design CozoDB schema
- ✅ Implement `chunks_to_graph()` bridge
- ✅ Define Node/Edge dataclasses
- ⚠️ **Incomplete**: Full graph construction
- ⚠️ **Incomplete**: Call chain tracing
- ⚠️ **Incomplete**: Impact analysis tools

### Phase 5: Agent Experience (Planned, Not Started)
- ❌ Auto-install agent skills
- ❌ Claude Code PreToolUse hooks
- ❌ PostToolUse auto-reindex
- ❌ One-command setup (`wsctx init`)

### Phase 6: Web UI (Planned, Not Started)
- ❌ Browser-based graph explorer
- ❌ Interactive search interface
- ❌ Real-time indexing dashboard

---

## Lessons Learned

### What Worked Well
1. **Modular Architecture**: Easy to test, debug, and extend
2. **Fallback Strategy**: Zero production failures from missing deps
3. **Type Safety**: Strict mypy caught many bugs early
4. **Documentation**: Comprehensive docs reduced support burden
5. **Rust Extension**: Significant speedup for hot paths

### What Didn't Work
1. **Late Graph RAG**: Should have started earlier
2. **No Auto-Install**: Friction killed conversion
3. **Poor Positioning**: "Context packager" vs "AI nervous system"
4. **No Community**: Built alone, lost to network effects
5. **Perfectionism**: Spent 12 months building "perfect" product

### Advice for Successors
1. **Ship Fast**: MVP in 3 months, iterate publicly
2. **Build Community**: Discord before v1.0 launch
3. **Craft Narrative**: Emotional story > technical specs
4. **Copy Winners**: GitNexus auto-install pattern worked
5. **Focus on Enterprise**: They value reliability over features

---

## References

### Internal Documentation
- `PROJECT_POSTMORTEM.md` - Lessons learned and failure analysis
- `COMPETITOR_ANALYSIS.md` - GitNexus comparison
- `docs/development/plans/` - Implementation plans
- `docs/reports/GRAPH_RAG_ROADMAP.md` - Graph RAG research

### External Resources
- [LEANN Paper](https://github.com/yichuan-w/LEANN)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [FAISS Library](https://faiss.ai/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [CozoDB Documentation](https://docs.cozodb.org/)

---

**End of Architecture Summary**

*This document represents the final state of ws-ctx-engine as of March 29, 2026. The codebase remains available under GPL-3.0 license for future development.*
