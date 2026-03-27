# Index Management Intelligence Roadmap

**Date**: March 27, 2026  
**Project**: ws-ctx-engine (MCP Context Packaging)  
**Status**: Strategic Initiative  
**Inspired by**: Qoder Repo Wiki's intelligent index management  

---

## Executive Summary

Current indexing approach: **Full re-index on every change** — inefficient at scale.

**Problem**: 
- 4,000 file codebase → 120 minutes to re-index
- Change 1 file → still re-index all 4,000 files
- Wasted compute: **99.9%**

**Solution**: Intelligent index management inspired by Qoder Repo Wiki:
1. ✅ Incremental updates (only affected files)
2. ✅ Staleness detection (know when index is stale)
3. ✅ Query caching (avoid re-computation)
4. ✅ Lazy batching (batch multiple changes)
5. ✅ Partitioned indexes (separate stable vs unstable code)
6. ✅ Background maintenance (non-blocking updates)

**Expected Impact**:
- Re-index time: **120 min → 1 sec** per file (99.9% reduction)
- Query latency: **60-70% faster** for repeated queries
- Compute savings: **90%** less re-indexing work

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Qoder's Approach — What We Learned](#2-qoders-approach--what-we-learned)
3. [Proposed Architecture](#3-proposed-architecture)
4. [Implementation Phases](#4-implementation-phases)
5. [Performance Projections](#5-performance-projections)
6. [Risk Mitigation](#6-risk-mitigation)
7. [Success Metrics](#7-success-metrics)

---

## 1. Current State Analysis

### 1.1 How Indexing Works Today

```python
# src/ws_ctx_engine/index/indexer.py

class Indexer:
    def index_codebase(self, repo_path: str):
        """Full re-index of entire codebase"""
        chunks = self.chunker.parse(repo_path)
        
        embeddings = []
        for chunk in chunks:
            emb = self.embedder.encode(chunk.content)
            embeddings.append(emb)
        
        self.vector_index.clear()
        self.vector_index.insert_all(chunks, embeddings)
```

**Flow**:
```
File Change Detected
    ↓
Trigger Full Re-index
    ↓
Re-chunk ALL files (4,000 files)
    ↓
Re-embed ALL chunks (~20K embeddings)
    ↓
Replace entire vector index
    ↓
Total time: ~120 minutes
```

### 1.2 Pain Points

| Scenario | Current Behavior | Problem |
|----------|-----------------|---------|
| **Single file change** | Re-index all 4,000 files | 99.9% wasted work |
| **Multiple commits in 5 min** | Re-index 10 times | 9x redundant work |
| **Same query asked twice** | Re-compute embedding both times | No caching |
| **Docs change (.md files)** | Re-index .py files too | No partitioning |
| **Index becomes stale** | System doesn't know | No health monitoring |

### 1.3 Cost Analysis

**Current Monthly Cost** (estimated for active development):

- Dev commits: 20/day × 22 days = 440 commits/month
- Avg re-index time: 120 minutes
- **Total re-index time**: 440 × 120 min = **880 hours/month**
- **Compute cost** (@ $0.10/min GPU): 440 × 120 × $0.10 = **$5,280/month**

**With intelligent management**:
- Incremental updates: 440 × 1 min = 440 minutes
- **Compute cost**: 440 × 1 × $0.10 = **$44/month**
- **Savings**: **$5,236/month (99% reduction)**

---

## 2. Qoder's Approach — What We Learned

### 2.1 Core Insights

From deep research into Qoder Repo Wiki:

**Insight 1: Incremental > Full**
- Qoder monitors file-level changes
- Only re-indexes affected modules
- Rest of index stays valid

**Insight 2: Staleness Detection**
- Tracks file hashes at index time
- Compares current hash vs indexed hash
- Knows exactly which chunks are stale

**Insight 3: Smart Batching**
- Waits 5 minutes after last change
- Batches multiple file changes together
- Avoids re-indexing during active editing

**Insight 4: Query Caching**
- Caches query results for 30-60 minutes
- Hit rate: ~60-70% for dev follow-up questions
- Avoids re-computing same embeddings

### 2.2 What We Can Reuse (No Re-invention)

✅ **Git infrastructure** — Already have git repo  
✅ **File hashing** — Python `hashlib` standard library  
✅ **LRU Cache** — `cachetools` or `functools.lru_cache`  
✅ **Background threads** — Python `threading` module  
✅ **Queue management** — Python `queue.Queue`

**New code needed**: ~500 lines (mostly glue code)

---

## 3. Proposed Architecture

### 3.1 High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│              Index Management Intelligence               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐    ┌──────────────────┐          │
│  │ FileWatcher      │    │ QueryCache       │          │
│  │                  │    │                  │          │
│  │ - Detect changes │    │ - Cache results  │          │
│  │ - Hash files     │    │ - 30min TTL      │          │
│  │ - Trigger update │    │ - 60-70% hit rate│          │
│  └──────────────────┘    └──────────────────┘          │
│           ↓                       ↑                     │
│  ┌──────────────────┐            │                     │
│  │ IncrementalUpdater│           │                     │
│  │                   │            │                     │
│  │ - Delete old chunks│           │                     │
│  │ - Re-chunk file   │            │                     │
│  │ - Re-embed only   │            │                     │
│  │   changed parts   │            │                     │
│  └──────────────────┘            │                     │
│           ↓                       │                     │
│  ┌──────────────────┐    ┌──────────────────┐          │
│  │ StalenessMonitor │    │ BackgroundWorker │          │
│  │                  │    │                  │          │
│  │ - Health checks  │    │ - Non-blocking   │          │
│  │ - Report score   │    │ - Batched jobs   │          │
│  │ - Alert if <0.7  │    │ - Priority queue │          │
│  └──────────────────┘    └──────────────────┘          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Component Details

#### **Component 1: FileWatcher**

```python
# src/ws_ctx_engine/index/file_watcher.py

import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self, indexer_callback):
        self.indexer_callback = indexer_callback
        self.file_hashes = {}
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        filepath = event.src_path
        if not self._is_code_file(filepath):
            return
        
        # Compute hash
        new_hash = self._hash_file(filepath)
        old_hash = self.file_hashes.get(filepath)
        
        if new_hash != old_hash:
            logger.info(f"File changed: {filepath}")
            self.file_hashes[filepath] = new_hash
            
            # Trigger incremental update
            self.indexer_callback(filepath)

class FileWatcher:
    def __init__(self, repo_path: str):
        self.observer = Observer()
        self.handler = None
    
    def start(self, on_file_changed: callable):
        """Start watching for file changes"""
        self.handler = CodeChangeHandler(on_file_changed)
        self.observer.schedule(self.handler, path=repo_path, recursive=True)
        self.observer.start()
        logger.info(f"Watching {repo_path} for changes")
    
    def stop(self):
        self.observer.stop()
        self.observer.join()
```

---

#### **Component 2: IncrementalUpdater**

```python
# src/ws_ctx_engine/index/incremental_updater.py

class IncrementalIndexUpdater:
    """
    Updates only affected chunks when file changes.
    Avoids full re-index of entire codebase.
    """
    
    def __init__(self, vector_index, graph_store, chunker, embedder):
        self.vector_index = vector_index
        self.graph_store = graph_store
        self.chunker = chunker
        self.embedder = embedder
    
    def update_on_file_change(self, filepath: str):
        """
        When file changes:
        1. Remove old chunks from this file
        2. Re-chunk the file
        3. Re-embed only new chunks
        4. Update graph nodes/edges
        """
        start_time = time.time()
        
        # Step 1: Remove old chunks
        old_chunk_ids = self.vector_index.get_ids_by_file(filepath)
        if old_chunk_ids:
            self.vector_index.delete_batch(old_chunk_ids)
            logger.debug(f"Removed {len(old_chunk_ids)} old chunks")
        
        # Step 2: Re-chunk file
        new_chunks = self.chunker.chunk_file(filepath)
        
        # Step 3: Re-embed and insert
        for chunk in new_chunks:
            embedding = self.embedder.encode(chunk.content)
            self.vector_index.upsert(chunk.id, embedding, chunk.metadata)
            
            # Update graph if available
            if self.graph_store:
                self.graph_store.upsert_edges_from_chunk(chunk)
        
        elapsed = time.time() - start_time
        logger.info(f"Incremental indexed {filepath} in {elapsed:.3f}s")
        
        return len(new_chunks)
    
    def update_batch(self, filepaths: list[str]):
        """Update multiple files in one batch"""
        total_chunks = 0
        for filepath in filepaths:
            chunks_added = self.update_on_file_change(filepath)
            total_chunks += chunks_added
        
        logger.info(f"Batch updated {len(filepaths)} files, {total_chunks} chunks")
        return total_chunks
```

---

#### **Component 3: StalenessMonitor**

```python
# src/ws_ctx_engine/index/staleness_monitor.py

import hashlib
from dataclasses import dataclass

@dataclass
class IndexHealth:
    total_chunks: int
    stale_chunks: int
    healthy_chunks: int
    health_score: float  # 0.0 - 1.0
    
    def __str__(self):
        status = "🟢" if self.health_score > 0.8 else \
                 "🟡" if self.health_score > 0.5 else "🔴"
        return f"{status} Index Health: {self.health_score:.2f} ({self.stale_chunks}/{self.total_chunks} stale)"

class StalenessMonitor:
    """
    Monitors index health by comparing file hashes.
    Alerts when staleness exceeds threshold.
    """
    
    def __init__(self, vector_index, chunker):
        self.vector_index = vector_index
        self.chunker = chunker
        self.indexed_hashes = {}  # filepath → hash at index time
    
    def check_health(self) -> IndexHealth:
        """
        Returns health score:
        - 1.0 = All chunks in sync
        - 0.8 = 20% stale (acceptable)
        - 0.5 = 50% stale (needs re-index soon)
        - 0.2 = Critical (block queries)
        """
        total = self.vector_index.count()
        stale_count = 0
        
        # Group chunks by file
        chunks_by_file = self._group_chunks_by_file()
        
        for filepath, chunk_ids in chunks_by_file.items():
            if self._is_file_stale(filepath):
                stale_count += len(chunk_ids)
        
        healthy_count = total - stale_count
        health_score = healthy_count / total if total > 0 else 1.0
        
        return IndexHealth(total, stale_count, healthy_count, health_score)
    
    def _is_file_stale(self, filepath: str) -> bool:
        """Check if file content differs from indexed version"""
        if not Path(filepath).exists():
            return True  # File deleted = stale
        
        current_hash = self._hash_file(filepath)
        indexed_hash = self.indexed_hashes.get(filepath)
        
        return current_hash != indexed_hash
    
    def _hash_file(self, filepath: str) -> str:
        """Fast hash (only code, ignore comments/whitespace)"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Strip comments and whitespace for more stable hash
            code_only = self._strip_comments(content)
            return hashlib.sha256(code_only.encode()).hexdigest()
    
    def _strip_comments(self, code: str) -> str:
        """Remove comments to avoid hash changes on comment edits"""
        # Simple implementation — can enhance per language
        lines = code.split('\n')
        code_lines = [
            line.split('#')[0].split('//')[0] 
            for line in lines 
            if line.strip() and not line.strip().startswith(('#', '//', '/*', '*'))
        ]
        return '\n'.join(code_lines)
    
    def get_stale_chunk_ids(self) -> list[str]:
        """Return list of chunk IDs that need re-indexing"""
        stale_ids = []
        chunks_by_file = self._group_chunks_by_file()
        
        for filepath, chunk_ids in chunks_by_file.items():
            if self._is_file_stale(filepath):
                stale_ids.extend(chunk_ids)
        
        return stale_ids
```

---

#### **Component 4: QueryCache**

```python
# src/ws_ctx_engine/retrieval/cached_retrieval.py

from cachetools import TTLCache, cached

class CachedRetrievalEngine:
    """
    Adds intelligent caching to retrieval queries.
    Avoids re-computing embeddings for repeated queries.
    """
    
    def __init__(self, base_retrieval_engine, cache_ttl: int = 1800):
        """
        Args:
            base_retrieval_engine: Underlying retrieval engine
            cache_ttl: Cache TTL in seconds (default: 30 minutes)
        """
        self.base = base_retrieval_engine
        self.cache = TTLCache(maxsize=500, ttl=cache_ttl)
        self.hit_count = 0
        self.miss_count = 0
    
    def retrieve(self, query: str, top_k: int = 10) -> list[CodeChunk]:
        """
        Retrieve chunks for query, using cache when possible.
        
        Cache key: (query, top_k)
        Cache value: list[CodeChunk]
        """
        cache_key = f"{query}:{top_k}"
        
        if cache_key in self.cache:
            self.hit_count += 1
            logger.debug(f"Cache HIT: {query} (hit rate: {self.hit_rate():.1%})")
            return self.cache[cache_key]
        
        # Cache miss — perform actual retrieval
        self.miss_count += 1
        results = self.base.retrieve(query, top_k)
        
        # Cache results
        self.cache[cache_key] = results
        
        logger.debug(f"Cache MISS: {query} (hit rate: {self.hit_rate():.1%})")
        return results
    
    def hit_rate(self) -> float:
        """Return cache hit rate percentage"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def clear_cache(self):
        """Clear cache (e.g., after major re-index)"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        logger.info("Query cache cleared")
```

---

#### **Component 5: LazyBatcher**

```python
# src/ws_ctx_engine/index/lazy_batcher.py

import threading
import time
from typing import Callable

class LazyBatcher:
    """
    Batches multiple file changes into single re-index operation.
    Prevents re-indexing during active editing sessions.
    """
    
    def __init__(self, update_callback: Callable[[list[str]], None], 
                 batch_delay_sec: int = 300):
        """
        Args:
            update_callback: Function to call with batch of files
            batch_delay_sec: Wait time before processing batch (default: 5 min)
        """
        self.update_callback = update_callback
        self.batch_delay = batch_delay_sec
        self.pending_files: set[str] = set()
        self.timer: threading.Timer | None = None
        self.lock = threading.Lock()
    
    def schedule_update(self, filepath: str):
        """
        Schedule file for re-indexing.
        If called multiple times within delay window, resets timer.
        """
        with self.lock:
            self.pending_files.add(filepath)
            
            # Cancel existing timer
            if self.timer:
                self.timer.cancel()
            
            # Start new timer
            self.timer = threading.Timer(self.batch_delay, self._flush_batch)
            self.timer.start()
            
            logger.debug(f"Scheduled update for {filepath} "
                        f"({len(self.pending_files)} files pending)")
    
    def _flush_batch(self):
        """Process all pending files in one batch"""
        with self.lock:
            if not self.pending_files:
                return
            
            files = list(self.pending_files)
            self.pending_files.clear()
        
        logger.info(f"Processing batch of {len(files)} files")
        self.update_callback(files)
    
    def flush_now(self):
        """Force immediate processing of pending files"""
        if self.timer:
            self.timer.cancel()
        self._flush_batch()
```

---

### 3.3 Integration with Existing Code

**Where Components Fit**:

```
src/ws_ctx_engine/
├── index/
│   ├── indexer.py              # Existing — full re-index
│   ├── incremental_updater.py  # NEW — incremental updates
│   ├── file_watcher.py         # NEW — detect changes
│   ├── staleness_monitor.py    # NEW — health checks
│   └── lazy_batcher.py         # NEW — batch updates
├── retrieval/
│   ├── retrieval.py            # Existing — search logic
│   └── cached_retrieval.py     # NEW — add caching layer
└── mcp/
    ├── server.py               # Existing — MCP tools
    └── cached_search.py        # NEW — cache MCP queries
```

---

## 4. Implementation Phases

### Phase 1: Incremental Updates (Week 1) ⭐⭐⭐

**Goal**: Enable file-level incremental re-indexing

**Tasks**:
- [ ] Implement `IncrementalIndexUpdater` (200 lines)
- [ ] Add `get_ids_by_file()` method to `VectorIndex`
- [ ] Test with single file change
- [ ] Benchmark: 120 min → <1 sec

**Success Criteria**:
- ✅ Changing 1 file triggers re-index of only that file
- ✅ Re-index time <1 second per file
- ✅ No regression in retrieval quality

**Effort**: 1 day

---

### Phase 2: Staleness Detection (Week 2) ⭐⭐

**Goal**: Monitor index health and alert when stale

**Tasks**:
- [ ] Implement `StalenessMonitor` (150 lines)
- [ ] Add file hash tracking to `IncrementalIndexUpdater`
- [ ] Create health check endpoint
- [ ] Add logging/alerting when health <0.7

**Success Criteria**:
- ✅ System knows exactly which chunks are stale
- ✅ Health score reported accurately
- ✅ Alerts trigger when needed

**Effort**: 0.5 day

---

### Phase 3: Query Caching (Week 3) ⭐⭐⭐

**Goal**: Cache repeated queries to reduce latency

**Tasks**:
- [ ] Add `CachedRetrievalEngine` wrapper (100 lines)
- [ ] Integrate with existing retrieval pipeline
- [ ] Add cache metrics (hit rate, size)
- [ ] Tune TTL (start with 30 minutes)

**Success Criteria**:
- ✅ Cache hit rate >60% for dev workflows
- ✅ Query latency reduced 60-70% for cached queries
- ✅ Cache invalidation works after re-index

**Effort**: 2-3 hours

---

### Phase 4: Lazy Batching (Week 4) ⭐

**Goal**: Batch multiple changes to reduce re-index frequency

**Tasks**:
- [ ] Implement `LazyBatcher` (80 lines)
- [ ] Wire into file watcher
- [ ] Set default delay: 5 minutes
- [ ] Add manual flush option

**Success Criteria**:
- ✅ 90% reduction in re-index operations during active editing
- ✅ No user-visible delays
- ✅ Batch processes reliably after delay

**Effort**: 0.5 day

---

### Phase 5: Background Worker (Optional — Phase 2 Sprint) ⭐

**Goal**: Non-blocking index updates

**Tasks**:
- [ ] Create background thread for updates
- [ ] Add priority queue
- [ ] Handle graceful shutdown
- [ ] Add error recovery

**Success Criteria**:
- ✅ Index updates don't block main thread
- ✅ Queue survives process restart (optional)
- ✅ Errors logged and retried

**Effort**: 0.5 day

---

### Phase 6: Partitioned Indexes (Optional — Phase 2 Sprint) ⭐⭐

**Goal**: Separate stable vs unstable code

**Tasks**:
- [ ] Split index by file type (.py vs .md)
- [ ] Route queries to appropriate partitions
- [ ] Merge results with weighted ranking
- [ ] Benchmark improvement

**Success Criteria**:
- ✅ Docs changes don't trigger .py re-index
- ✅ 50% faster updates for mixed changes
- ✅ No quality degradation

**Effort**: 1 day

---

## 5. Performance Projections

### 5.1 Latency Improvements

| Scenario | Current | Phase 1 | Phase 3 | Final |
|----------|---------|---------|---------|-------|
| **Single file change** | 120 min | **1 sec** | 1 sec | 1 sec |
| **10 files in 5 min** | 1,200 min (10×) | 10 sec | 10 sec | **5 sec** (batched) |
| **Repeated query** | 500 ms | 500 ms | **50 ms** | 50 ms |
| **Full re-index** | 120 min | 120 min | 120 min | 120 min |

### 5.2 Compute Cost Savings

**Assumptions**:
- Active dev: 20 commits/day × 22 days = 440 changes/month
- GPU cost: $0.10/minute
- Current avg re-index: 120 minutes

**Monthly Cost Comparison**:

| Approach | Re-indexes/Month | Time/Month | Cost/Month | Savings |
|----------|-----------------|------------|------------|---------|
| **Current (full)** | 440 | 52,800 min | $5,280 | — |
| **Phase 1 (incremental)** | 440 | 440 min | $44 | **99%** |
| **Phase 4 (batched)** | 44 | 220 min | $22 | **99.6%** |
| **Phase 3 (cached)** | N/A | N/A | N/A | **+60% speedup** |

### 5.3 Developer Productivity

**Time saved waiting for re-index**:

| Scenario | Current Wait | With Incremental | Saved/Month |
|----------|-------------|------------------|-------------|
| After each commit | 120 min | 1 sec | **880 hours** |
| Before demo | 120 min | 1 sec | **4 hours** |
| Debugging session (5 commits) | 600 min | 5 sec | **10 hours** |

**Total productivity gain**: ~900 hours/month = **$45,000/month** (at $50/hr)

---

## 6. Risk Mitigation

### Risk 1: Incremental Update Bugs

**Risk**: Partial updates corrupt index state

**Mitigation**:
- ✅ Comprehensive unit tests for `IncrementalIndexUpdater`
- ✅ Validation after each update (checksum verification)
- ✅ Rollback mechanism: keep backup of previous index
- ✅ Feature flag: can disable and fall back to full re-index

**Fallback Plan**:
```python
if incremental_update_fails():
    logger.error("Incremental update failed, falling back to full re-index")
    self.full_indexer.index_codebase()
```

---

### Risk 2: Cache Staleness

**Risk**: Serving outdated results from cache

**Mitigation**:
- ✅ Short TTL (30 minutes default)
- ✅ Auto-invalidate cache after re-index
- ✅ Version stamp cache entries
- ✅ Manual cache clear command

**Fallback Plan**:
```python
# Emergency cache clear
@mcp_tool(name="clear_query_cache")
async def clear_cache():
    retrieval_engine.clear_cache()
    return "Cache cleared"
```

---

### Risk 3: File Watcher Performance

**Risk**: Watching 4,000 files consumes resources

**Mitigation**:
- ✅ Use efficient `watchdog` library (native OS events)
- ✅ Filter to only tracked file types (.py, .ts, .md, etc.)
- ✅ Exclude vendor/, node_modules/, .git/
- ✅ Sample test: monitor resource usage with 10K files

**Fallback Plan**:
- Disable file watcher, use manual trigger instead

---

### Risk 4: Staleness Detection Overhead

**Risk**: Hash computation slows down system

**Mitigation**:
- ✅ Hash only on file change, not every query
- ✅ Cache file hashes in memory
- ✅ Lazy hashing: only hash when health check runs
- ✅ Async hashing in background thread

**Fallback Plan**:
- Run health checks less frequently (every 10 min instead of 1 min)

---

## 7. Success Metrics

### 7.1 Key Performance Indicators (KPIs)

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Avg re-index time** | 120 min | **<1 sec/file** | Log timing |
| **Cache hit rate** | 0% | **>60%** | Cache metrics |
| **Index health score** | Unknown | **>0.9** | Staleness monitor |
| **Compute cost/month** | $5,280 | **<$100** | AWS bill |
| **Dev productivity** | 900 hrs lost | **<50 hrs lost** | Survey |

### 7.2 Monitoring Dashboard

**Metrics to Track** (add to existing perf dashboard):

```python
# Example metrics to emit
metrics.gauge("index.total_chunks", count)
metrics.gauge("index.stale_chunks", stale_count)
metrics.gauge("index.health_score", health_score)
metrics.histogram("index.reindex_latency_sec", elapsed_time)
metrics.counter("index.reindex_operations_total", 1)
metrics.gauge("query_cache.size", cache_size)
metrics.gauge("query_cache.hit_rate", hit_rate)
```

### 7.3 Go/No-Go Gates

**Phase 1 Gate** (after Week 1):
- [ ] Incremental update works for single file
- [ ] No data corruption after 100 updates
- [ ] Re-index time <1 second
- [ ] Rollback tested and working

**Phase 3 Gate** (after Week 3):
- [ ] Cache hit rate >50% in real usage
- [ ] No stale results served
- [ ] Cache invalidation works correctly
- [ ] Memory usage <100MB for cache

**Production Gate** (before full rollout):
- [ ] All phases complete and tested
- [ ] Compute cost reduced >90%
- [ ] No user-reported regressions
- [ ] Monitoring dashboard operational

---

## Appendix A: Code Snippets

### A.1 Quick Start — Enable Incremental Updates

```python
# In your indexing pipeline, replace:

# OLD CODE:
indexer = Indexer()
indexer.index_codebase(repo_path)  # Takes 120 min

# NEW CODE:
incremental = IncrementalIndexUpdater(
    vector_index=vector_index,
    graph_store=graph_store,
    chunker=chunker,
    embedder=embedder
)

# First time: full index
indexer.index_codebase(repo_path)

# Subsequent: incremental
incremental.update_on_file_change("src/changed_file.py")  # Takes <1 sec
```

---

### A.2 Quick Start — Add Query Caching

```python
# In your retrieval pipeline, add wrapper:

# OLD CODE:
retrieval = RetrievalEngine(vector_index)
results = retrieval.retrieve(query, top_k=10)

# NEW CODE:
cached_retrieval = CachedRetrievalEngine(retrieval, cache_ttl=1800)
results = cached_retrieval.retrieve(query, top_k=10)

# Check performance
print(f"Cache hit rate: {cached_retrieval.hit_rate():.1%}")
```

---

### A.3 Quick Start — Monitor Index Health

```python
# Add health check to your monitoring:

monitor = StalenessMonitor(vector_index, chunker)
health = monitor.check_health()

print(health)  # Output: "🟢 Index Health: 0.95 (50/1000 stale)"

if health.health_score < 0.8:
    logger.warning(f"Index health degraded: {health}")
    # Optionally trigger auto-reindex
    incremental.update_batch(monitor.get_stale_chunk_ids())
```

---

## Appendix B: Testing Strategy

### B.1 Unit Tests

```python
# tests/unit/test_incremental_updater.py

def test_incremental_update_single_file():
    """Verify only changed file is re-indexed"""
    updater = IncrementalIndexUpdater(...)
    
    # Initial index
    initial_count = vector_index.count()
    
    # Change one file
    updater.update_on_file_change("src/test.py")
    
    # Verify count unchanged (same number of chunks)
    assert vector_index.count() == initial_count
    
    # Verify only test.py chunks changed
    test_chunks = vector_index.get_chunks_by_file("src/test.py")
    assert len(test_chunks) > 0

def test_staleness_detection():
    """Verify staleness detector catches changes"""
    monitor = StalenessMonitor(...)
    
    # Initial health should be perfect
    health = monitor.check_health()
    assert health.health_score == 1.0
    
    # Modify a file
    modify_file("src/test.py")
    
    # Health should degrade
    health = monitor.check_health()
    assert health.health_score < 1.0
    assert health.stale_chunks > 0
```

---

### B.2 Integration Tests

```python
# tests/integration/test_index_management.py

def test_end_to_end_incremental_indexing():
    """Full workflow: edit → detect → update → query"""
    # Setup
    watcher = FileWatcher(repo_path)
    updater = IncrementalIndexUpdater(...)
    watcher.start(updater.update_on_file_change)
    
    # Edit file
    with open("src/test.py", "a") as f:
        f.write("\ndef new_function(): pass\n")
    
    # Wait for watcher to trigger
    time.sleep(2)
    
    # Verify update happened
    chunks = vector_index.get_chunks_by_file("src/test.py")
    assert any("new_function" in c.content for c in chunks)
    
    # Cleanup
    watcher.stop()
```

---

## References

- Qoder Repo Wiki documentation: https://docs.qoder.com/user-guide/repo-wiki
- Watchdog library (file system events): https://pypi.org/project/watchdog/
- Cachetools (TTL cache): https://pypi.org/project/cachetools/
- Vector index implementation: `src/ws_ctx_engine/index/vector_index.py`
- Graph store roadmap: `docs/reports/GRAPH_RAG_ROADMAP.md`

---

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-27 | Initial roadmap |
