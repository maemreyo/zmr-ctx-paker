# Performance Monitoring

<cite>
**Referenced Files in This Document**
- [performance.py](file://src/ws_ctx_engine/monitoring/performance.py)
- [indexer.py](file://src/ws_ctx_engine/workflow/indexer.py)
- [query.py](file://src/ws_ctx_engine/workflow/query.py)
- [base.py](file://src/ws_ctx_engine/chunker/base.py)
- [timing.py](file://src/ws_ctx_engine/perf/timing.py)
- [__init__.py](file://src/ws_ctx_engine/perf/__init__.py)
- [_rust lib.rs](file://_rust/src/lib.rs)
- [_rust walker.rs](file://_rust/src/walker.rs)
- [_rust Cargo.toml](file://_rust/Cargo.toml)
- [performance.md](file://docs/guides/performance.md)
- [test_performance_benchmarks.py](file://tests/test_performance_benchmarks.py)
- [test_performance_properties.py](file://tests/property/test_performance_properties.py)
- [test_perf_timing.py](file://tests/unit/test_perf_timing.py)
- [test_phase5_integration.py](file://tests/integration/test_phase5_integration.py)
- [graph.py](file://src/ws_ctx_engine/graph/graph.py)
- [vector_index.py](file://src/ws_ctx_engine/vector_index/vector_index.py)
- [leann_index.py](file://src/ws_ctx_engine/vector_index/leann_index.py)
- [retrieval.py](file://src/ws_ctx_engine/retrieval/retrieval.py)
</cite>

## Update Summary
**Changes Made**
- Added comprehensive documentation for the new Timing class and performance instrumentation system
- Updated Core Components section to include TimingContext and @timed decorator
- Enhanced Detailed Component Analysis with new timing instrumentation examples
- Added new section covering the lightweight timing instrumentation system
- Updated Architecture Overview to reflect enhanced performance monitoring
- Added practical examples of timing instrumentation usage across different components

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Lightweight Timing Instrumentation System](#lightweight-timing-instrumentation-system)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)
11. [Appendices](#appendices)

## Introduction
This document explains the performance monitoring system in ws-ctx-engine, detailing how operation durations, memory usage, and resource utilization are measured across indexing and query phases. The system now includes enhanced performance monitoring with a new Timing class providing detailed latency breakdowns across different components. It covers comprehensive instrumentation for encoding times, search operations, page-rank computations, and merge operations. The document details the benchmarking methodologies used to evaluate system efficiency, including the automated benchmark suite that compares Python versus Rust implementations. You will learn how to interpret performance metrics, identify bottlenecks, and track system behavior under different workloads, along with practical examples and best practices for large-scale codebase processing.

## Project Structure
The performance monitoring system is centered around a lightweight metrics collector and tracker, integrated into the core workflows for indexing and querying, enhanced with comprehensive timing instrumentation. Supporting performance enhancements are provided by an optional Rust extension that accelerates hot-path operations.

```mermaid
graph TB
subgraph "Enhanced Monitoring"
PM["PerformanceMetrics<br/>dataclass"]
PT["PerformanceTracker<br/>start/end/start_phase/end_phase"]
TIMING["TimingContext<br/>@timed decorator"]
end
subgraph "Workflows"
IDX["index_repository()<br/>indexer.py"]
QRY["query_and_pack()<br/>query.py"]
SEARCH["search_codebase()<br/>query.py"]
end
subgraph "Rust Extension"
RS_LIB["_rust/lib.rs<br/>PyO3 module"]
RS_WALK["_rust/walker.rs<br/>parallel file walker"]
RS_CARGO["_rust/Cargo.toml<br/>build profile"]
end
subgraph "Instrumented Components"
ENC["embedding_encode()<br/>vector_index.py"]
SRCH["leann_search()<br/>leann_index.py"]
PR["pagerank()<br/>graph.py"]
RET["retrieve()<br/>retrieval.py"]
end
PM --> PT
PT --> IDX
PT --> QRY
TIMING --> ENC
TIMING --> SRCH
TIMING --> PR
TIMING --> RET
SEARCH --> TIMING
RS_LIB --> CHUNK_BASE
RS_WALK --> CHUNK_BASE
RS_CARGO --> RS_LIB
```

**Diagram sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [timing.py:25-80](file://src/ws_ctx_engine/perf/timing.py#L25-L80)
- [vector_index.py:197-250](file://src/ws_ctx_engine/vector_index/vector_index.py#L197-L250)
- [leann_index.py:172-216](file://src/ws_ctx_engine/vector_index/leann_index.py#L172-L216)
- [graph.py:191-242](file://src/ws_ctx_engine/graph/graph.py#L191-L242)
- [retrieval.py:265-402](file://src/ws_ctx_engine/retrieval/retrieval.py#L265-L402)

**Section sources**
- [performance.py:1-263](file://src/ws_ctx_engine/monitoring/performance.py#L1-L263)
- [indexer.py:1-493](file://src/ws_ctx_engine/workflow/indexer.py#L1-L493)
- [query.py:1-671](file://src/ws_ctx_engine/workflow/query.py#L1-L671)
- [timing.py:1-80](file://src/ws_ctx_engine/perf/timing.py#L1-L80)
- [base.py:1-176](file://src/ws_ctx_engine/chunker/base.py#L1-L176)
- [_rust lib.rs:1-22](file://_rust/src/lib.rs#L1-L22)
- [_rust walker.rs:1-53](file://_rust/src/walker.rs#L1-L53)
- [_rust Cargo.toml:1-25](file://_rust/Cargo.toml#L1-L25)

## Core Components
- PerformanceMetrics: Stores indexing/query metrics, memory usage, and per-phase timings.
- PerformanceTracker: Tracks elapsed time for phases, aggregates metrics, and optionally tracks peak memory usage.
- **TimingContext**: Context manager that logs wall-clock elapsed time for code blocks with structured log output.
- **@timed decorator**: Function decorator that automatically times wrapped functions and emits performance logs.

Key capabilities:
- Timing: Whole-phase and per-operation timing for indexing and query.
- Counts: Files processed, files selected, and total tokens.
- Storage: Index size on disk.
- Memory: Optional peak memory tracking via psutil.
- **Lightweight instrumentation**: Structured log-based timing without heavy profiler overhead.
- **Comprehensive coverage**: Detailed latency breakdowns for encoding, search, page-rank, and merge operations.
- Formatting: Human-readable summaries and dictionary export for serialization.

**Section sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- [timing.py:25-80](file://src/ws_ctx_engine/perf/timing.py#L25-L80)

## Architecture Overview
The performance monitoring architecture integrates tightly with the indexing and query workflows, enhanced with comprehensive timing instrumentation. Workflows initialize a tracker, mark phase boundaries, and populate metrics. The new Timing class provides lightweight, structured logging for critical operations. The Rust extension accelerates hot-path operations, reducing overall latency and memory pressure.

```mermaid
sequenceDiagram
participant User as "Caller"
participant Tracker as "PerformanceTracker"
participant Workflow as "index_repository()"
participant Timing as "@timed Decorators"
participant Chunker as "AST Chunker"
participant VIdx as "Vector Index"
participant Graph as "RepoMap Graph"
User->>Workflow : "index_repository(repo)"
Workflow->>Tracker : "start_indexing()"
Workflow->>Timing : "start_phase('parsing') with @timed"
Workflow->>Chunker : "parse_with_fallback(...)"
Chunker-->>Workflow : "chunks"
Workflow->>Timing : "end_phase('parsing') with @timed"
Workflow->>Tracker : "track_memory()"
Workflow->>Timing : "start_phase('vector_indexing') with @timed"
Workflow->>VIdx : "build(...)"
VIdx-->>Workflow : "index saved"
Workflow->>Timing : "end_phase('vector_indexing') with @timed"
Workflow->>Tracker : "track_memory()"
Workflow->>Timing : "start_phase('graph_building') with @timed"
Workflow->>Graph : "build(...)"
Graph-->>Workflow : "graph saved"
Workflow->>Timing : "end_phase('graph_building') with @timed"
Workflow->>Tracker : "track_memory()"
Workflow->>Tracker : "set_index_size(...), end_indexing()"
Workflow-->>User : "tracker with metrics"
```

**Diagram sources**
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [performance.py:72-214](file://src/ws_ctx_engine/monitoring/performance.py#L72-L214)
- [timing.py:25-80](file://src/ws_ctx_engine/perf/timing.py#L25-L80)

**Section sources**
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [performance.py:72-214](file://src/ws_ctx_engine/monitoring/performance.py#L72-L214)
- [timing.py:25-80](file://src/ws_ctx_engine/perf/timing.py#L25-L80)

## Detailed Component Analysis

### PerformanceMetrics and PerformanceTracker
- PerformanceMetrics: Captures indexing_time, files_processed, index_size; query_time, files_selected, total_tokens; memory_usage; and phase_timings.
- PerformanceTracker: Manages lifecycle of metrics, supports start/end for whole phases and named sub-phases, updates index size, sets token and selection counts, and optionally tracks peak memory.

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
+dict[str,float] phase_timings
+to_dict() dict
}
class PerformanceTracker {
-PerformanceMetrics metrics
-dict[str,float] _phase_start_times
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

### Indexing Workflow Integration
- Initializes PerformanceTracker and starts the indexing phase.
- Starts and ends phases for parsing, vector indexing, graph building, metadata saving, and domain map building.
- Updates metrics for files processed, index size, and tracks memory after major steps.
- Ends indexing and logs formatted metrics.

```mermaid
flowchart TD
Start(["index_repository"]) --> Init["Create tracker<br/>start_indexing()"]
Init --> Parse["start_phase('parsing')<br/>parse_with_fallback"]
Parse --> AfterParse["end_phase('parsing')<br/>track_memory()"]
AfterParse --> Vector["start_phase('vector_indexing')<br/>build vector index"]
Vector --> AfterVector["end_phase('vector_indexing')<br/>track_memory()"]
AfterVector --> Graph["start_phase('graph_building')<br/>build graph"]
Graph --> AfterGraph["end_phase('graph_building')<br/>track_memory()"]
AfterGraph --> Metadata["start_phase('metadata_saving')<br/>save metadata"]
Metadata --> AfterMetadata["end_phase('metadata_saving')"]
AfterMetadata --> Domain["start_phase('domain_map_building')<br/>build domain map"]
Domain --> AfterDomain["end_phase('domain_map_building')"]
AfterDomain --> Finalize["set_index_size()<br/>end_indexing()<br/>format_metrics('indexing')"]
Finalize --> End(["Return tracker"])
```

**Diagram sources**
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [performance.py:72-214](file://src/ws_ctx_engine/monitoring/performance.py#L72-L214)

**Section sources**
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [performance.py:72-214](file://src/ws_ctx_engine/monitoring/performance.py#L72-L214)

### Query Workflow Integration
- Initializes PerformanceTracker and starts the query phase.
- Loads indexes, retrieves candidates, selects files within budget, and packs output.
- Records per-phase timings and tracks memory after major steps.
- Sets files_selected and total_tokens, ends query, and logs formatted metrics.

```mermaid
sequenceDiagram
participant Caller as "Caller"
participant Tracker as "PerformanceTracker"
participant Query as "query_and_pack()"
participant Loader as "load_indexes()"
participant Retriever as "RetrievalEngine"
participant Budget as "BudgetManager"
participant Packer as "Packer"
Caller->>Query : "query_and_pack(repo, query)"
Query->>Tracker : "start_query()"
Query->>Tracker : "start_phase('index_loading')"
Query->>Loader : "load_indexes()"
Loader-->>Query : "vector_index, graph, metadata"
Query->>Tracker : "end_phase('index_loading'), track_memory()"
Query->>Tracker : "start_phase('retrieval')"
Query->>Retriever : "retrieve(...)"
Retriever-->>Query : "ranked_files"
Query->>Tracker : "end_phase('retrieval'), track_memory()"
Query->>Tracker : "start_phase('budget_selection')"
Query->>Budget : "select_files(...)"
Budget-->>Query : "selected_files, total_tokens"
Query->>Tracker : "set_files_selected/set_total_tokens"
Query->>Tracker : "end_phase('budget_selection'), track_memory()"
Query->>Tracker : "start_phase('packing')"
Query->>Packer : "pack(...)"
Packer-->>Query : "output_path"
Query->>Tracker : "end_phase('packing')"
Query->>Tracker : "end_query()"
Query-->>Caller : "output_path, {tracker, ...}"
```

**Diagram sources**
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [performance.py:72-214](file://src/ws_ctx_engine/monitoring/performance.py#L72-L214)

**Section sources**
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [performance.py:72-214](file://src/ws_ctx_engine/monitoring/performance.py#L72-L214)

### Rust Extension Acceleration
- The optional Rust extension exposes a parallel file walker that respects .gitignore semantics and is significantly faster than Python's equivalent.
- The chunker attempts to import the Rust module first, falling back to Python implementations if unavailable.
- The Rust module is built as a cdylib with release optimizations.

```mermaid
graph LR
Py["Python chunker/base.py<br/>RUST_AVAILABLE"] --> TryRust["Try ws_ctx_engine._rust or _rust"]
TryRust --> |Success| RustMod["PyO3 module _rust"]
TryRust --> |Fail| PyFallback["Python fallbacks"]
RustMod --> Walker["walk_files(root, respect_hidden)"]
Walker --> Py
```

**Diagram sources**
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)
- [_rust lib.rs:1-22](file://_rust/src/lib.rs#L1-L22)
- [_rust walker.rs:1-53](file://_rust/src/walker.rs#L1-L53)

**Section sources**
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)
- [_rust lib.rs:1-22](file://_rust/src/lib.rs#L1-L22)
- [_rust walker.rs:1-53](file://_rust/src/walker.rs#L1-L53)
- [_rust Cargo.toml:1-25](file://_rust/Cargo.toml#L1-L25)

## Lightweight Timing Instrumentation System

### TimingContext and @timed Decorator
The new timing instrumentation system provides lightweight, structured logging for performance measurement without the overhead of heavy profilers. This system is designed for hot-path profiling where minimal performance impact is crucial.

**TimingContext**: A context manager that measures execution time for code blocks and logs structured performance information.

**@timed decorator**: A function decorator that automatically times wrapped functions and emits performance logs with labels for identification.

```mermaid
classDiagram
class TimingContext {
+str label
-float _t0
+__enter__() TimingContext
+__exit__(*_) void
}
class TimedDecorator {
+str label
+decorator(fn) Callable
}
class Logger {
+debug(message) void
}
TimingContext --> Logger : "emits structured logs"
TimedDecorator --> Logger : "emits structured logs"
```

**Diagram sources**
- [timing.py:56-80](file://src/ws_ctx_engine/perf/timing.py#L56-L80)
- [timing.py:25-54](file://src/ws_ctx_engine/perf/timing.py#L25-L54)

### Instrumented Operations
The timing system is comprehensively applied across critical operations:

**Vector Index Operations**:
- `embedding_model_load`: Measures model initialization time
- `embedding_encode`: Times text encoding operations
- `leann_search`: Monitors search performance

**Graph Operations**:
- `igraph_pagerank`: Times PageRank computation
- `networkx_pagerank`: Times fallback PageRank computation

**Retrieval Operations**:
- `retrieval_retrieve`: Times complete retrieval process
- `search_codebase`: Times end-to-end search workflow

**Section sources**
- [timing.py:1-80](file://src/ws_ctx_engine/perf/timing.py#L1-L80)
- [vector_index.py:145-250](file://src/ws_ctx_engine/vector_index/vector_index.py#L145-L250)
- [leann_index.py:172-216](file://src/ws_ctx_engine/vector_index/leann_index.py#L172-L216)
- [graph.py:191-242](file://src/ws_ctx_engine/graph/graph.py#L191-L242)
- [retrieval.py:265-402](file://src/ws_ctx_engine/retrieval/retrieval.py#L265-L402)
- [query.py:159](file://src/ws_ctx_engine/workflow/query.py#L159)

### Usage Examples
The timing instrumentation is applied consistently across the codebase:

**Function Decoration**:
```python
@timed("embedding_encode")
def encode(self, texts: list[str]) -> np.ndarray:
    # encoding logic
```

**Context Manager Usage**:
```python
with TimingContext("pagerank_compute"):
    scores = graph.pagerank()
```

**Structured Log Output**:
```
DEBUG wsctx.perf - [perf] embedding_encode elapsed=123.4ms
DEBUG wsctx.perf - [perf] leann_search elapsed=45.6ms
```

**Section sources**
- [timing.py:25-80](file://src/ws_ctx_engine/perf/timing.py#L25-L80)
- [test_perf_timing.py:17-91](file://tests/unit/test_perf_timing.py#L17-L91)
- [test_phase5_integration.py:492-510](file://tests/integration/test_phase5_integration.py#L492-L510)

## Dependency Analysis
- PerformanceTracker depends on time for timing and optionally psutil for memory tracking.
- Workflows depend on PerformanceTracker to measure and report metrics.
- **TimingContext and @timed depend on time for timing and logging for structured output.**
- The chunker conditionally uses the Rust extension for file walking, improving performance and indirectly reducing memory pressure.
- **Instrumented components rely on the wsctx.perf logger for structured timing output.**

```mermaid
graph TB
PT["PerformanceTracker"] --> TIME["time"]
PT --> PSUTIL["psutil (optional)"]
TIMING["TimingSystem"] --> TIME
TIMING --> LOGGING["logging (structured)"]
IDX["indexer.py"] --> PT
QRY["query.py"] --> PT
CHUNK["chunker/base.py"] --> RS["Rust extension (optional)"]
ENC["vector_index.py"] --> TIMING
SRCH["leann_index.py"] --> TIMING
PR["graph.py"] --> TIMING
RET["retrieval.py"] --> TIMING
```

**Diagram sources**
- [performance.py:8-206](file://src/ws_ctx_engine/monitoring/performance.py#L8-L206)
- [timing.py:11-20](file://src/ws_ctx_engine/perf/timing.py#L11-L20)
- [indexer.py:21-116](file://src/ws_ctx_engine/workflow/indexer.py#L21-L116)
- [query.py:17-289](file://src/ws_ctx_engine/workflow/query.py#L17-L289)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)

**Section sources**
- [performance.py:8-206](file://src/ws_ctx_engine/monitoring/performance.py#L8-L206)
- [timing.py:11-20](file://src/ws_ctx_engine/perf/timing.py#L11-L20)
- [indexer.py:21-116](file://src/ws_ctx_engine/workflow/indexer.py#L21-L116)
- [query.py:17-289](file://src/ws_ctx_engine/workflow/query.py#L17-L289)
- [base.py:10-25](file://src/ws_ctx_engine/chunker/base.py#L10-L25)

## Performance Considerations
- Use PerformanceTracker.start_phase/end_phase around major steps to capture per-phase timings and identify bottlenecks.
- Enable psutil to track peak memory usage; absence of psutil gracefully degrades to no memory tracking.
- **Use @timed decorators and TimingContext for lightweight, structured timing of critical operations.**
- **Monitor instrumented operations for detailed latency breakdowns across encoding, search, page-rank, and retrieval phases.**
- Prefer the Rust extension for file walking to reduce indexing latency and memory footprint.
- Monitor index size growth and adjust backend configurations to maintain query performance.
- Use the benchmark suite to compare performance across backends and configurations.
- **Configure logging level appropriately to capture timing information without excessive overhead.**

## Troubleshooting Guide
Common issues and remedies:
- Missing psutil: Memory tracking is skipped; install psutil to enable peak memory reporting.
- Empty metrics: Ensure tracker.start_indexing/start_query and end_indexing/end_query are called in workflows.
- **Missing timing logs: Ensure wsctx.perf logger is configured and at DEBUG level for timing output.**
- **Unexpected timing values: Verify @timed decorators are properly applied and functions are being called.**
- Unexpectedly high memory usage: Investigate vector index and graph building phases; consider backend tuning or disabling embedding cache if appropriate.
- Slow indexing: Verify Rust extension availability; confirm .gitignore semantics are respected to avoid scanning ignored directories.
- **Timing instrumentation not working: Check that instrumented functions are decorated with @timed and logger name is "wsctx.perf".**

**Section sources**
- [performance.py:185-206](file://src/ws_ctx_engine/monitoring/performance.py#L185-L206)
- [indexer.py:114-116](file://src/ws_ctx_engine/workflow/indexer.py#L114-L116)
- [query.py:287-289](file://src/ws_ctx_engine/workflow/query.py#L287-L289)
- [timing.py:17-20](file://src/ws_ctx_engine/perf/timing.py#L17-L20)

## Conclusion
The ws-ctx-engine performance monitoring system provides precise timing, counts, storage metrics, and optional memory tracking integrated into the indexing and query workflows. The enhanced system now includes comprehensive timing instrumentation through the new Timing class, providing detailed latency breakdowns across encoding times, search operations, page-rank computations, and merge operations. The optional Rust extension accelerates hot-path operations, improving throughput and reducing latency. The lightweight timing instrumentation system offers structured, low-overhead performance measurement for critical operations. The automated benchmark suite enables apples-to-apples comparisons between Python and Rust implementations and across backend configurations, facilitating informed tuning and scaling decisions.

## Appendices

### Benchmarking Methodology
- Automated suite: Uses fixtures to generate repositories of varying sizes and runs indexing and query operations, asserting performance targets and capturing metrics.
- Targets: Indexing and query durations for primary and fallback backends; memory usage tracking.
- **Timing instrumentation: Captures detailed latency breakdowns for individual operations using @timed decorators.**
- Execution: Run tests marked as benchmarks to evaluate performance under realistic conditions.

**Section sources**
- [test_performance_benchmarks.py:141-440](file://tests/test_performance_benchmarks.py#L141-L440)
- [performance.md:45-81](file://docs/guides/performance.md#L45-L81)

### Practical Examples and Best Practices
- Interpreting metrics:
  - Indexing: Total time, files processed per second, index size, and per-phase timings.
  - Query: Total time, files selected, total tokens, and per-phase timings.
  - Memory: Peak memory usage when psutil is available.
  - **Timing instrumentation: Individual operation latencies for encoding, search, page-rank, and retrieval.**
- Identifying bottlenecks:
  - Compare phase_timings to locate long-running steps (parsing, vector indexing, graph building, retrieval, budget selection, packing).
  - **Use @timed decorator outputs to identify slow individual operations within phases.**
- Monitoring under workloads:
  - Scale repository size and backend choices; observe index size growth and query latency.
  - Use formatted metrics output to log performance during CI runs.
  - **Monitor timing logs for consistent performance across different workloads.**
- **Adding instrumentation**:
  - Use @timed decorator for function-level timing: `@timed("operation_name")`
  - Use TimingContext for block-level timing: `with TimingContext("operation_name"):`
  - Choose descriptive labels that clearly identify the operation being measured.

**Section sources**
- [performance.py:215-263](file://src/ws_ctx_engine/monitoring/performance.py#L215-L263)
- [test_performance_properties.py:14-270](file://tests/property/test_performance_properties.py#L14-L270)
- [timing.py:25-80](file://src/ws_ctx_engine/perf/timing.py#L25-L80)
- [test_perf_timing.py:17-91](file://tests/unit/test_perf_timing.py#L17-L91)