# ws-ctx-engine: System Idea

## 1. Problem Statement

### The Context Window Challenge

Large Language Models (LLMs) have revolutionized code assistance, but they operate within finite context windows—typically ranging from 8K to 200K tokens. When developers seek AI-assisted code review, generation, or debugging, they face a fundamental constraint: **how do you fit a meaningful portion of your codebase into this limited window?**

### Current Approaches and Their Limitations

**Approach 1: Include Everything**
Tools like Repomix concatenate entire repositories into a single file. This approach:

- Wastes precious tokens on irrelevant code
- Often exceeds context limits for non-trivial projects
- Provides no prioritization of important files
- Results in "Lost in the Middle" phenomenon where LLMs lose focus on key content

**Approach 2: Simple Heuristics**
Other tools use basic filtering (file size, file type, directory patterns):

- Miss critical dependencies that aren't in the filtered set
- Cannot understand semantic relationships between files
- Treat all code equally regardless of structural importance
- Fail to adapt to the specific query or task at hand

**Approach 3: Signatures Only**
Some tools (like Aider's RepoMap) provide only function/class signatures:

- Lose implementation details necessary for debugging
- Cannot help with code review of actual logic
- Insufficient for understanding complex algorithms

### The Real Need

Developers need a tool that **intelligently selects** the most relevant code for their specific query or task, maximizing the value extracted from every token in the context window.

---

## 2. Solution Overview

**ws-ctx-engine** is an intelligent codebase context packaging system that solves the context window challenge through three core mechanisms:

### 2.1 Semantic Relevance (Vector Similarity)

Using sentence-transformers embeddings, ws-ctx-engine understands the _meaning_ of code, not just its text:

```
Query: "authentication and user management"
       ↓
Vector similarity identifies files discussing auth,
login, sessions, permissions—even if they don't
contain the exact query words.
```

### 2.2 Structural Importance (PageRank Scores)

By analyzing the dependency graph of your codebase, ws-ctx-engine identifies structurally important files:

```
A file imported by 50 other files → High PageRank
A utility used only once        → Low PageRank
```

This ensures foundational modules (base classes, core utilities, shared types) are prioritized appropriately.

### 2.3 Query Signals (Multi-Factor Boosting)

Beyond semantic and structural analysis, ws-ctx-engine applies intelligent boosts:

- **Symbol Matching**: Files defining symbols mentioned in the query get boosted
- **Path Keywords**: Files whose paths contain query keywords rank higher
- **Domain Classification**: Queries are classified to match domain-specific directories
- **Test Penalty**: Test files are deprioritized (configurable) to focus on implementation

### The Hybrid Formula

```
importance_score = semantic_weight × semantic_score
                 + pagerank_weight × pagerank_score
                 + symbol_boost (if symbols match)
                 + path_boost (if path keywords match)
                 + domain_boost (if domain matches)
                 × (1 - test_penalty) (if test file)
```

Default weights: `semantic=0.6, pagerank=0.4, symbol_boost=0.3, path_boost=0.2, test_penalty=0.5`

---

## 3. Core Concepts

### 3.1 Hybrid Ranking

Traditional search uses either keyword matching or semantic similarity. ws-ctx-engine combines **multiple ranking signals**:

| Signal   | What It Captures             | Why It Matters                                   |
| -------- | ---------------------------- | ------------------------------------------------ |
| Semantic | Meaning similarity to query  | Finds conceptually related code                  |
| PageRank | Structural importance        | Ensures core modules are included                |
| Symbol   | Exact identifier matches     | Precise targeting when symbols are named         |
| Path     | Directory/filename relevance | Leverages naming conventions                     |
| Domain   | Keyword-to-directory mapping | Handles conceptual queries like "chunking logic" |

### 3.2 Token Budget Management

ws-ctx-engine treats context packing as an optimization problem:

**Greedy Knapsack Algorithm:**

1. Sort files by importance score (descending)
2. Accumulate files until token budget is reached
3. Reserve 20% of budget for metadata and manifest

```
Token Budget: 100,000
├── Content Budget (80%): 80,000 tokens
│   ├── File 1: 5,000 tokens (score: 0.95)
│   ├── File 2: 3,000 tokens (score: 0.90)
│   ├── File 3: 8,000 tokens (score: 0.85)
│   └── ... (greedy selection continues)
└── Metadata Reserve (20%): 20,000 tokens
    ├── REVIEW_CONTEXT.md manifest
    ├── Directory structure
    └── Dependency hints
```

**Token Counting**: Uses tiktoken with cl100k_base encoding for ±2% accuracy vs actual LLM tokenization.

### 3.3 6-Level Fallback Architecture

ws-ctx-engine **never fails** due to missing dependencies. Each component has automatic fallbacks:

```
Level 1: igraph + NativeLEANN + local embeddings (optimal, 97% storage savings)
  ↓ igraph fails to install (C++ compilation issues)
Level 2: NetworkX + NativeLEANN + local embeddings
  ↓ LEANN library unavailable
Level 3: NetworkX + LEANNIndex + local embeddings
  ↓ LEANNIndex fails
Level 4: NetworkX + FAISS + local embeddings
  ↓ Local embeddings OOM (out of memory)
Level 5: NetworkX + FAISS + API embeddings
  ↓ API fails (network issues, rate limits)
Level 6: File size ranking only (no graph, no embeddings)
```

**Philosophy**: Graceful degradation > hard failure. All transitions are logged with actionable suggestions.

### 3.4 Incremental Indexing

For large repositories, full indexing can take minutes. ws-ctx-engine implements incremental updates:

```
First Index:
  10,000 files → Full AST parsing → Full embedding generation → 5 minutes

Subsequent Indexes:
  50 changed files detected (SHA256 hash comparison)
  → Parse only changed files
  → Update only changed embeddings
  → 10 seconds
```

**Staleness Detection**: Metadata stores file hashes to detect changes automatically.

---

## 4. Output Formats

### 4.1 XML Format (Repomix-style)

Single-file output optimized for paste workflows:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<repository name="my-project" files="25" tokens="48000">
  <metadata>
    <generated>2024-03-25T10:30:00Z</generated>
    <query>authentication logic</query>
  </metadata>

  <file path="src/auth/login.py" tokens="2500" importance="0.95">
def login(username: str, password: str) -> User:
    """Authenticate user and return session."""
    ...
  </file>

  <file path="src/auth/session.py" tokens="1800" importance="0.90">
    ...
  </file>
</repository>
```

**Best for**: Claude.ai paste, ChatGPT one-shot, codebases < 50 files

### 4.2 ZIP Format (Recommended)

Directory structure preserved with manifest:

```
ws-ctx-engine.zip
├── files/
│   ├── src/
│   │   ├── auth/
│   │   │   ├── login.py
│   │   │   └── session.py
│   │   └── models/
│   │       └── user.py
│   └── tests/
│       └── test_auth.py
└── REVIEW_CONTEXT.md
```

**REVIEW_CONTEXT.md** contains:

- Files included with importance scores
- Recommended reading order
- Dependency hints ("login.py imports session.py")
- Query context and selection rationale

**Best for**: Cursor upload, Claude Code, multi-turn workflows, large codebases

---

## 5. Target Use Cases

### 5.1 AI-Assisted Code Review

```bash
# Generate context for PR review
ws-ctx-engine pack /path/to/repo \
  --query "authentication changes" \
  --changed-files pr_diff.txt \
  --format zip
```

The tool will:

1. Boost changed files in ranking
2. Include dependencies of changed files
3. Add transitive dependencies based on PageRank
4. Package with reading order for efficient review

### 5.2 Documentation Generation

```bash
# Select core API files for documentation
ws-ctx-engine pack /path/to/repo \
  --query "public API endpoints and data models" \
  --format zip \
  --budget 80000
```

### 5.3 Bug Investigation

```bash
# Find relevant code for a bug
ws-ctx-engine pack /path/to/repo \
  --query "database connection pooling timeout handling" \
  --format xml \
  --budget 30000
```

### 5.4 Codebase Understanding

```bash
# Understand a new codebase
ws-ctx-engine pack /path/to/repo \
  --query "how does the main processing pipeline work" \
  --format zip
```

---

## 6. Key Differentiators

### vs. Repomix

| Feature              | Repomix    | ws-ctx-engine                |
| -------------------- | ---------- | ---------------------------- |
| Selection            | All files  | Intelligent ranking          |
| Token awareness      | Count only | Budget-constrained selection |
| Dependency awareness | None       | PageRank-based               |
| Semantic search      | None       | Vector similarity            |
| Output formats       | XML only   | XML, ZIP, JSON, YAML, MD     |

### vs. Aider RepoMap

| Feature       | Aider RepoMap   | ws-ctx-engine                  |
| ------------- | --------------- | ------------------------------ |
| Content       | Signatures only | Full file content              |
| Ranking       | PageRank only   | Hybrid (semantic + structural) |
| Query support | Limited         | Natural language queries       |
| Output        | Map only        | Full packaged context          |

### vs. ripmap

| Feature           | ripmap | ws-ctx-engine                         |
| ----------------- | ------ | ------------------------------------- |
| Implementation    | Rust   | Python (with optional Rust extension) |
| Semantic search   | None   | Vector embeddings                     |
| Fallback strategy | None   | 6-level graceful degradation          |
| Output formats    | Text   | Multiple formats                      |

### Unique Strengths

1. **Dual-format Output**: XML (paste) vs ZIP (upload) serves different workflows
2. **Hybrid Ranking**: Semantic + structural ensures no important files are missed
3. **Production Fallbacks**: Never fails due to missing dependencies
4. **Budget-aware**: Precise token counting fits any LLM context window
5. **Agent-ready**: MCP server with security features (PathGuard, RADE, RateLimiter)
6. **Domain Intelligence**: Query classification adapts ranking to query type

---

## 7. Design Philosophy

### "Fail Gracefully, Log Actionably"

Every component has fallbacks. Every fallback transition is logged with:

- What failed
- What fallback was used
- How to fix (install command, config change)

### "Intelligence Over Size"

Selection is based on importance scores, not file size or recency. The goal is maximum information value per token.

### "Production Ready, Not Just a Prototype"

- Comprehensive error handling
- Structured logging with timing
- Performance monitoring
- Security features for agent use

### "Developer AND Agent Friendly"

- CLI for human developers
- MCP server for AI agents
- Consistent output schemas
- Actionable error messages
