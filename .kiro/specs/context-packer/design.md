# Design Document: Context Packer

## Overview

Context Packer is a Python-based tool that intelligently packages codebases into optimized context for Large Language Models. The system uses a hybrid ranking approach combining semantic search with structural analysis (PageRank) to select the most relevant files within a token budget. It supports dual-format output (XML for one-shot paste workflows, ZIP for multi-turn upload workflows) and implements comprehensive fallback strategies to ensure production reliability.

The core design philosophy emphasizes:
- **Intelligence over size**: Select files based on importance scores, not file size
- **Budget awareness**: Precise token counting to fit LLM context windows
- **Production readiness**: Fallback solutions for every component
- **Dual-format flexibility**: Support both paste and upload workflows

## Architecture

### System Components

The system is organized into six primary components with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Layer                               │
│  • Repository path                                           │
│  • Optional: PR diff / changed files                         │
│  • Optional: Natural language query                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  AST Chunker                                 │
│  Primary: py-tree-sitter | Fallback: Regex                  │
│  • Parse source → AST                                        │
│  • Extract function/class boundaries                         │
│  • Generate symbol definitions + references                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Index Phase (Offline)                           │
│                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │   Vector Index       │    │   RepoMap Graph      │      │
│  │ Primary: LEANN       │    │ Primary: igraph      │      │
│  │ Fallback: FAISS      │    │ Fallback: NetworkX   │      │
│  └──────────────────────┘    └──────────────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Query Phase (Per Review)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Retrieval Engine                            │  │
│  │  1. Semantic search (Vector Index)                    │  │
│  │  2. Structural ranking (PageRank)                     │  │
│  │  3. Score merging (weighted combination)              │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                Budget Manager                                │
│  • Token counting (tiktoken)                                 │
│  • Greedy knapsack selection                                 │
│  • 80/20 split (content/metadata)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Output Packers                                  │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │   XML Packer         │    │   ZIP Packer         │      │
│  │   (lxml)             │    │   (zipfile)          │      │
│  └──────────────────────┘    └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

**Index Phase Flow:**
1. AST Chunker parses all source files into CodeChunk objects
2. Vector Index builds embeddings for semantic search
3. RepoMap Graph constructs dependency graph and computes PageRank
4. Both indexes are persisted to disk for reuse

**Query Phase Flow:**
1. Load pre-built indexes from disk
2. Retrieval Engine performs semantic search and graph ranking
3. Scores are merged using configurable weights
4. Budget Manager selects files using greedy knapsack
5. Output Packer generates XML or ZIP based on configuration

### Fallback Strategy Architecture

The system implements a graceful degradation hierarchy:

```
Level 1: igraph + LEANN + local embeddings (optimal)
  ↓ igraph fails
Level 2: NetworkX + LEANN + local embeddings
  ↓ LEANN fails
Level 3: NetworkX + FAISS + local embeddings
  ↓ local embeddings OOM
Level 4: NetworkX + FAISS + API embeddings
  ↓ API fails
Level 5: NetworkX + TF-IDF (no embeddings)
  ↓ NetworkX too slow
Level 6: File size ranking only (no graph)
```

Each component detects failures at import time or runtime and automatically switches to the fallback implementation.

## Components and Interfaces

### 1. AST Chunker

**Responsibility:** Parse source code into structured chunks with metadata

**Interface:**
```python
class CodeChunk:
    path: str
    start_line: int
    end_line: int
    content: str
    symbols_defined: List[str]  # function/class names
    symbols_referenced: List[str]  # imports, calls
    language: str

class ASTChunker(ABC):
    @abstractmethod
    def parse(self, repo_path: str) -> List[CodeChunk]:
        """Parse all source files in repository"""
        pass

class TreeSitterChunker(ASTChunker):
    """Primary implementation using py-tree-sitter"""
    def parse(self, repo_path: str) -> List[CodeChunk]:
        # Use tree-sitter for accurate AST parsing
        pass

class RegexChunker(ASTChunker):
    """Fallback implementation using regex patterns"""
    def parse(self, repo_path: str) -> List[CodeChunk]:
        # Use regex for basic function/class detection
        pass
```

**Technology:**
- Primary: `py-tree-sitter` (C bindings, 40+ languages)
- Fallback: Regex patterns for Python/JavaScript/TypeScript

**Performance Target:** <5 seconds per 1000 lines of code

### 2. Vector Index

**Responsibility:** Semantic search over code chunks

