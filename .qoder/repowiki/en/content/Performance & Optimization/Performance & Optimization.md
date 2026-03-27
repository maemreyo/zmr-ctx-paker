# Performance & Optimization

<cite>
**Referenced Files in This Document**
- [performance.py](file://src/ws_ctx_engine/monitoring/performance.py)
- [indexer.py](file://src/ws_ctx_engine/workflow/indexer.py)
- [query.py](file://src/ws_ctx_engine/workflow/query.py)
- [backend_selector.py](file://src/ws_ctx_engine/backend_selector/backend_selector.py)
- [vector_index.py](file://src/ws_ctx_engine/vector_index/vector_index.py)
- [leann_index.py](file://src/ws_ctx_engine/vector_index/leann_index.py)
- [embedding_cache.py](file://src/ws_ctx_engine/vector_index/embedding_cache.py)
- [config.py](file://src/ws_ctx_engine/config/config.py)
- [base.py](file://src/ws_ctx_engine/chunker/base.py)
- [Cargo.toml](file://_rust/Cargo.toml)
- [lib.rs](file://_rust/src/lib.rs)
- [walker.rs](file://_rust/src/walker.rs)
- [performance.md](file://docs/guides/performance.md)
- [test_performance_benchmarks.py](file://tests/test_performance_benchmarks.py)
- [toon_vs_alternatives.py](file://benchmarks/toon_vs_alternatives.py)
</cite>

## Update Summary
**Changes Made**
- Updated MCP-specific performance documentation references to point to the consolidated MCP Performance Optimization Guide v3
- Removed detailed MCP-specific optimization sections that have been moved to the dedicated guide
- Focused the general performance guide on broader optimization topics applicable to all users
- Maintained all core performance monitoring, benchmarking, and optimization content
- Preserved Rust extension documentation and performance targets

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document provides comprehensive performance and optimization guidance for ws-ctx-engine. It covers the performance monitoring system, benchmarking methodologies, the Rust extension delivering 8–20x speedup for hot-path operations, memory optimization strategies, caching mechanisms for embeddings and indices, backend selection strategies, CPU/GPU utilization, parallel processing, tuning parameters, resource allocation guidelines, scalability considerations, benchmark results, and troubleshooting.

**Important**: MCP-specific performance optimizations have been consolidated into the comprehensive MCP Performance Optimization Guide v3. This general performance guide now focuses on broader optimization topics while MCP-specific optimizations are fully documented in the dedicated guide.

## Project Structure
The performance-critical parts of the system are organized around:
- Monitoring and metrics collection
- Indexing and query workflows
- Backend selection and vector index backends
- Rust hot-path acceleration
- Configuration-driven performance controls

```mermaid
graph TB
subgraph "Monitoring"
PM["PerformanceMetrics<br/>PerformanceTracker"]
end
subgraph "Workflows"
IDX["index_repository()"]
QRY["query_and_pack()"]
end
subgraph "Backends"
BS["BackendSelector"]
VI["VectorIndex (LEANN/FAISS)"]
LEANN["NativeLEANNIndex"]
end
subgraph "Rust Hot-Paths"
RT["Rust Extension (_rust)"]
WF["walk_files()"]
end
subgraph "Config"
CFG["Config"]
end
PM --> IDX
PM --> QRY
IDX --> BS
QRY --> BS
BS --> VI
VI --> LEANN
IDX --> RT
RT --> WF
CFG --> IDX
CFG --> QRY
```

**Diagram sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- [indexer.py:72-493](file://src/ws_ctx_engine/workflow/indexer.py#L72-L493)
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)
- [vector_index.py:21-800](file://src/ws_ctx_engine/vector_index/vector_index.py#L21-L800)
- [leann_index.py:20-296](file://src/ws_ctx_engine/vector_index/leann_index.py#L20-L296)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)
- [Cargo.toml:1-25](file://_rust/Cargo.toml#L1-L25)

**Section sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- [indexer.py:72-493](file://src/ws_ctx_engine/workflow/indexer.py#L72-L493)
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)
- [vector_index.py:21-800](file://src/ws_ctx_engine/vector_index/vector_index.py#L21-L800)
- [leann_index.py:20-296](file://src/ws_ctx_engine/vector_index/leann_index.py#L20-L296)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)
- [Cargo.toml:1-25](file://_rust/Cargo.toml#L1-L25)

## Core Components
- Performance monitoring: Tracks indexing/query durations, files processed/index size, tokens selected, and peak memory usage.
- Workflows: Index and query phases orchestrate parsing, vector indexing, graph building, retrieval, budget selection, packing, and metadata persistence.
- Backend selection: Centralized fallback chain across vector index, graph, and embeddings backends.
- Rust hot-path: Accelerates file walking; Python fallbacks exist for hashing and token counting.
- Caching: Embedding cache avoids re-embedding unchanged content; incremental rebuilds leverage caches.
- Configuration: Tunable performance flags (e.g., embedding cache, incremental indexing) and backend preferences.

**Section sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- [indexer.py:72-493](file://src/ws_ctx_engine/workflow/indexer.py#L72-L493)
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)
- [config.py:94-101](file://src/ws_ctx_engine/config/config.py#L94-L101)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)

## Architecture Overview
The system measures performance end-to-end and applies optimizations at multiple layers:
- Hot-path acceleration via Rust for file walking.
- Incremental indexing with embedding cache and staleness detection.
- Backend selection with graceful fallbacks.
- Memory tracking and budget-aware selection.

```mermaid
sequenceDiagram
participant CLI as "CLI/User"
participant IDX as "index_repository()"
participant TRK as "PerformanceTracker"
participant SEL as "BackendSelector"
participant VI as "VectorIndex"
participant EC as "EmbeddingCache"
CLI->>IDX : "index_repository(repo)"
IDX->>TRK : "start_indexing()"
IDX->>SEL : "select_vector_index()"
SEL-->>IDX : "VectorIndex impl"
IDX->>EC : "load() when enabled"
IDX->>VI : "build(chunks, embedding_cache)"
VI-->>EC : "lookup/store via cache"
VI-->>IDX : "save(vector.idx)"
IDX->>TRK : "set_index_size(), end_indexing()"
TRK-->>CLI : "format_metrics('indexing')"
```

**Diagram sources**
- [indexer.py:72-493](file://src/ws_ctx_engine/workflow/indexer.py#L72-L493)
- [backend_selector.py:36-81](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L36-L81)
- [vector_index.py:536-644](file://src/ws_ctx_engine/vector_index/vector_index.py#L536-L644)
- [embedding_cache.py:55-84](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L55-L84)
- [performance.py:95-114](file://src/ws_ctx_engine/monitoring/performance.py#L95-L114)

## Detailed Component Analysis

### Performance Monitoring and Metrics
- Tracks indexing and query durations, files processed, index size, files selected, total tokens, and peak memory usage.
- Supports phase-level timing and human-readable formatting.
- Memory tracking uses psutil when available; gracefully degrades when unavailable.

```mermaid
classDiagram
class PerformanceMetrics {
+float indexing_time
+int files_processed
+int index_size
+float query_time
+int files_selected
+int total_tokens
+int memory_usage
+dict[str, float] phase_timings
+to_dict() dict
}
class PerformanceTracker {
-PerformanceMetrics metrics
-dict[str, float] _phase_start_times
-float _indexing_start
-float _query_start
+start_indexing() void
+end_indexing() void
+start_query() void
+end_query() void
+start_phase(phase_name) void
+end_phase(phase_name) void
+set_files_processed(count) void
+set_index_size(index_dir) void
+set_files_selected(count) void
+set_total_tokens(tokens) void
+set_memory_usage(bytes) void
+track_memory() void
+get_metrics() PerformanceMetrics
+format_metrics(phase) str
}
PerformanceTracker --> PerformanceMetrics : "aggregates"
```

**Diagram sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)

**Section sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)

### Rust Hot-Path Acceleration
- The Rust extension exposes a single hot-path function: file walking with parallel traversal and .gitignore respect.
- The extension is optional; Python fallbacks are used when unavailable.
- Benchmarks indicate 8–20x speedup for file walking and 8–12x for related operations.

```mermaid
flowchart TD
Start(["Call walk_files(root, respect_hidden)"]) --> CheckExt{"Rust available?"}
CheckExt --> |Yes| RustWalk["Parallel walker (ignore crate)<br/>respects .gitignore"]
CheckExt --> |No| PyWalk["Python fallback (os.walk)"]
RustWalk --> Sort["Sort paths deterministically"]
PyWalk --> Sort
Sort --> Return(["Return list[str] paths"])
```

**Diagram sources**
- [base.py:14-25](file://src/ws_ctx_engine/chunker/base.py#L14-L25)
- [lib.rs:16-21](file://_rust/src/lib.rs#L16-L21)
- [walker.rs:16-52](file://_rust/src/walker.rs#L16-L52)
- [Cargo.toml:10-25](file://_rust/Cargo.toml#L10-L25)

**Section sources**
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)
- [lib.rs:1-22](file://_rust/src/lib.rs#L1-L22)
- [walker.rs:1-53](file://_rust/src/walker.rs#L1-L53)
- [Cargo.toml:1-25](file://_rust/Cargo.toml#L1-L25)
- [performance.md:1-81](file://docs/guides/performance.md#L1-L81)

### Indexing Workflow and Incremental Optimization
- Detects incremental changes by comparing stored file hashes to current disk state.
- Uses embedding cache to avoid re-embedding unchanged files.
- Saves metadata for staleness detection and supports domain-only rebuilds.

```mermaid
flowchart TD
A["Start index_repository()"] --> B["Parse codebase (AST chunker)"]
B --> C{"Incremental mode active?"}
C --> |Yes| D["Compare stored hashes to disk"]
D --> E["Identify changed/deleted paths"]
C --> |No| F["Full rebuild"]
E --> G["Filter chunks for changed paths"]
G --> H["Build vector index (with cache)"]
F --> H
H --> I["Build graph (with fallback)"]
I --> J["Save vector.idx, graph.pkl, metadata.json"]
J --> K["Compute index size, end indexing"]
K --> L["Return PerformanceTracker"]
```

**Diagram sources**
- [indexer.py:27-371](file://src/ws_ctx_engine/workflow/indexer.py#L27-L371)
- [embedding_cache.py:55-84](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L55-L84)

**Section sources**
- [indexer.py:27-371](file://src/ws_ctx_engine/workflow/indexer.py#L27-L371)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

### Query Workflow and Budget-Aware Selection
- Loads indexes with auto-detection and staleness handling.
- Hybrid retrieval combines semantic and graph signals.
- Budget manager selects files within token budget and tracks total tokens.

```mermaid
sequenceDiagram
participant Q as "query_and_pack()"
participant L as "load_indexes()"
participant R as "RetrievalEngine"
participant BM as "BudgetManager"
participant P as "Packer/Formatter"
Q->>L : "load_indexes(repo)"
L-->>Q : "VectorIndex, Graph, Metadata"
Q->>R : "retrieve(query, top_k)"
R-->>Q : "ranked_files"
Q->>BM : "select_files(ranked, repo_path)"
BM-->>Q : "selected_files, total_tokens"
Q->>P : "pack(selected_files, metadata)"
P-->>Q : "output_path"
Q-->>Q : "track files_selected, total_tokens"
```

**Diagram sources**
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [indexer.py:404-493](file://src/ws_ctx_engine/workflow/indexer.py#L404-L493)

**Section sources**
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [indexer.py:404-493](file://src/ws_ctx_engine/workflow/indexer.py#L404-L493)

### Backend Selection Strategies
- Centralized selector chooses backends with graceful fallback across vector index, graph, and embeddings.
- Fallback levels define optimal to minimal configurations with storage and performance trade-offs.

```mermaid
classDiagram
class BackendSelector {
+select_vector_index(model_name, device, batch_size, index_path) VectorIndex
+select_graph(boost_factor) RepoMapGraph
+select_embeddings_backend() str
+get_fallback_level() int
+log_current_configuration() void
}
```

**Diagram sources**
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)

**Section sources**
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)

### Vector Index Backends and Storage Optimization
- LEANN-based backends provide 97% storage savings by selectively recomputing embeddings.
- FAISS-based backend offers exact brute-force search with ID mapping for incremental updates.
- EmbeddingGenerator handles local and API fallbacks with memory-aware checks.

```mermaid
classDiagram
class VectorIndex {
<<abstract>>
+build(chunks) void
+search(query, top_k) list
+save(path) void
+load(path) VectorIndex
+get_file_symbols() dict
}
class LEANNIndex {
+build(chunks) void
+search(query, top_k) list
+save(path) void
+load(path) LEANNIndex
+get_file_symbols() dict
}
class FAISSIndex {
+build(chunks, embedding_cache) void
+search(query, top_k) list
+save(path) void
+load(path) FAISSIndex
}
class EmbeddingGenerator {
+encode(texts) ndarray
-_init_local_model() bool
-_init_api_client() bool
}
VectorIndex <|-- LEANNIndex
VectorIndex <|-- FAISSIndex
LEANNIndex --> EmbeddingGenerator : "uses"
FAISSIndex --> EmbeddingGenerator : "uses"
```

**Diagram sources**
- [vector_index.py:21-800](file://src/ws_ctx_engine/vector_index/vector_index.py#L21-L800)

**Section sources**
- [vector_index.py:21-800](file://src/ws_ctx_engine/vector_index/vector_index.py#L21-L800)
- [leann_index.py:20-296](file://src/ws_ctx_engine/vector_index/leann_index.py#L20-L296)

### Embedding Cache and Incremental Indexing Benefits
- Disk-backed cache persists content-hash → embedding vector mappings.
- On incremental rebuilds, unchanged files reuse cached vectors; new/changed files are embedded and appended.
- Reduces embedding cost and speeds up rebuilds.

```mermaid
flowchart TD
A["Start incremental build"] --> B["Load EmbeddingCache"]
B --> C{"For each file chunk"}
C --> D{"Content hash cached?"}
D --> |Yes| E["Reuse cached vector"]
D --> |No| F["Encode via EmbeddingGenerator"]
F --> G["Store in cache"]
E --> H["Append to index"]
G --> H
H --> I["Persist cache and index"]
```

**Diagram sources**
- [embedding_cache.py:55-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L55-L127)
- [vector_index.py:536-644](file://src/ws_ctx_engine/vector_index/vector_index.py#L536-L644)

**Section sources**
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)
- [vector_index.py:536-644](file://src/ws_ctx_engine/vector_index/vector_index.py#L536-L644)

### Configuration and Tuning Parameters
- Performance flags: cache_embeddings, incremental_index, max_workers (reserved).
- Embeddings: model, device (cpu/cuda), batch_size, API provider/key.
- Backend selection: vector_index, graph, embeddings with auto/forced backends.

**Section sources**
- [config.py:94-101](file://src/ws_ctx_engine/config/config.py#L94-L101)
- [config.py:83-92](file://src/ws_ctx_engine/config/config.py#L83-L92)
- [config.py:74-81](file://src/ws_ctx_engine/config/config.py#L74-L81)

## Dependency Analysis
- The indexing workflow depends on the backend selector, vector index, and embedding cache.
- The query workflow depends on index loading, retrieval engine, budget manager, and packer/formatter.
- Rust hot-path is optional and integrates via Python fallback chain.

```mermaid
graph LR
IDX["indexer.py"] --> BS["backend_selector.py"]
IDX --> VI["vector_index.py"]
VI --> EC["embedding_cache.py"]
QRY["query.py"] --> IDX
QRY --> RET["retrieval (referenced)"]
QRY --> BM["budget (referenced)"]
BASE["chunker/base.py"] --> RT["Rust (_rust)"]
```

**Diagram sources**
- [indexer.py:14-22](file://src/ws_ctx_engine/workflow/indexer.py#L14-L22)
- [query.py:13-22](file://src/ws_ctx_engine/workflow/query.py#L13-L22)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)

**Section sources**
- [indexer.py:14-22](file://src/ws_ctx_engine/workflow/indexer.py#L14-L22)
- [query.py:13-22](file://src/ws_ctx_engine/workflow/query.py#L13-L22)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)

## Performance Considerations
- Hot-path acceleration: Prefer installing the Rust extension for significant gains in file walking and related operations.
- Incremental indexing: Enable cache_embeddings and incremental_index to reduce rebuild costs.
- Backend selection: Use primary backends (LEANN + igraph) for optimal performance; fallback to FAISS + NetworkX when necessary.
- Memory usage: Monitor peak memory via PerformanceTracker; local embeddings may trigger API fallback under low-memory conditions.
- Parallelization: The Rust walker uses parallel traversal; consider CPU/GPU device settings for embeddings.
- Output formats: Token counts vary by format; see format benchmarks for guidance.

## Troubleshooting Guide
- Missing Rust extension: The system falls back to Python implementations automatically; verify installation and availability.
- Low memory during embeddings: Local model initialization may be skipped or API fallback triggered; adjust device/batch size or use API embeddings.
- Stale indexes: The loader detects staleness and can auto-rebuild; disable auto-rebuild if needed.
- Slow indexing: Check backend selection, embedding cache usage, and incremental mode; verify file filters and include/exclude patterns.
- Query timeouts: Reduce top_k, adjust token budget, or switch to primary backends.

**Section sources**
- [base.py:14-25](file://src/ws_ctx_engine/chunker/base.py#L14-L25)
- [vector_index.py:128-278](file://src/ws_ctx_engine/vector_index/vector_index.py#L128-L278)
- [indexer.py:426-493](file://src/ws_ctx_engine/workflow/indexer.py#L426-L493)
- [query.py:294-323](file://src/ws_ctx_engine/workflow/query.py#L294-L323)

## Conclusion
ws-ctx-engine delivers strong performance through a combination of Rust hot-path acceleration, incremental indexing with embedding caching, backend selection with graceful fallbacks, and robust monitoring. By tuning configuration flags, selecting appropriate backends, and leveraging caching and incremental rebuilds, teams can achieve efficient indexing and querying at scale.

**MCP-Specific Optimizations**: For MCP-specific performance optimizations, refer to the comprehensive MCP Performance Optimization Guide v3, which consolidates all MCP-related performance enhancements including model loading optimization, hybrid search architecture, and advanced caching strategies.

## Appendices

### Benchmarking Methodologies and Results
- Performance targets and speedups for file walking and related operations are documented, including optional Rust extension benchmarks.
- Unit tests enforce performance targets for indexing and querying under different backend configurations.
- Format token benchmarks compare output sizes across formats using tiktoken encoding.

**Section sources**
- [performance.md:1-81](file://docs/guides/performance.md#L1-L81)
- [test_performance_benchmarks.py:141-440](file://tests/test_performance_benchmarks.py#L141-L440)
- [toon_vs_alternatives.py:1-260](file://benchmarks/toon_vs_alternatives.py#L1-L260)

### Optimization Case Studies
- File walking acceleration: Installing the Rust extension reduces file walk time from several hundred milliseconds to under 200 ms for large repositories.
- Incremental rebuilds: Embedding cache avoids re-embedding unchanged files, dramatically reducing rebuild times on large codebases.
- Backend selection: Primary backends (LEANN + igraph) meet strict latency targets; fallback backends maintain usability within acceptable bounds.

**Section sources**
- [performance.md:1-81](file://docs/guides/performance.md#L1-L81)
- [indexer.py:200-240](file://src/ws_ctx_engine/workflow/indexer.py#L200-L240)
- [test_performance_benchmarks.py:172-249](file://tests/test_performance_benchmarks.py#L172-L249)