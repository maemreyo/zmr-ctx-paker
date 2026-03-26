# Observer Pattern & Event Handling

<cite>
**Referenced Files in This Document**
- [logger.py](file://src/ws_ctx_engine/logger/logger.py)
- [performance.py](file://src/ws_ctx_engine/monitoring/performance.py)
- [dedup_cache.py](file://src/ws_ctx_engine/session/dedup_cache.py)
- [embedding_cache.py](file://src/ws_ctx_engine/vector_index/embedding_cache.py)
- [logger_demo.py](file://examples/logger_demo.py)
- [test_logger.py](file://tests/unit/test_logger.py)
- [test_session_dedup_cache.py](file://tests/unit/test_session_dedup_cache.py)
- [__init__.py](file://src/ws_ctx_engine/__init__.py)
</cite>

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

## Introduction
This document explains how the Observer pattern is implemented across logging, monitoring, and caching subsystems in the ws-ctx-engine project. It focuses on:
- How WsCtxEngineLogger acts as an observable subject that emits log events to registered observers (handlers)
- How performance monitors observe system metrics during indexing and query operations
- How cache observers track content changes and deduplicate repeated content

We also describe observer registration, notification mechanisms, and the event-driven architecture, with practical examples and diagrams that map to actual source files.

## Project Structure
The Observer pattern touches three primary areas:
- Logging: WsCtxEngineLogger publishes structured log events
- Monitoring: PerformanceTracker collects and exposes metrics
- Caching: SessionDeduplicationCache and EmbeddingCache persistently track content changes

```mermaid
graph TB
subgraph "Logging"
WL["WsCtxEngineLogger<br/>publishes log events"]
end
subgraph "Monitoring"
PT["PerformanceTracker<br/>collects metrics"]
PM["PerformanceMetrics<br/>data container"]
end
subgraph "Caching"
SDC["SessionDeduplicationCache<br/>tracks content hashes"]
EC["EmbeddingCache<br/>persists embeddings"]
end
WL --> |"log_* events"| Observers["Observers / Handlers"]
PT --> |"metrics updates"| Observers
SDC --> |"content hash changes"| Observers
EC --> |"embedding persistence"| Observers
```

**Diagram sources**
- [logger.py:13-145](file://src/ws_ctx_engine/logger/logger.py#L13-L145)
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- [dedup_cache.py:35-154](file://src/ws_ctx_engine/session/dedup_cache.py#L35-L154)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

**Section sources**
- [logger.py:13-145](file://src/ws_ctx_engine/logger/logger.py#L13-L145)
- [performance.py:72-263](file://src/ws_ctx_engine/monitoring/performance.py#L72-L263)
- [dedup_cache.py:35-154](file://src/ws_ctx_engine/session/dedup_cache.py#L35-L154)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

## Core Components
- WsCtxEngineLogger: Centralized logging subject emitting structured log events to console and file handlers. Provides convenience methods for fallback, phase completion, and error logging.
- PerformanceTracker: Tracks timing, file counts, index sizes, token counts, and memory usage; exposes metrics for observation.
- SessionDeduplicationCache: Persists content hashes per session; acts as an observer of content changes and provides dedup markers when content repeats.
- EmbeddingCache: Persists content-hash to embedding mappings; logs load/save events that can be observed by external systems.

Key implementation references:
- Logger subject and methods: [logger.py:13-145](file://src/ws_ctx_engine/logger/logger.py#L13-L145)
- Performance metrics and tracker: [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)
- Session cache observer: [dedup_cache.py:35-154](file://src/ws_ctx_engine/session/dedup_cache.py#L35-L154)
- Embedding cache persistence: [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

**Section sources**
- [logger.py:13-145](file://src/ws_ctx_engine/logger/logger.py#L13-L145)
- [performance.py:72-263](file://src/ws_ctx_engine/monitoring/performance.py#L72-L263)
- [dedup_cache.py:35-154](file://src/ws_ctx_engine/session/dedup_cache.py#L35-L154)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

## Architecture Overview
The system follows an event-driven architecture:
- Subjects emit events: WsCtxEngineLogger emits log events; PerformanceTracker emits metric snapshots; caches emit persistence events
- Observers react: Handlers receive log events; external systems monitor metrics; downstream components consume dedup markers and embedding updates

```mermaid
sequenceDiagram
participant Caller as "Caller"
participant Logger as "WsCtxEngineLogger"
participant Console as "Console Handler"
participant File as "File Handler"
Caller->>Logger : "log_phase(phase, duration, metrics)"
Logger->>Console : "emit formatted log"
Logger->>File : "emit formatted log"
Console-->>Caller : "visible on console"
File-->>Caller : "written to file"
```

**Diagram sources**
- [logger.py:79-94](file://src/ws_ctx_engine/logger/logger.py#L79-L94)
- [logger.py:43-62](file://src/ws_ctx_engine/logger/logger.py#L43-L62)

**Section sources**
- [logger.py:79-94](file://src/ws_ctx_engine/logger/logger.py#L79-L94)
- [logger.py:43-62](file://src/ws_ctx_engine/logger/logger.py#L43-L62)

## Detailed Component Analysis

### WsCtxEngineLogger: Observable Subject for Log Events
WsCtxEngineLogger is the central observable subject that publishes structured log events to registered observers (console and file handlers). It supports:
- Dual-output handlers: console (INFO+) and file (DEBUG+)
- Structured formatting: timestamp | level | name | message
- Convenience methods for fallback, phase completion, and error logging

```mermaid
classDiagram
class WsCtxEngineLogger {
+Path log_dir
+Path log_file_path
+Logger logger
+__init__(log_dir, name)
+log_fallback(component, primary, fallback, reason) void
+log_phase(phase, duration, metrics) void
+log_error(error, context) void
+debug(message) void
+info(message) void
+warning(message) void
+error(message) void
}
class get_logger {
+__call__(log_dir) WsCtxEngineLogger
}
get_logger --> WsCtxEngineLogger : "returns singleton"
```

- Observer registration: The subject initializes and registers console and file handlers internally; observers are effectively bound to these handlers.
- Notification mechanism: Calls to log_* methods propagate through the Python logging framework to attached handlers.
- Event-driven behavior: Each log_* call triggers immediate emission to observers.

Practical usage and examples:
- Logger demo script demonstrates basic usage and structured logging: [logger_demo.py:1-36](file://examples/logger_demo.py#L1-L36)
- Unit tests verify structured format, fallback logging, phase logging, and error logging: [test_logger.py:82-180](file://tests/unit/test_logger.py#L82-L180)

**Diagram sources**
- [logger.py:13-145](file://src/ws_ctx_engine/logger/logger.py#L13-L145)

**Section sources**
- [logger.py:13-145](file://src/ws_ctx_engine/logger/logger.py#L13-L145)
- [logger_demo.py:1-36](file://examples/logger_demo.py#L1-L36)
- [test_logger.py:82-180](file://tests/unit/test_logger.py#L82-L180)

### PerformanceTracker: Metrics Observer for System Performance
PerformanceTracker observes system metrics across indexing and query phases. It tracks:
- Timing: indexing_time, query_time, and per-phase timings
- Counts: files_processed, files_selected, total_tokens
- Memory: peak memory usage
- Persistence: index size calculation via directory walk

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
+dict~str,float~ phase_timings
+to_dict() dict
}
class PerformanceTracker {
+PerformanceMetrics metrics
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

- Observer registration: External systems can poll metrics via get_metrics() and format_metrics().
- Notification mechanism: Metrics are updated synchronously during lifecycle methods; observers can subscribe by periodically retrieving metrics.
- Event-driven behavior: Lifecycle methods (start/end) act as events that trigger metric updates.

**Diagram sources**
- [performance.py:13-263](file://src/ws_ctx_engine/monitoring/performance.py#L13-L263)

**Section sources**
- [performance.py:72-263](file://src/ws_ctx_engine/monitoring/performance.py#L72-L263)

### SessionDeduplicationCache: Content Change Observer for Caching
SessionDeduplicationCache observes content changes by tracking content hashes within a session. It:
- Computes SHA-256 hashes for incoming content
- Persists seen hashes to disk in a JSON file
- Returns a dedup marker when the same content is encountered again
- Supports atomic writes to avoid corruption and isolation via session_id

```mermaid
flowchart TD
Start(["check_and_mark(file_path, content)"]) --> Hash["Compute SHA-256 hash"]
Hash --> Exists{"Hash exists in seen_hashes?"}
Exists --> |Yes| Marker["Build DEDUPLICATED marker"]
Marker --> ReturnDup["Return (True, marker)"]
Exists --> |No| Save["Record hash → path and persist cache"]
Save --> ReturnNew["Return (False, original content)"]
```

- Observer registration: The cache itself is the observer; it maintains state and persists changes.
- Notification mechanism: On first encounter, content is stored; on subsequent encounters, a marker is returned.
- Event-driven behavior: Each call to check_and_mark is an event that either updates state or returns a cached result.

**Diagram sources**
- [dedup_cache.py:65-89](file://src/ws_ctx_engine/session/dedup_cache.py#L65-L89)

**Section sources**
- [dedup_cache.py:35-154](file://src/ws_ctx_engine/session/dedup_cache.py#L35-L154)
- [test_session_dedup_cache.py:8-98](file://tests/unit/test_session_dedup_cache.py#L8-L98)

### EmbeddingCache: Persistence Observer for Vector Embeddings
EmbeddingCache persists content-hash to embedding vector mappings to avoid recomputation. It:
- Loads existing cache from disk (JSON index + NumPy vectors)
- Stores new or updated embeddings
- Saves cache atomically to disk
- Logs load/save events for observability

```mermaid
classDiagram
class EmbeddingCache {
-Path _cache_dir
-Path _embeddings_path
-Path _index_path
-dict~str,int~ _hash_to_idx
-ndarray _vectors
+__init__(cache_dir) void
+load() void
+save() void
+lookup(content_hash) ndarray?
+store(content_hash, vector) void
+content_hash(text) str
+size() int
}
```

- Observer registration: External systems can observe load/save events via logger output.
- Notification mechanism: load() and save() methods log informational and warning events.
- Event-driven behavior: Persistence events occur on explicit load/save calls.

**Diagram sources**
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

**Section sources**
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)

## Dependency Analysis
The modules interact as follows:
- WsCtxEngineLogger depends on Python logging and file I/O; it emits to console and file handlers
- PerformanceTracker depends on time measurement and optional psutil for memory tracking
- SessionDeduplicationCache depends on hashing and JSON persistence
- EmbeddingCache depends on NumPy and JSON for persistence

```mermaid
graph LR
WL["WsCtxEngineLogger"] --> LOG["Python logging"]
WL --> FS["Filesystem"]
PT["PerformanceTracker"] --> TIME["time"]
PT --> PS["psutil (optional)"]
SDC["SessionDeduplicationCache"] --> HASH["hashlib"]
SDC --> JSON["json"]
SDC --> FS
EC["EmbeddingCache"] --> NP["numpy"]
EC --> JSON
EC --> FS
```

**Diagram sources**
- [logger.py:7-11](file://src/ws_ctx_engine/logger/logger.py#L7-L11)
- [performance.py:8-11](file://src/ws_ctx_engine/monitoring/performance.py#L8-L11)
- [dedup_cache.py:28-32](file://src/ws_ctx_engine/session/dedup_cache.py#L28-L32)
- [embedding_cache.py:18-24](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L18-L24)

**Section sources**
- [logger.py:7-11](file://src/ws_ctx_engine/logger/logger.py#L7-L11)
- [performance.py:8-11](file://src/ws_ctx_engine/monitoring/performance.py#L8-L11)
- [dedup_cache.py:28-32](file://src/ws_ctx_engine/session/dedup_cache.py#L28-L32)
- [embedding_cache.py:18-24](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L18-L24)

## Performance Considerations
- Logging overhead: Using dual handlers (console and file) increases I/O; ensure batching and appropriate log levels for production.
- Metrics tracking: Memory tracking via psutil adds overhead; disable if not needed.
- Cache persistence: Atomic writes in SessionDeduplicationCache and EmbeddingCache minimize corruption risk but add I/O; tune frequency of saves.
- Hash computation: SHA-256 hashing is efficient but consider content size; large files increase CPU usage.

## Troubleshooting Guide
Common issues and resolutions:
- Duplicate handlers: Creating multiple loggers with the same name avoids duplicates by reusing the underlying logger; verify handler count and avoid repeated initialization.
- Path traversal protection: SessionDeduplicationCache validates cache file paths to prevent directory traversal; ensure session_id does not contain path separators.
- Cache corruption: Atomic write strategy prevents partial writes; if corruption occurs, clear cache and regenerate.
- Embedding cache loading: Load failures are logged as warnings; verify file permissions and disk space.

Evidence and references:
- Singleton logger and handler verification: [test_logger.py:241-263](file://tests/unit/test_logger.py#L241-L263)
- Path traversal protection: [dedup_cache.py:49-57](file://src/ws_ctx_engine/session/dedup_cache.py#L49-L57)
- Atomic write behavior: [dedup_cache.py:119-136](file://src/ws_ctx_engine/session/dedup_cache.py#L119-L136)
- Embedding cache load/save logging: [embedding_cache.py:55-83](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L55-L83)

**Section sources**
- [test_logger.py:241-263](file://tests/unit/test_logger.py#L241-L263)
- [dedup_cache.py:49-57](file://src/ws_ctx_engine/session/dedup_cache.py#L49-L57)
- [dedup_cache.py:119-136](file://src/ws_ctx_engine/session/dedup_cache.py#L119-L136)
- [embedding_cache.py:55-83](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L55-L83)

## Conclusion
The ws-ctx-engine project implements an event-driven architecture centered around:
- WsCtxEngineLogger as an observable subject emitting structured log events
- PerformanceTracker observing and aggregating system metrics
- SessionDeduplicationCache and EmbeddingCache acting as observers of content changes and persistence events

Observers are integrated through Python logging handlers, polling of metrics, and cache state updates. The design emphasizes reliability (atomic writes), observability (structured logs and metrics), and performance (hash-based deduplication and optional memory tracking).