**Interface:**
```python
class VectorIndex(ABC):
    @abstractmethod
    def build(self, chunks: List[CodeChunk]) -> None:
        """Build vector index from chunks"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Return (file_path, similarity_score) pairs"""
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """Persist index to disk"""
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, path: str) -> 'VectorIndex':
        """Load index from disk"""
        pass

class LEANNIndex(VectorIndex):
    """Primary: Low-storage graph-based index"""
    # 97% storage savings, recompute on-the-fly
    pass

class FAISSIndex(VectorIndex):
    """Fallback: HNSW index from faiss-cpu"""
    # Battle-tested, 3% storage overhead
    pass
```

**Technology:**
- Primary: LEANN (custom implementation, graph-based)
- Fallback: `faiss-cpu` with HNSW index
- Embeddings: `sentence-transformers` (all-MiniLM-L6-v2)
- API Fallback: OpenAI embeddings API

**Performance Target:** <2 seconds query time for 10k files

### 3. RepoMap Graph

**Responsibility:** Build dependency graph and compute structural importance

**Interface:**
```python
class RepoMapGraph(ABC):
    @abstractmethod
    def build(self, chunks: List[CodeChunk]) -> None:
        """Build dependency graph from symbol references"""
        pass
    
    @abstractmethod
    def pagerank(self, changed_files: List[str] = None) -> Dict[str, float]:
        """Compute PageRank scores, boosting changed files"""
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """Persist graph to disk"""
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, path: str) -> 'RepoMapGraph':
        """Load graph from disk"""
        pass

class IGraphRepoMap(RepoMapGraph):
    """Primary: C++ backend for fast PageRank"""
    pass

class NetworkXRepoMap(RepoMapGraph):
    """Fallback: Pure Python implementation"""
    pass
```

**Technology:**
- Primary: `python-igraph` (C++ backend)
- Fallback: `networkx` (pure Python)

**Performance Target:** 
- igraph: <1 second for 10k nodes
- NetworkX: <10 seconds for 10k nodes

### 4. Retrieval Engine

**Responsibility:** Merge semantic and structural scores

**Interface:**
```python
class RetrievalEngine:
    def __init__(
        self,
        vector_index: VectorIndex,
        graph: RepoMapGraph,
        semantic_weight: float = 0.6,
        pagerank_weight: float = 0.4
    ):
        self.vector_index = vector_index
        self.graph = graph
        self.semantic_weight = semantic_weight
        self.pagerank_weight = pagerank_weight
    
    def retrieve(
        self,
        query: str = None,
        changed_files: List[str] = None,
        top_k: int = 100
    ) -> List[Tuple[str, float]]:
        """
        Return (file_path, importance_score) pairs
        
        importance_score = semantic_weight * semantic_score 
                         + pagerank_weight * pagerank_score
        """
        # 1. Get semantic scores
        semantic_scores = self.vector_index.search(query, top_k) if query else {}
        
        # 2. Get PageRank scores
        pagerank_scores = self.graph.pagerank(changed_files)
        
        # 3. Normalize both to [0, 1]
        semantic_normalized = self._normalize(semantic_scores)
        pagerank_normalized = self._normalize(pagerank_scores)
        
        # 4. Merge with weights
        merged = self._merge_scores(
            semantic_normalized,
            pagerank_normalized
        )
        
        return sorted(merged.items(), key=lambda x: x[1], reverse=True)
```

**Algorithm:**
1. Normalize semantic scores to [0, 1] range
2. Normalize PageRank scores to [0, 1] range
3. Compute weighted sum: `final = w1 * semantic + w2 * pagerank`
4. Sort by final score descending

### 5. Budget Manager

**Responsibility:** Select files within token budget using greedy knapsack

**Interface:**
```python
class BudgetManager:
    def __init__(self, token_budget: int, encoding: str = "cl100k_base"):
        self.token_budget = token_budget
        self.encoding = tiktoken.get_encoding(encoding)
        self.content_budget = int(token_budget * 0.8)  # Reserve 20% for metadata
    
    def select_files(
        self,
        ranked_files: List[Tuple[str, float]],
        repo_path: str
    ) -> Tuple[List[str], int]:
        """
        Return (selected_files, total_tokens)
        
        Uses greedy knapsack: sort by importance, accumulate until budget reached
        """
        selected = []
        total_tokens = 0
        
        for file_path, importance_score in ranked_files:
            content = read_file(os.path.join(repo_path, file_path))
            tokens = len(self.encoding.encode(content))
            
            if total_tokens + tokens <= self.content_budget:
                selected.append(file_path)
                total_tokens += tokens
            else:
                break
        
        return selected, total_tokens
```

**Technology:** `tiktoken` (OpenAI tokenizer)

