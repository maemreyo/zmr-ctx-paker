# Logging and Monitoring

<cite>
**Referenced Files in This Document**
- [logger.py](file://src/ws_ctx_engine/logger/logger.py)
- [backend_selector.py](file://src/ws_ctx_engine/backend_selector/backend_selector.py)
- [performance.py](file://src/ws_ctx_engine/monitoring/performance.py)
- [config.py](file://src/ws_ctx_engine/config/config.py)
- [graph.py](file://src/ws_ctx_engine/graph/graph.py)
- [vector_index.py](file://src/ws_ctx_engine/vector_index/vector_index.py)
- [indexer.py](file://src/ws_ctx_engine/workflow/indexer.py)
- [query.py](file://src/ws_ctx_engine/workflow/query.py)
- [embedding_cache.py](file://src/ws_ctx_engine/vector_index/embedding_cache.py)
- [models.py](file://src/ws_ctx_engine/models/models.py)
- [logger_demo.py](file://examples/logger_demo.py)
- [test_logger.py](file://tests/unit/test_logger.py)
- [test_fallback_scenarios.py](file://tests/integration/test_fallback_scenarios.py)
</cite>

## Update Summary
**Changes Made**
- Updated Logging Infrastructure section to reflect lazy initialization with `_ensure_initialized()` method
- Added comprehensive coverage of console-only fallback mode when file logging is unavailable
- Enhanced error handling documentation for log directory creation failures
- Updated all logging methods to reflect the new `_ensure_initialized()` pattern
- Added new section on Reliability and Error Recovery Capabilities
- Updated Troubleshooting Guide with console-only fallback scenarios

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Enhanced Logging Infrastructure](#enhanced-logging-infrastructure)
7. [Dependency Analysis](#dependency-analysis)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Conclusion](#conclusion)
11. [Appendices](#appendices)

## Introduction
This document describes the logging and monitoring system for backend selection and runtime observability in the engine. It explains how structured logs capture backend availability, selection decisions, fallback events, and performance metrics. The system now features enhanced reliability with lazy initialization, automatic error recovery, and console-only fallback modes. It also provides guidance for analyzing logs to troubleshoot backend issues, benchmark performance across tiers, and build automated monitoring dashboards for backend health.

## Project Structure
The logging and monitoring system spans several modules:
- Logging infrastructure: centralized logger with dual output (console and file) and structured message formats, featuring lazy initialization and error recovery
- Backend selection: automatic fallback chains for vector index, graph, and embeddings
- Monitoring: performance metrics collection and reporting for indexing and query phases
- Workflows: index and query phases that emit structured logs and metrics
- Configuration: backend choices and performance tuning options

```mermaid
graph TB
subgraph "Enhanced Logging Infrastructure"
L["WsCtxEngineLogger<br/>Lazy Initialization + Error Recovery"]
L --> EI["_ensure_initialized()<br/>Console-only Fallback Mode"]
end
subgraph "Backend Selection"
BS["BackendSelector<br/>Fallback levels 1..6"]
CFG["Config<br/>backends.* settings"]
end
subgraph "Monitoring"
PT["PerformanceTracker<br/>Timers & metrics"]
PM["PerformanceMetrics<br/>Structured metrics"]
end
subgraph "Workflows"
IDX["index_repository<br/>Structured logs + metrics"]
QRY["query_and_pack<br/>Structured logs + metrics"]
end
subgraph "Backends"
VI["VectorIndex<br/>LEANN/FAISS"]
GR["RepoMapGraph<br/>IGraph/NetworkX"]
EMB["EmbeddingGenerator<br/>Local/API"]
end
L --> BS
BS --> CFG
PT --> IDX
PT --> QRY
IDX --> VI
IDX --> GR
QRY --> VI
QRY --> GR
VI --> EMB
```

**Diagram sources**
- [logger.py:13-188](file://src/ws_ctx_engine/logger/logger.py#L13-L188)
- [backend_selector.py:13-193](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L193)
- [performance.py:72-263](file://src/ws_ctx_engine/monitoring/performance.py#L72-L263)
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)
- [vector_index.py:282-800](file://src/ws_ctx_engine/vector_index/vector_index.py#L282-L800)
- [graph.py:572-667](file://src/ws_ctx_engine/graph/graph.py#L572-L667)

**Section sources**
- [logger.py:13-188](file://src/ws_ctx_engine/logger/logger.py#L13-L188)
- [backend_selector.py:13-193](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L193)
- [performance.py:72-263](file://src/ws_ctx_engine/monitoring/performance.py#L72-L263)
- [indexer.py:72-371](file://src/ws_ctx_engine/workflow/indexer.py#L72-L371)
- [query.py:230-617](file://src/ws_ctx_engine/workflow/query.py#L230-L617)

## Core Components
- **WsCtxEngineLogger**: dual-output logger with structured format, lazy initialization, and automatic error recovery with console-only fallback mode
- **BackendSelector**: centralizes backend selection with explicit fallback levels and emits structured fallback logs
- **PerformanceTracker and PerformanceMetrics**: collect and report timing, file counts, index size, token counts, and memory usage
- **Workflows**: index_repository and query_and_pack orchestrate phases, log progress, and record metrics
- **Config**: defines backend choices and performance-related toggles that influence logging and monitoring

Key structured log categories:
- Backend configuration and fallback events
- Phase completion with metrics
- Error occurrences with context and stack traces
- Console-only fallback notifications when file logging fails

**Section sources**
- [logger.py:64-188](file://src/ws_ctx_engine/logger/logger.py#L64-L188)
- [backend_selector.py:120-178](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L120-L178)
- [performance.py:13-70](file://src/ws_ctx_engine/monitoring/performance.py#L13-L70)
- [indexer.py:168-371](file://src/ws_ctx_engine/workflow/indexer.py#L168-L371)
- [query.py:310-617](file://src/ws_ctx_engine/workflow/query.py#L310-L617)
- [config.py:74-101](file://src/ws_ctx_engine/config/config.py#L74-L101)

## Architecture Overview
The logging and monitoring architecture integrates tightly with backend selection and workflows, featuring enhanced reliability through lazy initialization and error recovery:

```mermaid
sequenceDiagram
participant CLI as "CLI/Caller"
participant IDX as "index_repository"
participant BS as "BackendSelector"
participant VI as "VectorIndex"
participant GR as "RepoMapGraph"
participant LOG as "WsCtxEngineLogger"
participant PERF as "PerformanceTracker"
CLI->>IDX : "index_repository(repo_path, config)"
IDX->>LOG : "info(...)" (start index)
IDX->>PERF : "start_indexing()"
IDX->>BS : "log_current_configuration()"
BS->>LOG : "info(...)" (backend config)
Note over LOG : Lazy initialization occurs on first use
IDX->>BS : "select_vector_index(...)"
BS->>VI : "create_vector_index(...)"
VI-->>BS : "VectorIndex instance or raises"
alt "VectorIndex creation fails"
BS->>LOG : "error(...)" (all backends failed)
BS->>LOG : "log_fallback(...)" (component=vector_index)
end
IDX->>BS : "select_graph(...)"
BS->>GR : "create_graph(...)"
GR-->>BS : "RepoMapGraph instance or raises"
alt "Graph creation fails"
BS->>LOG : "error(...)" (all backends failed)
BS->>LOG : "log_fallback(...)" (component=graph)
end
IDX->>PERF : "end_indexing(), set_index_size(), format_metrics()"
IDX->>LOG : "info(...)" (index complete)
IDX-->>CLI : "PerformanceTracker"
```

**Diagram sources**
- [indexer.py:125-371](file://src/ws_ctx_engine/workflow/indexer.py#L125-L371)
- [backend_selector.py:36-119](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L36-L119)
- [logger.py:64-188](file://src/ws_ctx_engine/logger/logger.py#L64-L188)
- [performance.py:95-214](file://src/ws_ctx_engine/monitoring/performance.py#L95-L214)

## Detailed Component Analysis

### Logging Infrastructure
- **Dual output handlers**: console (INFO+) and file (DEBUG+), with a standardized format
- **Lazy initialization**: `_ensure_initialized()` method ensures handlers are created only when first needed
- **Automatic error recovery**: Console-only fallback mode when file logging fails
- **Specialized helpers**:
  - `log_fallback(component, primary, fallback, reason)`: captures backend fallback events
  - `log_phase(phase, duration, **metrics)`: records phase completion with metrics
  - `log_error(error, context)`: logs errors with stack traces and contextual key-value pairs
- **Singleton access** via `get_logger()`

Practical usage examples are demonstrated in the demo script and unit tests.

**Updated** Enhanced with lazy initialization and console-only fallback capabilities

**Section sources**
- [logger.py:13-188](file://src/ws_ctx_engine/logger/logger.py#L13-L188)
- [logger_demo.py:1-36](file://examples/logger_demo.py#L1-L36)
- [test_logger.py:82-180](file://tests/unit/test_logger.py#L82-L180)

### Backend Selection and Fallback Tracking
- BackendSelector determines fallback level (1–6) based on configuration for vector_index, graph, and embeddings
- It logs the current configuration and triggers fallback events when primary backends fail
- Fallback events are emitted using the structured log_fallback format

```mermaid
flowchart TD
Start(["Select Backends"]) --> CheckCfg["Read config.backends.*"]
CheckCfg --> DecideVI{"VectorIndex available?"}
DecideVI --> |Yes| UseVI["Use configured vector backend"]
DecideVI --> |No| FallbackVI["log_fallback(component='vector_index')"]
FallbackVI --> UseVIAlt["Try next vector backend"]
UseVIAlt --> DecideGR{"Graph available?"}
DecideGR --> |Yes| UseGR["Use configured graph backend"]
DecideGR --> |No| FallbackGR["log_fallback(component='graph')"]
FallbackGR --> UseGRAlt["Try next graph backend"]
UseGRAlt --> Done(["Proceed with selected backends"])
```

**Diagram sources**
- [backend_selector.py:120-178](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L120-L178)
- [graph.py:572-621](file://src/ws_ctx_engine/graph/graph.py#L572-L621)
- [vector_index.py:506-647](file://src/ws_ctx_engine/vector_index/vector_index.py#L506-L647)

**Section sources**
- [backend_selector.py:120-178](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L120-L178)
- [graph.py:572-621](file://src/ws_ctx_engine/graph/graph.py#L572-L621)
- [vector_index.py:506-647](file://src/ws_ctx_engine/vector_index/vector_index.py#L506-L647)

### Performance Monitoring and Metrics
- PerformanceTracker measures:
  - Overall indexing and query durations
  - Phase-specific timings
  - Files processed, files selected, total tokens
  - Index size on disk
  - Peak memory usage (when psutil is available)
- PerformanceMetrics provides a serializable snapshot of collected metrics

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
+dict phase_timings
+to_dict() dict
}
class PerformanceTracker {
-PerformanceMetrics metrics
-dict _phase_start_times
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
PerformanceTracker --> PerformanceMetrics : "collects"
```

**Diagram sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)

**Section sources**
- [performance.py:72-263](file://src/ws_ctx_engine/monitoring/performance.py#L72-L263)
- [indexer.py:358-371](file://src/ws_ctx_engine/workflow/indexer.py#L358-L371)
- [query.py:602-617](file://src/ws_ctx_engine/workflow/query.py#L602-L617)

### Workflows: Indexing and Query
- index_repository orchestrates parsing, vector indexing, graph building, metadata saving, and domain map building. It logs phase completions and errors, records metrics, and reports totals.
- query_and_pack loads indexes, retrieves candidates, selects within budget, packs output, and logs metrics.

```mermaid
sequenceDiagram
participant IDX as "index_repository"
participant LOG as "WsCtxEngineLogger"
participant PERF as "PerformanceTracker"
IDX->>LOG : "info('Starting index phase...')"
IDX->>PERF : "start_indexing()"
loop "Phases"
IDX->>LOG : "log_phase(phase, duration, ...)"
IDX->>PERF : "start_phase()/end_phase()"
end
IDX->>PERF : "set_index_size(), end_indexing()"
IDX->>LOG : "info('Index phase complete | ...')"
IDX-->>IDX : "return tracker"
```

**Diagram sources**
- [indexer.py:118-371](file://src/ws_ctx_engine/workflow/indexer.py#L118-L371)
- [logger.py:79-94](file://src/ws_ctx_engine/logger/logger.py#L79-L94)
- [performance.py:95-133](file://src/ws_ctx_engine/monitoring/performance.py#L95-L133)

**Section sources**
- [indexer.py:118-371](file://src/ws_ctx_engine/workflow/indexer.py#L118-L371)
- [query.py:291-617](file://src/ws_ctx_engine/workflow/query.py#L291-L617)

### Embeddings and API Fallback Logging
- EmbeddingGenerator attempts local embeddings and falls back to API when memory constraints or failures occur. It logs fallback events with component, primary, fallback, and reason.

**Section sources**
- [vector_index.py:199-251](file://src/ws_ctx_engine/vector_index/vector_index.py#L199-L251)
- [vector_index.py:253-280](file://src/ws_ctx_engine/vector_index/vector_index.py#L253-L280)

### Configuration Impact on Logging and Monitoring
- Config.backends controls backend selection and influences fallback level and logs
- Config.embeddings affects embedding generation and may trigger API fallback logs
- Config.performance toggles caching and incremental indexing, impacting metrics and logs

**Section sources**
- [config.py:74-101](file://src/ws_ctx_engine/config/config.py#L74-L101)
- [config.py:192-215](file://src/ws_ctx_engine/config/config.py#L192-L215)

## Enhanced Logging Infrastructure

### Lazy Initialization with _ensure_initialized()
The logging system now features intelligent lazy initialization through the `_ensure_initialized()` method, which ensures handlers are created only when first needed. This approach provides several benefits:

- **Resource efficiency**: Handlers are only created when logging is actually used
- **Graceful degradation**: System continues to function even if initialization fails
- **Thread safety**: Proper synchronization during initialization

### Console-Only Fallback Mode
When file logging fails due to directory creation issues or permission problems, the system automatically switches to console-only logging:

- **Automatic detection**: File handler creation failures trigger fallback logic
- **Preserved functionality**: Console logging continues to work normally
- **Error isolation**: File logging failures don't affect application operation
- **Clear indication**: Console-only mode is maintained until file logging can be restored

### Improved Error Handling
The enhanced error handling covers various failure scenarios:

- **Directory creation failures**: Graceful handling of permission issues and invalid paths
- **File system errors**: Robust handling of disk space and access problems
- **Encoding issues**: Proper handling of character encoding problems
- **Exception propagation**: Clear error messages with stack traces for debugging

```mermaid
flowchart TD
Start(["Logger Usage Request"]) --> CheckInit{"Already initialized?"}
CheckInit --> |No| TryInit["Call _ensure_initialized()"]
CheckInit --> |Yes| UseLogger["Use existing logger"]
TryInit --> CreateDir["Create log directory"]
CreateDir --> DirSuccess{"Directory created?"}
DirSuccess --> |Yes| SetupDual["Setup console + file handlers"]
DirSuccess --> |No| SetupConsole["Setup console-only handlers"]
SetupDual --> InitComplete["Initialization complete"]
SetupConsole --> InitComplete
UseLogger --> End(["Return to caller"])
InitComplete --> End
```

**Diagram sources**
- [logger.py:36-98](file://src/ws_ctx_engine/logger/logger.py#L36-L98)

**Section sources**
- [logger.py:36-98](file://src/ws_ctx_engine/logger/logger.py#L36-L98)
- [logger.py:100-188](file://src/ws_ctx_engine/logger/logger.py#L100-L188)

## Dependency Analysis
- Logger is used pervasively across modules for structured logging
- BackendSelector depends on Config and uses logger for fallback and configuration logs
- Workflows depend on BackendSelector and logger for phase and error logs; they also depend on PerformanceTracker for metrics
- VectorIndex and Graph implementations use logger for fallback and operational logs
- EmbeddingCache uses standard logging to report cache load/save status

```mermaid
graph LR
CFG["Config"] --> BS["BackendSelector"]
BS --> LOG["WsCtxEngineLogger"]
IDX["indexer.py"] --> BS
IDX --> LOG
IDX --> PT["PerformanceTracker"]
QRY["query.py"] --> LOG
QRY --> PT
VI["vector_index.py"] --> LOG
GR["graph.py"] --> LOG
EC["embedding_cache.py"] --> LOG
```

**Diagram sources**
- [config.py:74-101](file://src/ws_ctx_engine/config/config.py#L74-L101)
- [backend_selector.py:26-34](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L26-L34)
- [indexer.py:125-127](file://src/ws_ctx_engine/workflow/indexer.py#L125-L127)
- [query.py:288-290](file://src/ws_ctx_engine/workflow/query.py#L288-L290)
- [vector_index.py:124-125](file://src/ws_ctx_engine/vector_index/vector_index.py#L124-L125)
- [graph.py:16-16](file://src/ws_ctx_engine/graph/graph.py#L16-L16)
- [embedding_cache.py:25-25](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L25-L25)

**Section sources**
- [config.py:74-101](file://src/ws_ctx_engine/config/config.py#L74-L101)
- [backend_selector.py:26-34](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L26-L34)
- [indexer.py:125-127](file://src/ws_ctx_engine/workflow/indexer.py#L125-L127)
- [query.py:288-290](file://src/ws_ctx_engine/workflow/query.py#L288-L290)
- [vector_index.py:124-125](file://src/ws_ctx_engine/vector_index/vector_index.py#L124-L125)
- [graph.py:16-16](file://src/ws_ctx_engine/graph/graph.py#L16-L16)
- [embedding_cache.py:25-25](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L25-L25)

## Performance Considerations
- Use PerformanceTracker to measure end-to-end indexing and query durations
- Track phase-specific timings to identify bottlenecks
- Monitor index size growth and memory usage to assess storage and resource needs
- Enable incremental indexing and embedding cache to reduce rebuild times
- **Enhanced logging performance**: Lazy initialization minimizes startup overhead
- **Error recovery efficiency**: Console-only fallback maintains system responsiveness during file logging failures

## Troubleshooting Guide

### Interpreting Structured Logs
- Backend configuration logs include fallback level and backend choices
- Fallback logs include component, primary backend, fallback backend, and reason
- Phase logs include phase name, duration, and additional metrics
- Error logs include context key-value pairs and stack traces
- **Console-only mode indicators**: Look for preserved logging functionality despite file logging failures

### Diagnosing Backend Issues
- If vector index creation fails, check fallback logs and configuration for vector_index backend
- If graph creation fails, check fallback logs and configuration for graph backend
- If embeddings fail due to memory, look for API fallback logs and adjust device/batch_size
- **File logging failures**: Check for console-only fallback mode indicators and directory permissions

### Automated Monitoring Dashboards
- Use structured logs to build dashboards tracking:
  - Fallback frequency per component
  - Phase durations over time
  - Error rates and error distribution
  - **Console-only fallback frequency**: Monitor reliability metrics
- Use PerformanceTracker metrics to monitor:
  - Index size growth
  - Token counts and budget utilization
  - Peak memory usage trends

### Console-Only Fallback Scenarios
When file logging becomes unavailable, the system automatically switches to console-only mode:

- **Symptoms**: No log files created, but console output continues
- **Causes**: Permission denied, invalid directory path, disk space issues
- **Resolution**: Fix file system issues, restore permissions, or remove read-only restrictions
- **Verification**: Check that console logging continues to function normally

**Section sources**
- [logger.py:64-188](file://src/ws_ctx_engine/logger/logger.py#L64-L188)
- [indexer.py:168-176](file://src/ws_ctx_engine/workflow/indexer.py#L168-L176)
- [query.py:317-322](file://src/ws_ctx_engine/workflow/query.py#L317-L322)

## Conclusion
The logging and monitoring system provides a robust, structured approach to backend selection observability and performance tracking. The enhanced logging infrastructure with lazy initialization, automatic error recovery, and console-only fallback mode ensures reliable operation even under adverse conditions. By leveraging structured logs and metrics, teams can quickly diagnose backend issues, benchmark performance across tiers, and operate reliable automated monitoring systems with improved fault tolerance.

## Appendices

### Log Message Reference
- Backend configuration: "Backend configuration | level=<N> | description=... | vector_index=... | graph=... | embeddings=..."
- Fallback event: "Fallback triggered | component=<name> | primary=<backend> | fallback=<backend> | reason=<msg>"
- Phase completion: "Phase complete | phase=<name> | duration=<s>s | <metrics...>"
- Error occurrence: "Error occurred | <context...>", with stack trace
- **Console-only mode**: Automatic fallback notification when file logging is unavailable

### Example Workflows and Tests
- Demo script demonstrates logger usage for fallback, phase logs, and error logging
- Unit tests validate structured log format, fallback/error logging behavior, and console-only fallback scenarios
- Integration tests exercise fallback scenarios and validate graceful degradation

**Section sources**
- [logger_demo.py:1-36](file://examples/logger_demo.py#L1-L36)
- [test_logger.py:82-180](file://tests/unit/test_logger.py#L82-L180)
- [test_fallback_scenarios.py:327-467](file://tests/integration/test_fallback_scenarios.py#L327-L467)