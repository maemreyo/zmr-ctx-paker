# Vector Index System

<cite>
**Referenced Files in This Document**
- [vector_index.py](file://src/ws_ctx_engine/vector_index/vector_index.py)
- [leann_index.py](file://src/ws_ctx_engine/vector_index/leann_index.py)
- [embedding_cache.py](file://src/ws_ctx_engine/vector_index/embedding_cache.py)
- [model_registry.py](file://src/ws_ctx_engine/vector_index/model_registry.py)
- [backend_selector.py](file://src/ws_ctx_engine/backend_selector/backend_selector.py)
- [indexer.py](file://src/ws_ctx_engine/workflow/indexer.py)
- [query.py](file://src/ws_ctx_engine/workflow/query.py)
- [config.py](file://src/ws_ctx_engine/config/config.py)
- [retrieval.py](file://src/ws_ctx_engine/retrieval/retrieval.py)
- [vector-index.md](file://docs/reference/vector-index.md)
- [performance.md](file://docs/guides/performance.md)
- [MCP_PERFORMANCE_OPTIMIZATION.md](file://docs/performance/MCP_PERFORMANCE_OPTIMIZATION.md)
- [test_vector_index.py](file://tests/unit/test_vector_index.py)
- [test_embedding_cache.py](file://tests/unit/test_embedding_cache.py)
- [test_model_registry.py](file://tests/unit/test_model_registry.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced ModelRegistry with thread-safe singleton patterns and ONNX backend acceleration
- Added automatic fallback mechanisms for model loading and encoding
- Integrated background model pre-warming in MCP server initialization
- Added comprehensive environment variable controls for model behavior
- Updated embedding generation to utilize ModelRegistry for improved performance

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
This document describes the vector index system that powers semantic search over code repositories. It explains the backend selection strategy, the LEANN implementation for efficient similarity search, and the embedding cache mechanisms. It documents the vector index interface, supported backends (LEANN, FAISS), and fallback strategies. It also covers embedding generation, storage optimization, query performance characteristics, configuration examples, memory usage optimization, scaling considerations, embedding cache management, precomputation strategies, and integration with the retrieval system.

**Updated** Enhanced with ModelRegistry thread-safe singleton patterns, ONNX backend acceleration, automatic fallback mechanisms, and background model pre-warming capabilities.

## Project Structure
The vector index system resides under the vector_index module and integrates with the broader indexing and querying workflows.

```mermaid
graph TB
subgraph "Vector Index Module"
VI["vector_index.py"]
LEANN["leann_index.py"]
CACHE["embedding_cache.py"]
REG["model_registry.py"]
end
subgraph "Integration"
BS["backend_selector.py"]
IDX["workflow/indexer.py"]
QRY["workflow/query.py"]
RET["retrieval/retrieval.py"]
CFG["config/config.py"]
MCP["mcp/server.py"]
end
VI --> BS
LEANN --> BS
CACHE --> IDX
REG --> VI
REG --> MCP
BS --> IDX
BS --> QRY
VI --> RET
LEANN --> RET
CFG --> BS
CFG --> IDX
CFG --> QRY
MCP --> REG
```

**Diagram sources**
- [vector_index.py:1-1122](file://src/ws_ctx_engine/vector_index/vector_index.py#L1-L1122)
- [leann_index.py:1-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L1-L297)
- [embedding_cache.py:1-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L1-L127)
- [model_registry.py:1-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L1-L207)
- [backend_selector.py:1-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L1-L191)
- [indexer.py:1-493](file://src/ws_ctx_engine/workflow/indexer.py#L1-L493)
- [query.py:1-617](file://src/ws_ctx_engine/workflow/query.py#L1-L617)
- [retrieval.py:1-627](file://src/ws_ctx_engine/retrieval/retrieval.py#L1-L627)
- [config.py:1-399](file://src/ws_ctx_engine/config/config.py#L1-L399)
- [server.py:60-66](file://src/ws_ctx_engine/mcp/server.py#L60-L66)

**Section sources**
- [vector_index.py:1-1122](file://src/ws_ctx_engine/vector_index/vector_index.py#L1-L1122)
- [leann_index.py:1-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L1-L297)
- [embedding_cache.py:1-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L1-L127)
- [model_registry.py:1-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L1-L207)
- [backend_selector.py:1-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L1-L191)
- [indexer.py:1-493](file://src/ws_ctx_engine/workflow/indexer.py#L1-L493)
- [query.py:1-617](file://src/ws_ctx_engine/workflow/query.py#L1-L617)
- [retrieval.py:1-627](file://src/ws_ctx_engine/retrieval/retrieval.py#L1-L627)
- [config.py:1-399](file://src/ws_ctx_engine/config/config.py#L1-L399)

## Core Components
- VectorIndex abstract base class defining the interface for all backends.
- EmbeddingGenerator for local and API-based embedding generation with memory-aware fallback.
- ModelRegistry: Thread-safe singleton registry for embedding models with ONNX acceleration and automatic fallback.
- LEANNIndex: cosine similarity-based implementation with file-level grouping.
- NativeLEANNIndex: production-grade implementation using the LEANN library with 97% storage savings.
- FAISSIndex: FAISS-based implementation with IndexFlatL2 + IndexIDMap2 for exact search and incremental updates.
- EmbeddingCache: disk-backed cache for incremental indexing to avoid re-embedding unchanged content.
- BackendSelector: orchestrates backend selection and fallback chains.
- Workflow integration: indexer and query phases integrate vector indexing and retrieval.

**Updated** Added ModelRegistry with thread-safe singleton patterns, ONNX backend acceleration, and automatic fallback mechanisms.

**Section sources**
- [vector_index.py:21-1122](file://src/ws_ctx_engine/vector_index/vector_index.py#L21-L1122)
- [leann_index.py:20-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L20-L297)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)
- [model_registry.py:84-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L84-L207)
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)
- [indexer.py:72-493](file://src/ws_ctx_engine/workflow/indexer.py#L72-L493)
- [query.py:158-617](file://src/ws_ctx_engine/workflow/query.py#L158-L617)

## Architecture Overview
The vector index system provides a unified interface for semantic search with pluggable backends and automatic fallback. The backend selection prioritizes NativeLEANN (97% storage savings), falls back to LEANNIndex, and finally to FAISSIndex. Embedding generation supports local sentence-transformers models with API fallback to OpenAI. Incremental indexing uses an embedding cache to avoid re-embedding unchanged files.

**Updated** Enhanced with ModelRegistry thread-safe singleton patterns, ONNX backend acceleration, and background model pre-warming.

```mermaid
sequenceDiagram
participant User as "Caller"
participant Selector as "BackendSelector"
participant Factory as "create_vector_index"
participant Impl as "VectorIndex Impl"
participant Cache as "EmbeddingCache"
participant Registry as "ModelRegistry"
User->>Selector : select_vector_index(...)
Selector->>Factory : create_vector_index(backend, ...)
alt native-leann available
Factory->>Impl : NativeLEANNIndex(...)
Impl-->>Factory : instance
else leann available
Factory->>Impl : LEANNIndex(...)
Impl-->>Factory : instance
else faiss available
Factory->>Impl : FAISSIndex(...)
Impl-->>Factory : instance
else error
Factory-->>Selector : RuntimeError
Selector-->>User : error
end
Factory-->>Selector : VectorIndex instance
Selector-->>User : VectorIndex instance
User->>Impl : build(chunks, embedding_cache?)
alt embedding_cache provided
Impl->>Cache : lookup/lookup_many(...)
Cache-->>Impl : cached vectors or misses
Impl->>Registry : get_model(model_name, device)
Registry-->>Impl : cached/pre-warmed model
Impl->>Impl : encode(remaining texts)
Impl->>Cache : store(hash, vector)
else no cache
Impl->>Registry : get_model(model_name, device)
Registry-->>Impl : cached/pre-warmed model
Impl->>Impl : encode(all texts)
end
Impl-->>User : index ready
```

**Diagram sources**
- [backend_selector.py:36-81](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L36-L81)
- [vector_index.py:972-1080](file://src/ws_ctx_engine/vector_index/vector_index.py#L972-L1080)
- [indexer.py:189-234](file://src/ws_ctx_engine/workflow/indexer.py#L189-L234)
- [embedding_cache.py:89-113](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L89-L113)
- [model_registry.py:95-163](file://src/ws_ctx_engine/vector_index/model_registry.py#L95-L163)

**Section sources**
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)
- [vector_index.py:972-1080](file://src/ws_ctx_engine/vector_index/vector_index.py#L972-L1080)
- [indexer.py:189-234](file://src/ws_ctx_engine/workflow/indexer.py#L189-L234)
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)
- [model_registry.py:84-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L84-L207)

## Detailed Component Analysis

### VectorIndex Interface
VectorIndex defines the contract for all vector index implementations:
- build: construct the index from CodeChunk objects, optionally using an embedding cache.
- search: perform semantic similarity search and return file paths with similarity scores.
- save/load: persist and restore index state.
- get_file_symbols: return file-to-symbols mapping for downstream boosting.

Key behaviors:
- All implementations must handle empty inputs gracefully.
- Search validates query emptiness and index readiness.
- Save/load enforce index readiness and backend-specific metadata.

**Section sources**
- [vector_index.py:21-84](file://src/ws_ctx_engine/vector_index/vector_index.py#L21-L84)

### EmbeddingGenerator
EmbeddingGenerator encapsulates embedding generation with memory-aware fallback:
- Initializes sentence-transformers locally when sufficient memory is available.
- Falls back to OpenAI API embeddings when local model fails or memory is low.
- Uses configurable model name, device, and batch size.
- Tracks memory thresholds and logs fallback events.

**Updated** Now utilizes ModelRegistry for thread-safe model loading with ONNX acceleration and automatic fallback.

```mermaid
flowchart TD
Start(["encode(texts)"]) --> CheckLocal["Check local model init"]
CheckLocal --> |Not initialized| InitLocal["Init local model via ModelRegistry"]
InitLocal --> |Success & memory ok| LocalEncode["Local encode"]
InitLocal --> |ImportError/MemoryError| UseAPI["Set use_api=True"]
CheckLocal --> |Already initialized| CheckMem["Check memory"]
CheckMem --> |OK| LocalEncode
CheckMem --> |Low memory| UseAPI
LocalEncode --> |Success| ReturnLocal["Return embeddings"]
LocalEncode --> |MemoryError| UseAPI
UseAPI --> APICall["API encode"]
APICall --> ReturnAPI["Return embeddings"]
```

**Diagram sources**
- [vector_index.py:199-280](file://src/ws_ctx_engine/vector_index/vector_index.py#L199-L280)
- [model_registry.py:95-163](file://src/ws_ctx_engine/vector_index/model_registry.py#L95-L163)

**Section sources**
- [vector_index.py:96-280](file://src/ws_ctx_engine/vector_index/vector_index.py#L96-L280)
- [model_registry.py:84-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L84-L207)

### ModelRegistry (Enhanced Thread-Safe Singleton)
ModelRegistry provides thread-safe singleton caching for SentenceTransformer models with advanced features:
- Double-checked locking pattern ensures thread safety under concurrent access.
- Automatic ONNX backend detection and acceleration (~3x CPU speedup).
- Environment variable controls for model behavior and performance tuning.
- Background model pre-warming capability for reduced cold-start latency.
- Fork-safe design with automatic lock reset in child processes.

Key features:
- Thread-safe singleton with double-checked locking.
- Automatic ONNX backend detection when both onnxruntime and optimum are available.
- Memory guard prevents model loading when available RAM is below threshold.
- Environment variable controls: WSCTX_DISABLE_MODEL_PRELOAD, WSCTX_EMBEDDING_MODEL, WSCTX_DISABLE_ONNX, WSCTX_ENABLE_ONNX, WSCTX_MEMORY_THRESHOLD_MB.
- Background pre-warming support for MCP server initialization.

**New Section** Comprehensive documentation of the enhanced ModelRegistry component.

```mermaid
classDiagram
class ModelRegistry {
+dict cache
+Lock _lock
+get_model(model_name, device, backend) Any|None
+_load_model(model_name, device, backend) Any|None
+_onnx_available() bool
+_reinit_registry_after_fork() void
+clear() void
}
class EmbeddingGenerator {
+get_model(model_name, device) Any|None
+encode(texts) ndarray
+_init_local_model() bool
}
ModelRegistry --> EmbeddingGenerator : "used by"
```

**Diagram sources**
- [model_registry.py:84-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L84-L207)
- [vector_index.py:145-170](file://src/ws_ctx_engine/vector_index/vector_index.py#L145-L170)

**Section sources**
- [model_registry.py:1-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L1-L207)
- [vector_index.py:145-170](file://src/ws_ctx_engine/vector_index/vector_index.py#L145-L170)

### LEANNIndex (Cosine Similarity)
LEANNIndex groups chunks by file path, concatenates content per file, and computes embeddings. It stores file paths, embeddings, and symbol mappings. Search uses cosine similarity with normalized vectors.

Key implementation details:
- Groups chunks by path, concatenates content, and computes embeddings.
- Stores file → symbols mapping for symbol boost.
- Uses cosine similarity with L2 normalization and dot product.

```mermaid
classDiagram
class LEANNIndex {
+string model_name
+string device
+int batch_size
+EmbeddingGenerator _embedding_generator
+string[] _file_paths
+ndarray _embeddings
+dict~string, string[]~ _file_symbols
+build(chunks, embedding_cache)
+search(query, top_k)
+save(path)
+load(path)
+get_file_symbols()
+_cosine_similarity(query, embeddings)
}
class EmbeddingGenerator {
+encode(texts) ndarray
+_init_local_model() bool
+_encode_with_api(texts) ndarray
}
LEANNIndex --> EmbeddingGenerator : "uses"
```

**Diagram sources**
- [vector_index.py:282-504](file://src/ws_ctx_engine/vector_index/vector_index.py#L282-L504)

**Section sources**
- [vector_index.py:282-504](file://src/ws_ctx_engine/vector_index/vector_index.py#L282-L504)

### NativeLEANNIndex (97% Storage Savings)
NativeLEANNIndex uses the actual LEANN library to achieve 97% storage savings via graph-based selective recomputation. It stores index metadata and relies on the LEANN library for index construction and search.

Key features:
- Integrates with the LEANN library (LeannBuilder/LeannSearcher).
- Supports HNSW and DiskANN backends.
- Persists index metadata and file-to-symbols mapping.

```mermaid
classDiagram
class NativeLEANNIndex {
+string index_path
+string backend
+int chunk_size
+int overlap
+string[] _file_paths
+dict~string, string[]~ _file_symbols
+build(chunks)
+search(query, top_k)
+save(path)
+load(path)
+get_file_symbols()
}
```

**Diagram sources**
- [leann_index.py:20-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L20-L297)

**Section sources**
- [leann_index.py:20-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L20-L297)

### FAISSIndex (FAISS-CPU)
FAISSIndex uses FAISS with IndexFlatL2 wrapped in IndexIDMap2 for exact search and incremental updates. It supports:
- IndexFlatL2 for brute-force exact search.
- IndexIDMap2 for ID mapping and incremental removal/addition.
- Incremental update via remove_ids + add_with_ids with monotonic ID assignment.

```mermaid
classDiagram
class FAISSIndex {
+string model_name
+string device
+int batch_size
+EmbeddingGenerator _embedding_generator
+string[] _file_paths
+dict~int, string~ _id_to_path
+int _next_id
+Any _index
+int _embedding_dim
+dict~string, string[]~ _file_symbols
+build(chunks, embedding_cache)
+search(query, top_k)
+save(path)
+load(path)
+update_incremental(deleted_paths, new_chunks, embedding_cache)
+_ensure_idmap2()
+get_file_symbols()
}
```

**Diagram sources**
- [vector_index.py:506-962](file://src/ws_ctx_engine/vector_index/vector_index.py#L506-L962)

**Section sources**
- [vector_index.py:506-962](file://src/ws_ctx_engine/vector_index/vector_index.py#L506-L962)

### EmbeddingCache (Incremental Indexing)
EmbeddingCache provides disk-backed caching of content-hash → embedding vector mappings:
- Uses SHA-256 of concatenated file content as the key.
- Persists embeddings.npy and embedding_index.json.
- Supports lookup, store, load, and save operations.
- Enables incremental rebuilds by skipping unchanged files.

```mermaid
flowchart TD
Start(["Incremental Build"]) --> Group["Group new chunks by file"]
Group --> ForEach["For each file"]
ForEach --> Hash["content_hash(text)"]
Hash --> Lookup{"Cache hit?"}
Lookup --> |Yes| UseCached["Use cached vector"]
Lookup --> |No| Encode["Encode text"]
Encode --> Store["Store in cache"]
UseCached --> Next["Next file"]
Store --> Next
Next --> Done(["Build index with cached vectors"])
```

**Diagram sources**
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)
- [vector_index.py:539-562](file://src/ws_ctx_engine/vector_index/vector_index.py#L539-L562)

**Section sources**
- [embedding_cache.py:28-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L28-L127)
- [vector_index.py:539-562](file://src/ws_ctx_engine/vector_index/vector_index.py#L539-L562)

### Backend Selection Strategy
BackendSelector implements graceful degradation:
- Level 1: igraph + NativeLEANN + local embeddings (optimal, 97% storage savings).
- Level 2: NetworkX + NativeLEANN + local embeddings.
- Level 3: NetworkX + LEANNIndex + local embeddings.
- Level 4: NetworkX + FAISS + local embeddings.
- Level 5: NetworkX + FAISS + API embeddings.
- Level 6: File size ranking only (no graph).

It selects backends based on configuration and logs the current fallback level.

```mermaid
flowchart TD
Start(["select_vector_index"]) --> ReadCfg["Read config.backends.vector_index"]
ReadCfg --> TryNative["Try NativeLEANN"]
TryNative --> |Success| ReturnNative["Return NativeLEANNIndex"]
TryNative --> |Fail| TryLEANN["Try LEANNIndex"]
TryLEANN --> |Success| ReturnLEANN["Return LEANNIndex"]
TryLEANN --> |Fail| TryFAISS["Try FAISSIndex"]
TryFAISS --> |Success| ReturnFAISS["Return FAISSIndex"]
TryFAISS --> |Fail| Error["Raise RuntimeError"]
```

**Diagram sources**
- [backend_selector.py:36-81](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L36-L81)
- [vector_index.py:972-1080](file://src/ws_ctx_engine/vector_index/vector_index.py#L972-L1080)

**Section sources**
- [backend_selector.py:13-191](file://src/ws_ctx_engine/backend_selector/backend_selector.py#L13-L191)
- [vector_index.py:972-1080](file://src/ws_ctx_engine/vector_index/vector_index.py#L972-L1080)

### Integration with Retrieval System
The retrieval system combines semantic and structural signals:
- Semantic scores from vector_index.search.
- PageRank scores from RepoMapGraph.
- Symbol boost, path boost, domain boost, and test penalty.
- Min-max normalization to [0, 1].

```mermaid
sequenceDiagram
participant User as "Caller"
participant Engine as "RetrievalEngine"
participant Vec as "VectorIndex"
participant Graph as "RepoMapGraph"
User->>Engine : retrieve(query, changed_files, top_k)
Engine->>Vec : search(query, top_k)
Vec-->>Engine : semantic_results
Engine->>Graph : pagerank(changed_files)
Graph-->>Engine : pagerank_scores
Engine->>Engine : normalize + merge scores
Engine->>Engine : apply symbol/path/domain/test signals
Engine-->>User : ranked_files
```

**Diagram sources**
- [retrieval.py:250-368](file://src/ws_ctx_engine/retrieval/retrieval.py#L250-L368)
- [vector_index.py:43-56](file://src/ws_ctx_engine/vector_index/vector_index.py#L43-L56)

**Section sources**
- [retrieval.py:140-368](file://src/ws_ctx_engine/retrieval/retrieval.py#L140-L368)
- [vector_index.py:43-56](file://src/ws_ctx_engine/vector_index/vector_index.py#L43-L56)

### Background Model Pre-Warming
The MCP server includes background model pre-warming to eliminate cold-start latency:
- Pre-warms the default model during server initialization.
- Best-effort approach with graceful error handling.
- Reduces first-query latency from 6-8 seconds to sub-second response times.

**New Section** Documentation of background model pre-warming mechanism.

**Section sources**
- [server.py:60-66](file://src/ws_ctx_engine/mcp/server.py#L60-L66)
- [model_registry.py:189-193](file://src/ws_ctx_engine/vector_index/model_registry.py#L189-L193)

## Dependency Analysis
- Internal dependencies:
  - VectorIndex implementations depend on EmbeddingGenerator and CodeChunk.
  - FAISSIndex depends on FAISS library for index operations.
  - NativeLEANNIndex depends on the LEANN library for index construction/search.
  - EmbeddingGenerator depends on ModelRegistry for thread-safe model management.
- External dependencies:
  - numpy for array operations.
  - psutil for memory checks.
  - sentence-transformers for local embeddings.
  - faiss-cpu for FAISS backend.
  - leann for NativeLEANN backend.
  - openai for API fallback.
  - onnxruntime and optimum for ONNX backend acceleration.
  - threading for thread-safe singleton patterns.

**Updated** Added onnxruntime and optimum dependencies for ONNX backend acceleration.

```mermaid
graph TB
VI["vector_index.py"] --> ST["sentence-transformers"]
VI --> FAISS["faiss-cpu"]
VI --> NP["numpy"]
VI --> PS["psutil"]
LEANN["leann_index.py"] --> LEANNLIB["leann"]
QRY["workflow/query.py"] --> RET["retrieval/retrieval.py"]
IDX["workflow/indexer.py"] --> VI
IDX --> LEANN
CFG["config/config.py"] --> BS["backend_selector.py"]
BS --> VI
BS --> LEANN
REG["model_registry.py"] --> ST
REG --> ORT["onnxruntime"]
REG --> OPT["optimum"]
MCP["mcp/server.py"] --> REG
```

**Diagram sources**
- [vector_index.py:1-1122](file://src/ws_ctx_engine/vector_index/vector_index.py#L1-L1122)
- [leann_index.py:1-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L1-L297)
- [indexer.py:1-493](file://src/ws_ctx_engine/workflow/indexer.py#L1-L493)
- [query.py:1-617](file://src/ws_ctx_engine/workflow/query.py#L1-L617)
- [config.py:1-399](file://src/ws_ctx_engine/config/config.py#L1-L399)
- [model_registry.py:36-48](file://src/ws_ctx_engine/vector_index/model_registry.py#L36-L48)
- [server.py:60-66](file://src/ws_ctx_engine/mcp/server.py#L60-L66)

**Section sources**
- [vector_index.py:1-1122](file://src/ws_ctx_engine/vector_index/vector_index.py#L1-L1122)
- [leann_index.py:1-297](file://src/ws_ctx_engine/vector_index/leann_index.py#L1-L297)
- [indexer.py:1-493](file://src/ws_ctx_engine/workflow/indexer.py#L1-L493)
- [query.py:1-617](file://src/ws_ctx_engine/workflow/query.py#L1-L617)
- [config.py:1-399](file://src/ws_ctx_engine/config/config.py#L1-L399)
- [model_registry.py:1-207](file://src/ws_ctx_engine/vector_index/model_registry.py#L1-L207)

## Performance Considerations
- Backend latency targets:
  - NativeLEANN: <10ms (1k), <50ms (10k), <200ms (100k).
  - LEANNIndex: <5ms (1k), <20ms (10k), <100ms (100k).
  - FAISSIndex (HNSW): <1ms (1k), <5ms (10k), <20ms (100k).
- Memory usage:
  - NativeLEANN: ~3MB (97% savings).
  - LEANNIndex: ~15MB.
  - FAISSIndex: ~20MB (384-dim, 10k files).
- Embedding dimensions:
  - all-MiniLM-L6-v2: 384 dimensions.
- Optional Rust acceleration:
  - File walking, gitignore matching, chunk hashing, and token counting can be accelerated by 8–20x with the Rust extension.
- Model loading performance:
  - Thread-safe singleton eliminates cold-start penalty (6-8 seconds reduced to sub-second).
  - ONNX backend provides ~3x CPU encoding speedup.
  - Background pre-warming further reduces first-query latency.

**Updated** Added performance improvements from ModelRegistry enhancements and ONNX acceleration.

**Section sources**
- [vector-index.md:402-419](file://docs/reference/vector-index.md#L402-L419)
- [performance.md:8-16](file://docs/guides/performance.md#L8-L16)
- [MCP_PERFORMANCE_OPTIMIZATION.md:1087-1124](file://docs/performance/MCP_PERFORMANCE_OPTIMIZATION.md#L1087-L1124)

## Troubleshooting Guide
Common issues and resolutions:
- Local model initialization failures:
  - Insufficient memory triggers API fallback.
  - ImportError for sentence-transformers leads to API fallback.
  - ModelRegistry memory threshold prevents loading when RAM is below WSCTX_MEMORY_THRESHOLD_MB.
- FAISS not available:
  - Install faiss-cpu; otherwise, fallback to LEANNIndex.
- NativeLEANN not available:
  - Install leann or leann extras; otherwise, fallback to LEANNIndex.
- Out of memory during encoding:
  - EmbeddingGenerator frees memory and switches to API fallback.
  - ModelRegistry memory guard prevents model loading when RAM is low.
- Incremental update failures:
  - Index rebuild is attempted; ensure embedding cache is enabled and persisted.
- ONNX backend issues:
  - Missing onnxruntime or optimum packages prevent ONNX acceleration.
  - Set WSCTX_DISABLE_ONNX=1 to force PyTorch backend.
- Thread safety concerns:
  - ModelRegistry uses double-checked locking to prevent race conditions.
  - Fork-safe design resets locks and cache in child processes.

**Updated** Added troubleshooting guidance for ModelRegistry and ONNX backend issues.

**Section sources**
- [vector_index.py:130-280](file://src/ws_ctx_engine/vector_index/vector_index.py#L130-L280)
- [vector_index.py:564-646](file://src/ws_ctx_engine/vector_index/vector_index.py#L564-L646)
- [vector_index.py:1011-1076](file://src/ws_ctx_engine/vector_index/vector_index.py#L1011-L1076)
- [indexer.py:210-230](file://src/ws_ctx_engine/workflow/indexer.py#L210-L230)
- [model_registry.py:130-141](file://src/ws_ctx_engine/vector_index/model_registry.py#L130-L141)
- [model_registry.py:122-128](file://src/ws_ctx_engine/vector_index/model_registry.py#L122-L128)

## Conclusion
The vector index system provides a robust, configurable, and scalable foundation for semantic search over codebases. It balances performance and storage efficiency through multiple backends, memory-aware embedding generation, and incremental indexing with embedding caching. The retrieval system integrates semantic and structural signals to produce high-quality ranked results suitable for downstream packing and output generation.

**Updated** Enhanced with ModelRegistry thread-safe singleton patterns, ONNX backend acceleration, automatic fallback mechanisms, and background model pre-warming capabilities that significantly improve performance and reliability.

## Appendices

### Configuration Examples
- Backend selection:
  - vector_index.backend: auto | native-leann | leann | faiss
  - embeddings.model/device/batch_size: configure embedding generation
  - performance.cache_embeddings/incremental_index: enable caching and incremental builds
- ModelRegistry environment variables:
  - WSCTX_DISABLE_MODEL_PRELOAD: bypass caching (useful for testing)
  - WSCTX_EMBEDDING_MODEL: override model name regardless of request
  - WSCTX_DISABLE_ONNX: force PyTorch backend even when ONNX available
  - WSCTX_ENABLE_ONNX: legacy opt-in flag for ONNX backend
  - WSCTX_MEMORY_THRESHOLD_MB: minimum available RAM for model loading
- Example YAML:
  - See [vector-index.md:482-508](file://docs/reference/vector-index.md#L482-L508) for a complete configuration example.

**Updated** Added ModelRegistry environment variable configuration options.

**Section sources**
- [config.py:74-101](file://src/ws_ctx_engine/config/config.py#L74-L101)
- [vector-index.md:482-508](file://docs/reference/vector-index.md#L482-L508)
- [model_registry.py:7-29](file://src/ws_ctx_engine/vector_index/model_registry.py#L7-L29)

### Scaling Considerations
- Choose backends based on repository size:
  - NativeLEANNIndex: optimal for large repositories with tight storage budgets.
  - FAISSIndex: best for fastest search performance with moderate storage overhead.
  - LEANNIndex: balanced option with cosine similarity and full embedding storage.
- Enable embedding cache for incremental builds to reduce rebuild time.
- Monitor memory usage and adjust batch sizes accordingly.
- Leverage ModelRegistry thread-safe singleton for concurrent model access.
- Utilize ONNX backend acceleration for improved CPU encoding performance.
- Implement background model pre-warming for MCP servers to eliminate cold-start latency.

**Updated** Added scaling considerations for ModelRegistry enhancements and ONNX acceleration.

**Section sources**
- [vector-index.md:295-302](file://docs/reference/vector-index.md#L295-L302)
- [vector-index.md:406-418](file://docs/reference/vector-index.md#L406-L418)
- [MCP_PERFORMANCE_OPTIMIZATION.md:1087-1124](file://docs/performance/MCP_PERFORMANCE_OPTIMIZATION.md#L1087-L1124)

### Embedding Cache Management
- Persist cache under .ws-ctx-engine/embeddings.npy and embedding_index.json.
- Use content_hash to ensure cache invalidation on content changes.
- Load cache before building and save after incremental updates.

**Section sources**
- [embedding_cache.py:1-127](file://src/ws_ctx_engine/vector_index/embedding_cache.py#L1-L127)
- [indexer.py:197-237](file://src/ws_ctx_engine/workflow/indexer.py#L197-L237)

### Precomputation Strategies
- Group chunks by file path and concatenate content per file before embedding.
- Use embedding cache to avoid re-embedding unchanged files.
- For FAISSIndex, leverage IndexIDMap2 for incremental removal/addition with monotonic ID assignment.
- Utilize ModelRegistry thread-safe singleton for efficient model reuse across precomputation tasks.

**Updated** Added ModelRegistry utilization for efficient model reuse in precomputation.

**Section sources**
- [vector_index.py:330-359](file://src/ws_ctx_engine/vector_index/vector_index.py#L330-L359)
- [vector_index.py:914-953](file://src/ws_ctx_engine/vector_index/vector_index.py#L914-L953)
- [model_registry.py:95-163](file://src/ws_ctx_engine/vector_index/model_registry.py#L95-L163)

### Integration with Retrieval System
- VectorIndex.search feeds semantic scores to RetrievalEngine.
- get_file_symbols enables symbol-based boosting.
- RetrievalEngine merges semantic and PageRank scores, applies additional signals, and normalizes results.

**Section sources**
- [retrieval.py:250-368](file://src/ws_ctx_engine/retrieval/retrieval.py#L250-L368)
- [vector_index.py:86-93](file://src/ws_ctx_engine/vector_index/vector_index.py#L86-L93)

### ModelRegistry Environment Variables
The ModelRegistry supports comprehensive environment variable controls:

- WSCTX_DISABLE_MODEL_PRELOAD: Set to "1" to bypass caching (useful for testing or memory-constrained environments). Each get_model() call creates a fresh instance.
- WSCTX_EMBEDDING_MODEL: Override the model name regardless of what was requested. Example: "nomic-embed-text-v1.5".
- WSCTX_DISABLE_ONNX: Set to "1" to force the default PyTorch backend even when onnxruntime is installed. By default the registry auto-detects onnxruntime and uses it for ~3x CPU encoding speedup.
- WSCTX_ENABLE_ONNX: Legacy opt-in flag, still honored. Prefer WSCTX_DISABLE_ONNX=1 to turn ONNX off when auto-detection is undesired.
- WSCTX_MEMORY_THRESHOLD_MB: Minimum available RAM in MB required before loading a model (default 500). If available RAM is below this threshold, get_model() returns None.

**New Section** Complete documentation of ModelRegistry environment variable controls.

**Section sources**
- [model_registry.py:7-29](file://src/ws_ctx_engine/vector_index/model_registry.py#L7-L29)
- [MCP_PERFORMANCE_OPTIMIZATION.md:1107-1121](file://docs/performance/MCP_PERFORMANCE_OPTIMIZATION.md#L1107-L1121)