**Algorithm:** Greedy knapsack with 80/20 budget split

**Accuracy Target:** ±2% of actual LLM token count

### 6. Output Packers

**Responsibility:** Generate XML or ZIP output formats

**XML Packer Interface:**
```python
class XMLPacker:
    def pack(
        self,
        selected_files: List[str],
        repo_path: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generate Repomix-style XML output
        
        Structure:
        <repository>
          <metadata>
            <name>repo-name</name>
            <file_count>42</file_count>
            <total_tokens>95000</total_tokens>
          </metadata>
          <files>
            <file path="src/main.py" tokens="1234">
              <content><![CDATA[...]]></content>
            </file>
            ...
          </files>
        </repository>
        """
        pass
```

**ZIP Packer Interface:**
```python
class ZIPPacker:
    def pack(
        self,
        selected_files: List[str],
        repo_path: str,
        metadata: Dict[str, Any],
        importance_scores: Dict[str, float]
    ) -> bytes:
        """
        Generate ZIP with preserved structure
        
        Structure:
        context-pack.zip
        ├── files/
        │   ├── src/
        │   │   └── main.py
        │   └── tests/
        │       └── test_main.py
        └── REVIEW_CONTEXT.md
        
        REVIEW_CONTEXT.md contains:
        - List of included files with importance scores
        - Explanation of why each file was included
        - Suggested reading order
        """
        pass
```

**Technology:**
- XML: `lxml` (C-based, fast)
- ZIP: `zipfile` (stdlib)

## Data Models

### CodeChunk

```python
@dataclass
class CodeChunk:
    """Represents a parsed code segment with metadata"""
    
    path: str                      # Relative path from repo root
    start_line: int                # Starting line number (1-indexed)
    end_line: int                  # Ending line number (inclusive)
    content: str                   # Raw source code content
    symbols_defined: List[str]     # Functions/classes defined in this chunk
    symbols_referenced: List[str]  # Imports and function calls
    language: str                  # Programming language (python, javascript, etc)
    
    def token_count(self, encoding) -> int:
        """Count tokens using tiktoken"""
        return len(encoding.encode(self.content))
```

### Configuration

```python
@dataclass
class Config:
    """System configuration loaded from .context-pack.yaml"""
    
    # Output settings
    format: str = "zip"  # "xml" | "zip"
    token_budget: int = 100000
    output_path: str = "./output"
    
    # Scoring weights
    semantic_weight: float = 0.6
    pagerank_weight: float = 0.4
    
    # File filtering
    include_tests: bool = False
    include_patterns: List[str] = field(default_factory=lambda: ["**/*.py", "**/*.js", "**/*.ts"])
    exclude_patterns: List[str] = field(default_factory=lambda: ["*.min.js", "node_modules/**", "__pycache__/**"])
    
    # Backend selection
    backends: Dict[str, str] = field(default_factory=lambda: {
        "vector_index": "auto",  # auto | leann | faiss
        "graph": "auto",         # auto | igraph | networkx
        "embeddings": "auto"     # auto | local | api
    })
    
    # Embeddings config
    embeddings: Dict[str, Any] = field(default_factory=lambda: {
        "model": "all-MiniLM-L6-v2",
        "device": "cpu",
        "batch_size": 32,
        "api_provider": "openai",
        "api_key_env": "OPENAI_API_KEY"
    })
    
    # Performance tuning
    performance: Dict[str, Any] = field(default_factory=lambda: {
        "max_workers": 4,
        "cache_embeddings": True,
        "incremental_index": True
    })
    
    @classmethod
    def load(cls, path: str = ".context-pack.yaml") -> 'Config':
        """Load configuration from YAML file"""
        if not os.path.exists(path):
            return cls()  # Use defaults
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
```

### Index Metadata

```python
@dataclass
class IndexMetadata:
    """Metadata stored with indexes for staleness detection"""
    
    created_at: datetime
    repo_path: str
    file_count: int
    backend: str  # "leann", "faiss", "igraph", "networkx"
    file_hashes: Dict[str, str]  # path -> content hash
    
    def is_stale(self, repo_path: str) -> bool:
        """Check if any files have been modified since index creation"""
        for path, old_hash in self.file_hashes.items():
            full_path = os.path.join(repo_path, path)
            if not os.path.exists(full_path):
                return True
            
            with open(full_path, 'rb') as f:
                new_hash = hashlib.sha256(f.read()).hexdigest()
            
            if new_hash != old_hash:
                return True
        
        return False
```

## Data Flow

### Index Phase (Offline)

