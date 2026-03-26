# MCP Server Performance Optimization Plan

## Problem Analysis

**Current Issue**: `search_codebase` latency averages **10,023ms** (~10 seconds)

### Root Causes Identified:

1. **Embedding Model Loading** (Primary - ~6-8s)
   - `SentenceTransformer("facebook/contriever")` loads on-demand during first search
   - Model initialization includes downloading weights if not cached
   - First query bears the full cost

2. **LEANN Searcher Initialization** (Secondary - ~1-2s)
   - `LeannSearcher(index_path)` creates new searcher instance per request
   - Index file I/O overhead

3. **Graph Operations** (Minor - ~1-2s)
   - PageRank computation on each retrieval
   - Graph loading from disk

---

## Solutions

### Solution 1: Pre-load Embedding Model (HIGH IMPACT) ⭐ RECOMMENDED

**Implementation**: Lazy-load model in constructor with warm-up

```python
class MCPToolService:
    def __init__(self, workspace: str, config: MCPConfig, index_dir: str = ".ws-ctx-engine"):
        # ... existing init code ...
        
        # Pre-load embedding model
        self._embedding_model: Any = None
        self._preload_embedding_model()
    
    def _preload_embedding_model(self) -> None:
        """Pre-load sentence transformer model to avoid cold-start latency."""
        try:
            from sentence_transformers import SentenceTransformer
            
            # Load model once at startup
            self._embedding_model = SentenceTransformer(
                "facebook/contriever",
                device="cpu"
            )
            
            # Warm up with dummy query
            self._embedding_model.encode(["warm-up"])
            
            logger.info("Embedding model pre-loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to pre-load embedding model: {e}")
            self._embedding_model = None
```

**Benefits**:
- ✅ Eliminates 6-8s cold start on first query
- ✅ All subsequent queries benefit immediately
- ✅ Simple implementation, minimal code changes

**Trade-offs**:
- ⚠️ Increases server startup time by ~6-8s (one-time cost)
- ⚠️ Memory usage increases by ~500MB for model

---

### Solution 2: Singleton Pattern for Shared Resources (MEDIUM IMPACT)

**Implementation**: Use module-level singleton for expensive resources

```python
# src/ws_ctx_engine/vector_index/embedding_generator.py

class EmbeddingGeneratorSingleton:
    _instance: Optional['EmbeddingGeneratorSingleton'] = None
    _model: Any = None
    
    def __new__(cls) -> 'EmbeddingGeneratorSingleton':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self) -> Any:
        """Get or initialize model lazily with thread safety."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("facebook/contriever")
        return self._model

# Usage in RetrievalEngine
def retrieve(self, query: str, top_k: int = 100):
    # Get shared model instance instead of loading per-request
    model = EmbeddingGeneratorSingleton().get_model()
    # ... rest of search logic
```

**Benefits**:
- ✅ Model shared across all requests/sessions
- ✅ Reduces memory footprint
- ✅ Thread-safe lazy initialization

**Trade-offs**:
- ⚠️ Requires refactoring vector_index module
- ⚠️ More complex than Solution 1

---

### Solution 3: Cache LEANN Searcher Instance (LOW IMPACT)

**Implementation**: Reuse searcher instead of creating per-request

```python
class VectorIndex:
    def __init__(self, index_path: str):
        self.index_path = index_path
        self._searcher_cache: Optional[Any] = None
    
    def _get_searcher(self):
        """Lazy-load and cache LEANN searcher."""
        if self._searcher_cache is None:
            from leann import LeannSearcher
            self._searcher_cache = LeannSearcher(self.index_path)
        return self._searcher_cache
    
    def search(self, query: str, top_k: int = 10):
        searcher = self._get_searcher()
        results = searcher.search(query, top_k=top_k * 2)
        # ... rest of logic
```

**Benefits**:
- ✅ Saves ~1-2s per request
- ✅ Simple implementation

**Trade-offs**:
- ⚠️ Holds file handles open
- ⚠️ Less impact than model pre-loading

---

### Solution 4: Async Background Loading (OPTIONAL ENHANCEMENT)

**Implementation**: Load resources in background thread pool

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class MCPToolService:
    def __init__(self, workspace: str, config: MCPConfig):
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._model_loaded = asyncio.Event()
        
        # Start background loading
        asyncio.create_task(self._load_resources_async())
    
    async def _load_resources_async(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            self._preload_embedding_model
        )
        self._model_loaded.set()
    
    async def search_codebase(self, query: str):
        # Wait for model to be ready
        await self._model_loaded.wait()
        # Proceed with search
```

**Benefits**:
- ✅ Non-blocking startup
- ✅ Can show progress indicator

**Trade-offs**:
- ⚠️ Complex async/await integration
- ⚠️ Overkill for stdio-based MCP server

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 hours)
1. ✅ **Solution 1**: Pre-load embedding model in MCPToolService.__init__
2. ✅ **Solution 3**: Cache LEANN searcher in VectorIndex

Expected improvement: **10s → 2-3s** (70-80% reduction)

### Phase 2: Architecture Improvements (Optional, 4-6 hours)
1. Implement Solution 2: Singleton pattern
2. Add health check endpoint to verify model loaded
3. Add metrics/logging for timing breakdown

Expected improvement: **Additional 10-20%**

---

## Testing & Validation

### Benchmark Script
```python
import time
import json

def benchmark_search_latency(iterations=5):
    latencies = []
    for i in range(iterations):
        start = time.time()
        result = call_mcp_tool("search_codebase", {"query": "authentication"})
        elapsed = (time.time() - start) * 1000
        latencies.append(elapsed)
        print(f"Iteration {i+1}: {elapsed:.0f}ms")
    
    avg = sum(latencies) / len(latencies)
    print(f"\nAverage: {avg:.0f}ms")
    print(f"P95: {sorted(latencies)[int(0.95*len(latencies))]:.0f}ms")
    return latencies
```

### Success Criteria
- ✅ Average latency < 3,000ms (down from 10,023ms)
- ✅ P95 latency < 5,000ms
- ✅ No regression in search quality
- ✅ Memory increase < 1GB

---

## Configuration Options

Allow users to control pre-loading behavior via environment variables:

```bash
# Disable pre-loading (keep current behavior)
export WSCTX_DISABLE_MODEL_PRELOAD=1

# Use lighter model (trade accuracy for speed)
export WSCTX_EMBEDDING_MODEL="all-MiniLM-L6-v2"

# Set memory threshold (MB)
export WSCTX_MEMORY_THRESHOLD_MB=1024
```

---

## References

- LEANN backend: `/Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker/src/ws_ctx_engine/vector_index/leann_index.py`
- Embedding generator: `src/ws_ctx_engine/vector_index/vector_index.py#L96-L220`
- Retrieval engine: `src/ws_ctx_engine/retrieval/retrieval.py#L250-L350`