```python
def index_repository(repo_path: str, config: Config) -> None:
    """
    Build and persist indexes for later queries
    
    Steps:
    1. Parse codebase with AST Chunker
    2. Build Vector Index with embeddings
    3. Build RepoMap Graph with PageRank
    4. Save indexes to .context-pack/
    """
    
    # 1. Parse with fallback
    try:
        chunker = TreeSitterChunker()
        chunks = chunker.parse(repo_path)
    except ImportError:
        logger.warning("tree-sitter not available, using regex fallback")
        chunker = RegexChunker()
        chunks = chunker.parse(repo_path)
    
    # 2. Build vector index with fallback
    try:
        if config.backends["vector_index"] == "leann":
            vector_index = LEANNIndex()
        elif config.backends["vector_index"] == "faiss":
            vector_index = FAISSIndex()
        else:  # auto
            try:
                vector_index = LEANNIndex()
            except (ImportError, RuntimeError):
                logger.warning("LEANN not available, using FAISS fallback")
                vector_index = FAISSIndex()
        
        vector_index.build(chunks)
        vector_index.save(".context-pack/vector.idx")
    except Exception as e:
        logger.error(f"Vector index build failed: {e}")
        raise
    
    # 3. Build graph with fallback
    try:
        if config.backends["graph"] == "igraph":
            graph = IGraphRepoMap()
        elif config.backends["graph"] == "networkx":
            graph = NetworkXRepoMap()
        else:  # auto
            try:
                graph = IGraphRepoMap()
            except ImportError:
                logger.warning("igraph not available, using NetworkX fallback")
                graph = NetworkXRepoMap()
        
        graph.build(chunks)
        graph.save(".context-pack/graph.pkl")
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise
    
    # 4. Save metadata
    metadata = IndexMetadata(
        created_at=datetime.now(),
        repo_path=repo_path,
        file_count=len(chunks),
        backend=f"{vector_index.__class__.__name__}+{graph.__class__.__name__}",
        file_hashes={chunk.path: hash_file(chunk.path) for chunk in chunks}
    )
    with open(".context-pack/metadata.json", "w") as f:
        json.dump(asdict(metadata), f, default=str)
```

### Query Phase (Per Review)

```python
def query_and_pack(
    repo_path: str,
    query: str = None,
    changed_files: List[str] = None,
    config: Config = None
) -> str:
    """
    Query indexes and generate output
    
    Steps:
    1. Load indexes (auto-detect backend)
    2. Retrieve candidates with hybrid ranking
    3. Select files within budget
    4. Pack output in configured format
    """
    
    if config is None:
        config = Config.load()
    
    # 1. Load indexes
    vector_index = VectorIndex.load(".context-pack/vector.idx")
    graph = RepoMapGraph.load(".context-pack/graph.pkl")
    
    # 2. Retrieve with hybrid ranking
    retrieval_engine = RetrievalEngine(
        vector_index=vector_index,
        graph=graph,
        semantic_weight=config.semantic_weight,
        pagerank_weight=config.pagerank_weight
    )
    
    ranked_files = retrieval_engine.retrieve(
        query=query,
        changed_files=changed_files,
        top_k=100
    )
    
    # 3. Budget selection
    budget_manager = BudgetManager(token_budget=config.token_budget)
    selected_files, total_tokens = budget_manager.select_files(
        ranked_files=ranked_files,
        repo_path=repo_path
    )
    
    # 4. Pack output
    metadata = {
        "repo_name": os.path.basename(repo_path),
        "file_count": len(selected_files),
        "total_tokens": total_tokens,
        "query": query,
        "changed_files": changed_files
    }
    
    if config.format == "xml":
        packer = XMLPacker()
        output = packer.pack(selected_files, repo_path, metadata)
        output_path = os.path.join(config.output_path, "repomix-output.xml")
        with open(output_path, "w") as f:
            f.write(output)
    else:  # zip
        packer = ZIPPacker()
        importance_scores = dict(ranked_files)
        output = packer.pack(selected_files, repo_path, metadata, importance_scores)
        output_path = os.path.join(config.output_path, "context-pack.zip")
        with open(output_path, "wb") as f:
            f.write(output)
    
    return output_path
```


## Error Handling

### Error Categories

The system handles four categories of errors:

**1. Dependency Errors (ImportError)**
- Trigger: Primary backend fails to import
- Response: Automatic fallback to backup implementation
- Example: igraph not installed → switch to NetworkX

**2. Runtime Errors (RuntimeError, MemoryError)**
- Trigger: Backend fails during execution (OOM, build failure)
- Response: Fallback to simpler algorithm or API
- Example: Local embeddings OOM → switch to OpenAI API

**3. Data Errors (ValueError, FileNotFoundError)**
- Trigger: Invalid input or missing files
- Response: Log error with actionable message, skip file or fail gracefully
- Example: Corrupted source file → skip and continue

**4. Configuration Errors (ValidationError)**
- Trigger: Invalid configuration values
- Response: Log warning, use default values
- Example: Invalid weight values → use defaults (0.6, 0.4)

### Fallback Decision Tree

```python
class BackendSelector:
    """Automatic backend selection with fallback"""
    
    def select_vector_index(self, config: Config) -> VectorIndex:
        """Select vector index backend with fallback chain"""
        
        if config.backends["vector_index"] == "faiss":
            return self._load_faiss()
        
        if config.backends["vector_index"] == "leann":
            return self._load_leann()
        
        # Auto mode: try primary, fallback on failure
        try:
            return self._load_leann()
        except (ImportError, RuntimeError) as e:
            logger.warning(f"LEANN failed ({e}), falling back to FAISS")
            try:
                return self._load_faiss()
            except ImportError:
                logger.error("Both LEANN and FAISS unavailable, falling back to TF-IDF")
                return TFIDFIndex()  # Minimal fallback
    
    def select_graph(self, config: Config) -> RepoMapGraph:
        """Select graph backend with fallback chain"""
        
        if config.backends["graph"] == "networkx":
            return self._load_networkx()
        
        if config.backends["graph"] == "igraph":
            return self._load_igraph()
        
        # Auto mode
        try:
            return self._load_igraph()
        except ImportError as e:
            logger.warning(f"igraph failed ({e}), falling back to NetworkX")
            try:
                return self._load_networkx()
            except ImportError:
                logger.error("Both igraph and NetworkX unavailable, using file size ranking")
                return FileSizeRanker()  # Minimal fallback
```

### Error Logging Strategy

```python
class ContextPackerLogger:
    """Structured logging with context"""
    
    def __init__(self, log_dir: str = ".context-pack/logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler (DEBUG and above)
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"context-packer-{datetime.now():%Y%m%d-%H%M%S}.log")
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Structured format
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger("context_packer")
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)
    
    def log_fallback(self, component: str, primary: str, fallback: str, reason: str):
        """Log backend fallback with context"""
        self.logger.warning(
            f"Fallback triggered | component={component} | "
            f"primary={primary} | fallback={fallback} | reason={reason}"
        )
    
    def log_phase(self, phase: str, duration: float, **metrics):
        """Log phase completion with metrics"""
        metrics_str = " | ".join(f"{k}={v}" for k, v in metrics.items())
        self.logger.info(
            f"Phase complete | phase={phase} | duration={duration:.2f}s | {metrics_str}"
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error with full context and stack trace"""
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        self.logger.error(
            f"Error occurred | {context_str}",
            exc_info=True
        )
```

### Actionable Error Messages

```python
class ContextPackerError(Exception):
    """Base exception with actionable suggestions"""
    
    def __init__(self, message: str, suggestion: str):
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"{message}\n\nSuggestion: {suggestion}")

class DependencyError(ContextPackerError):
    """Raised when required dependency is missing"""
    
    @classmethod
    def missing_backend(cls, backend: str, install_cmd: str):
        return cls(
            message=f"Backend '{backend}' is not available",
            suggestion=f"Install with: {install_cmd}"
        )

class ConfigurationError(ContextPackerError):
    """Raised when configuration is invalid"""
    
    @classmethod
    def invalid_weight(cls, weight_name: str, value: float):
        return cls(
            message=f"Invalid {weight_name}: {value} (must be between 0 and 1)",
            suggestion=f"Update .context-pack.yaml with valid {weight_name} value"
        )

# Usage example
try:
    import igraph
except ImportError:
    raise DependencyError.missing_backend(
        backend="igraph",
        install_cmd="pip install python-igraph"
    )
```

### Recovery Strategies

**Partial Failure Recovery:**
```python
def parse_with_recovery(chunker: ASTChunker, repo_path: str) -> List[CodeChunk]:
    """Parse repository with per-file error recovery"""
    
    chunks = []
    failed_files = []
    
    for file_path in discover_source_files(repo_path):
        try:
            file_chunks = chunker.parse_file(file_path)
            chunks.extend(file_chunks)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            failed_files.append(file_path)
            # Continue with other files
    
    if failed_files:
        logger.info(f"Successfully parsed {len(chunks)} chunks from {len(chunks)} files")
        logger.warning(f"Failed to parse {len(failed_files)} files: {failed_files[:5]}...")
    
    return chunks
```

**Graceful Degradation:**
```python
def retrieve_with_degradation(
    retrieval_engine: RetrievalEngine,
    query: str,
    changed_files: List[str]
) -> List[Tuple[str, float]]:
    """Retrieve with graceful degradation if components fail"""
    
    try:
        # Try full hybrid retrieval
        return retrieval_engine.retrieve(query, changed_files)
    except Exception as e:
        logger.error(f"Hybrid retrieval failed: {e}")
        
        try:
            # Fall back to semantic only
            logger.info("Falling back to semantic search only")
            return retrieval_engine.vector_index.search(query, top_k=100)
        except Exception as e2:
            logger.error(f"Semantic search failed: {e2}")
            
            # Fall back to PageRank only
            logger.info("Falling back to PageRank only")
            pagerank_scores = retrieval_engine.graph.pagerank(changed_files)
            return sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)
```

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests:**
- Specific examples demonstrating correct behavior
- Edge cases (empty files, special characters, large files)
- Error conditions (missing files, invalid config)
- Integration points between components

**Property-Based Tests:**
- Universal properties that hold for all inputs
- Comprehensive input coverage through randomization
- Minimum 100 iterations per property test
- Each test references its design document property

### Testing Technology Stack

**Framework:** `pytest` for both unit and property tests

**Property-Based Testing Library:** `hypothesis`
- Mature Python library for property-based testing
- Supports complex data generation strategies
- Integrates seamlessly with pytest
- Provides automatic shrinking of failing examples

**Test Configuration:**
```python
# conftest.py
from hypothesis import settings, Verbosity

# Configure hypothesis for thorough testing
settings.register_profile("ci", max_examples=100, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=20, verbosity=Verbosity.normal)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.debug)

# Use CI profile by default
settings.load_profile("ci")
```

### Property Test Tagging

Each property-based test must include a comment tag referencing the design document property:

```python
from hypothesis import given, strategies as st

# Feature: context-packer, Property 1: Parser round-trip preserves structure
@given(st.text(min_size=1))
def test_parser_roundtrip(source_code):
    """For any valid source code, parse→print→parse should yield equivalent structure"""
    # Test implementation
    pass
```

### Test Organization

```
tests/
├── unit/
│   ├── test_ast_chunker.py
│   ├── test_vector_index.py
│   ├── test_graph.py
│   ├── test_retrieval.py
│   ├── test_budget.py
│   └── test_packers.py
├── property/
│   ├── test_parser_properties.py
│   ├── test_ranking_properties.py
│   ├── test_budget_properties.py
│   └── test_output_properties.py
├── integration/
│   ├── test_full_workflow.py
│   ├── test_fallback_scenarios.py
│   └── test_cli.py
└── conftest.py
```

### Unit Test Coverage

**AST Chunker:**
- Parse Python file with functions and classes
- Parse JavaScript file with arrow functions
- Handle syntax errors gracefully
- Extract correct symbol definitions and references

**Vector Index:**
- Build index from chunks
- Search returns correct top-K results
- Save and load preserves index
- Fallback to FAISS when LEANN unavailable

**RepoMap Graph:**
- Build graph from symbol references
- PageRank scores sum to 1.0
- Changed files receive boosted scores
- Fallback to NetworkX when igraph unavailable

**Retrieval Engine:**
- Merge scores with correct weights
- Normalize scores to [0, 1] range
- Handle missing semantic or PageRank scores

**Budget Manager:**
- Select files within token budget
- Greedy selection maximizes importance score
- Reserve 20% for metadata
- Token counting accuracy within ±2%

**Output Packers:**
- XML output is valid and well-formed
- ZIP preserves directory structure
- Manifest includes all required information

### Integration Test Scenarios

**Full Workflow:**
1. Index small repository (10 files)
2. Query with natural language
3. Verify output within token budget
4. Verify selected files have highest scores

**Fallback Scenarios:**
1. Force LEANN failure → verify FAISS fallback
2. Force igraph failure → verify NetworkX fallback
3. Force local embeddings OOM → verify API fallback
4. Verify performance within 2x of primary backend

**CLI Interface:**
1. `context-pack index` creates indexes
2. `context-pack query` generates output
3. `context-pack pack` runs full workflow
4. Invalid arguments show helpful error messages

### Performance Benchmarks

```python
import pytest
import time

@pytest.mark.benchmark
def test_index_performance_10k_files(benchmark_repo_10k):
    """Verify indexing completes within target time"""
    start = time.time()
    
    index_repository(benchmark_repo_10k, Config())
    
    duration = time.time() - start
    assert duration < 300, f"Indexing took {duration}s, expected <300s"

@pytest.mark.benchmark
def test_query_performance_10k_files(indexed_repo_10k):
    """Verify query completes within target time"""
    start = time.time()
    
    query_and_pack(indexed_repo_10k, query="authentication logic", config=Config())
    
    duration = time.time() - start
    assert duration < 10, f"Query took {duration}s, expected <10s"
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: AST Parsing Completeness

*For any* valid source file in a supported language (Python, JavaScript, TypeScript), parsing SHALL produce Code_Chunks with correct function and class boundaries, including all symbol definitions and references.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

### Property 2: Parser Fallback Resilience

*For any* file that causes Tree_Sitter to fail, the system SHALL fall back to regex-based parsing and log a warning, rather than crashing.

**Validates: Requirements 1.5, 1.6**

### Property 3: Vector Index Search Ordering

*For any* search query on a built Vector_Index, the returned results SHALL be ordered by descending cosine similarity scores.

**Validates: Requirements 2.1, 2.3**

### Property 4: Backend Fallback Automation

*For any* component where the primary backend fails to import or build, the system SHALL automatically switch to the fallback backend and log a warning with the component name and reason.

**Validates: Requirements 2.4, 2.5, 3.4, 3.5, 10.1, 10.2**

### Property 5: Embedding Fallback Chain

*For any* memory failure during local embedding generation, the system SHALL fall back to API-based embeddings without crashing.

**Validates: Requirements 2.6**

### Property 6: Dependency Graph Construction

*For any* set of Code_Chunks with symbol references, the RepoMap_Graph SHALL build a directed dependency graph where edges represent symbol dependencies.

**Validates: Requirements 3.1**

### Property 7: PageRank Score Validity

*For any* built RepoMap_Graph, the computed PageRank scores SHALL sum to 1.0 (within floating-point tolerance of ±0.001).

**Validates: Requirements 3.2**

### Property 8: Changed File Score Boosting

*For any* RepoMap_Graph and set of changed files, the PageRank scores of changed files SHALL be higher after boosting than before boosting.

**Validates: Requirements 3.3**

### Property 9: Score Merging Correctness

*For any* semantic scores and PageRank scores with weights (w1, w2), the merged importance score SHALL equal `w1 * normalized_semantic + w2 * normalized_pagerank` where both score types are normalized to [0, 1].

**Validates: Requirements 4.1, 4.3, 4.4**

### Property 10: Score Normalization Range

*For any* set of scores after normalization, all values SHALL be in the range [0, 1].

**Validates: Requirements 4.4**

### Property 11: Retrieval Output Format

*For any* retrieval operation, the output SHALL be a list of (file_path, importance_score) tuples sorted by importance_score in descending order.

**Validates: Requirements 4.5**

### Property 12: Token Counting Consistency

*For any* file content, token counting using tiktoken SHALL produce the same count when called multiple times on the same content.

**Validates: Requirements 5.1**

### Property 13: Greedy Selection Ordering

*For any* set of files with importance scores, the Budget_Manager SHALL process them in descending order of importance_score during selection.

**Validates: Requirements 5.2**

### Property 14: Budget Enforcement

*For any* file selection, the total tokens of selected files SHALL not exceed 80% of the configured Token_Budget.

**Validates: Requirements 5.3, 5.4**

### Property 15: Budget Manager Output Completeness

*For any* file selection, the Budget_Manager SHALL return both the list of selected files and the total token count.

**Validates: Requirements 5.6**

### Property 16: Greedy Knapsack Optimality

*For any* file selection result, no single file swap (removing one selected file and adding one unselected file) SHALL increase the total importance score while staying within the token budget.

**Validates: Requirements 5.7**

### Property 17: XML Generation Completeness

*For any* set of selected files, the generated XML SHALL include metadata header (repository name, file count, total tokens), file tags with paths, and token counts for each file.

**Validates: Requirements 6.1, 6.2, 6.3, 6.5**

### Property 18: XML Character Escaping

*For any* file content containing special XML characters (&, <, >, ", '), the XML_Packer SHALL escape them correctly in the output.

**Validates: Requirements 6.4**

### Property 19: XML Round-Trip Validity

*For any* generated XML output, parsing it with an XML parser SHALL succeed without errors, confirming the XML is well-formed and valid.

**Validates: Requirements 6.7**

### Property 20: ZIP Structure Preservation

*For any* set of selected files with directory structure, the ZIP_Packer SHALL create a ZIP archive where all files are under a `files/` directory with their original relative paths preserved, and a `REVIEW_CONTEXT.md` manifest exists in the ZIP root.

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 21: ZIP Manifest Completeness

*For any* generated ZIP manifest, it SHALL list all included files with their importance scores, explanations for inclusion, and a suggested reading order.

**Validates: Requirements 7.4, 7.5, 7.6**

### Property 22: Configuration Loading

*For any* valid `.context-pack.yaml` file, the Context_Packer SHALL load and apply all configuration values (format, token_budget, weights, patterns, backends).

**Validates: Requirements 8.1, 8.3, 8.4, 8.5, 8.6, 8.7**

### Property 23: Configuration Error Handling

*For any* invalid configuration value, the Context_Packer SHALL log an error and use the corresponding default value instead of crashing.

**Validates: Requirements 8.8**

### Property 24: Index Persistence Round-Trip

*For any* built Vector_Index and RepoMap_Graph, saving them to disk and then loading them SHALL produce indexes that return equivalent results for the same queries.

**Validates: Requirements 9.1, 9.2, 9.3**

### Property 25: Backend Auto-Detection

*For any* loaded index file, the Context_Packer SHALL correctly auto-detect which backend was used (LEANN vs FAISS, igraph vs NetworkX) and load it with the appropriate implementation.

**Validates: Requirements 9.4**

### Property 26: Index Staleness Detection

*For any* repository where files have been modified after index creation, the Context_Packer SHALL detect the indexes as stale based on file modification times or content hashes.

**Validates: Requirements 9.5**

### Property 27: Automatic Index Rebuild

*For any* stale index, the Context_Packer SHALL automatically rebuild it before processing queries.

**Validates: Requirements 9.6**

### Property 28: Graceful Degradation

*For any* component where all backends fail, the Context_Packer SHALL degrade to a simpler algorithm (TF-IDF for vector index, file size ranking for graph) and continue execution rather than crashing.

**Validates: Requirements 10.3, 10.4, 10.5, 10.6**

### Property 29: CLI Index Command

*For any* valid repository path provided to `context-pack index`, the command SHALL build and save indexes to `.context-pack/` directory.

**Validates: Requirements 11.2**

### Property 30: CLI Query Command

*For any* query text provided to `context-pack query`, the command SHALL search indexes and generate output in the configured format.

**Validates: Requirements 11.3**

### Property 31: CLI Pack Command

*For any* valid repository path provided to `context-pack pack`, the command SHALL execute the full workflow (index, query, pack) and produce output.

**Validates: Requirements 11.4**

### Property 32: CLI Flag Handling

*For any* valid CLI flags (--format, --budget, --config), the Context_Packer SHALL apply the flag values, overriding configuration file or default values.

**Validates: Requirements 11.5, 11.6, 11.7**

### Property 33: CLI Exit Codes

*For any* CLI command execution, the exit code SHALL be 0 on success and non-zero on failure.

**Validates: Requirements 11.8**

### Property 34: Comprehensive Error Logging

*For any* error that occurs, the Context_Packer SHALL log it with file path, line number, stack trace, and an actionable suggestion for fixing the issue.

**Validates: Requirements 12.1, 12.7**

### Property 35: Dual Output Logging

*For any* log message, it SHALL appear in both the console output and the log file in `.context-pack/logs/`.

**Validates: Requirements 12.6**

### Property 36: Log Level Filtering

*For any* configured log level, only messages at that level or higher SHALL be displayed (DEBUG < INFO < WARNING < ERROR).

**Validates: Requirements 12.4**

### Property 37: Verbose Mode Timing

*For any* operation running in verbose mode, the Context_Packer SHALL log detailed timing information for each phase.

**Validates: Requirements 12.5**

### Property 38: Metrics Reporting Completeness

*For any* completed indexing operation, the Context_Packer SHALL report total time, files processed, and index size; for any completed query operation, it SHALL report query time, files selected, and total tokens.

**Validates: Requirements 13.1, 13.2, 13.3**

### Property 39: Pretty Printer Format Validity

*For any* Code_Chunks in a supported language, the Pretty_Printer SHALL format them back to syntactically valid source code in that language.

**Validates: Requirements 14.2, 14.3**

### Property 40: Parser Round-Trip Equivalence

*For any* valid source file, the sequence parse → print → parse SHALL produce Code_Chunks that are structurally equivalent to the original parse result (same boundaries, symbols, and content).

**Validates: Requirements 14.4**

### Property 41: Round-Trip Failure Logging

*For any* round-trip operation that fails equivalence check, the Context_Packer SHALL log a warning with the file path and detected differences.

**Validates: Requirements 14.5**

