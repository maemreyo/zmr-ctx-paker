# Project Overview

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [docs/README.md](file://docs/README.md)
- [docs/reference/architecture.md](file://docs/reference/architecture.md)
- [docs/reference/design-ideas.md](file://docs/reference/design-ideas.md)
- [docs/reference/workflow.md](file://docs/reference/workflow.md)
- [docs/reference/ranking.md](file://docs/reference/ranking.md)
- [docs/reference/budget.md](file://docs/reference/budget.md)
- [docs/reference/packer.md](file://docs/reference/packer.md)
- [docs/guides/output-formats.md](file://docs/guides/output-formats.md)
- [docs/integrations/agent-workflows.md](file://docs/integrations/agent-workflows.md)
- [pyproject.toml](file://pyproject.toml)
- [src/ws_ctx_engine/__init__.py](file://src/ws_ctx_engine/__init__.py)
- [src/ws_ctx_engine/retrieval/retrieval.py](file://src/ws_ctx_engine/retrieval/retrieval.py)
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
10. [Appendices](#appendices)

## Introduction
ws-ctx-engine is an intelligent codebase packaging tool designed to optimize context delivery for Large Language Models (LLMs). Its core value proposition is hybrid ranking that combines semantic search with structural analysis (PageRank) to select the most relevant files within a token budget. This approach ensures that LLMs receive focused, high-value context tailored to the user’s query or task, while maintaining production-grade reliability through comprehensive fallback strategies.

Key benefits for AI-assisted development workflows:
- Hybrid ranking improves precision over pure semantic or structural methods alone.
- Token budget management prevents oversized context windows and wasted tokens.
- Dual output formats (XML and ZIP) serve paste-based and upload-based workflows.
- Production-ready fallbacks ensure robust operation across diverse environments.
- Incremental indexing accelerates repeated operations on large repositories.
- Agent-friendly features (phase-aware modes, semantic deduplication, AI rule persistence) streamline automated workflows.

Practical use cases:
- Code review: Focus on changed files and their dependencies with PageRank-driven coverage.
- Bug investigation: Rapidly surface relevant logic and supporting files around a problem area.
- Documentation generation: Curate representative API and module files for accurate documentation.
- Onboarding: Provide curated entry points and reading order for new team members.

## Project Structure
The repository is organized into:
- Core Python package under src/ws_ctx_engine/, exposing APIs and CLI entry points.
- Comprehensive documentation under docs/ covering architecture, guides, integrations, and reference materials.
- Examples and scripts for demos and CI tasks.
- Tests validating correctness, performance, and resilience.

```mermaid
graph TB
A["Root"] --> B["src/ws_ctx_engine/"]
A --> C["docs/"]
A --> D["examples/"]
A --> E["tests/"]
A --> F["pyproject.toml"]
A --> G["README.md"]
subgraph "Core Package"
B --> B1["cli/"]
B --> B2["workflow/"]
B --> B3["chunker/"]
B --> B4["vector_index/"]
B --> B5["graph/"]
B --> B6["retrieval/"]
B --> B7["budget/"]
B --> B8["packer/"]
B --> B9["ranking/"]
B --> B10["config/"]
B --> B11["logger/"]
B --> B12["errors/"]
B --> B13["models/"]
B --> B14["session/"]
B --> B15["templates/"]
end
subgraph "Docs"
C --> C1["reference/"]
C --> C2["guides/"]
C --> C3["integrations/"]
end
```

**Diagram sources**
- [docs/README.md:1-104](file://docs/README.md#L1-L104)
- [pyproject.toml:138-149](file://pyproject.toml#L138-L149)

**Section sources**
- [docs/README.md:1-104](file://docs/README.md#L1-L104)
- [pyproject.toml:138-149](file://pyproject.toml#L138-L149)

## Core Components
- Hybrid ranking engine: Merges semantic similarity and PageRank scores, then applies query-aware boosts and penalties.
- Token budget manager: Greedy knapsack selection respecting content and metadata budgets.
- Dual output packers: XML (paste) and ZIP (upload) with smart compression and context shuffling.
- Workflow orchestrator: Coordinates indexing and querying, with staleness detection and incremental updates.
- Fallback architecture: Automatic fallback across backends for vector indexing, graph analysis, and embeddings.

Implementation highlights:
- Hybrid ranking formula and adaptive boosting per query type.
- Token budget allocation (80% content, 20% metadata) with tiktoken-based counting.
- Smart compression and context shuffling to improve model recall.
- Session-based semantic deduplication and AI rule file persistence for agents.

**Section sources**
- [docs/reference/architecture.md:182-222](file://docs/reference/architecture.md#L182-L222)
- [docs/reference/budget.md:83-104](file://docs/reference/budget.md#L83-L104)
- [docs/reference/packer.md:38-106](file://docs/reference/packer.md#L38-L106)
- [docs/reference/workflow.md:138-191](file://docs/reference/workflow.md#L138-L191)
- [src/ws_ctx_engine/retrieval/retrieval.py:140-369](file://src/ws_ctx_engine/retrieval/retrieval.py#L140-L369)

## Architecture Overview
The system implements a six-stage pipeline: chunking → indexing → graphing → ranking → selection → packing. Each stage integrates specialized backends with automatic fallbacks, ensuring reliable operation across environments.

```mermaid
graph TB
subgraph "Stage 1: Chunking"
C1["ASTChunker<br/>TreeSitter/Regex"] --> C2["CodeChunk[]"]
end
subgraph "Stage 2: Indexing"
C2 --> I1["VectorIndex<br/>LEANN/FAISS/local embeddings"]
I1 --> I2[".ws-ctx-engine/vector.idx"]
end
subgraph "Stage 3: Graphing"
C2 --> G1["RepoMapGraph<br/>PageRank"]
G1 --> G2[".ws-ctx-engine/graph.pkl"]
end
subgraph "Stage 4: Ranking"
Q1["Query + Changed Files"] --> R1["RetrievalEngine<br/>Hybrid + Boosts"]
R1 --> R2["Dict[str,float]"]
end
subgraph "Stage 5: Selection"
R2 --> B1["BudgetManager<br/>Greedy Knapsack"]
B1 --> B2["SelectedFile[]"]
end
subgraph "Stage 6: Packing"
B2 --> P1["XMLPacker/ZIPPacker<br/>Shuffle + Compression"]
P1 --> O1["Output File<br/>XML/ZIP/JSON/YAML/MD"]
end
I2 -.-> R1
G2 -.-> R1
```

**Diagram sources**
- [docs/reference/architecture.md:76-296](file://docs/reference/architecture.md#L76-L296)
- [docs/reference/workflow.md:17-37](file://docs/reference/workflow.md#L17-L37)

**Section sources**
- [docs/reference/architecture.md:76-296](file://docs/reference/architecture.md#L76-L296)
- [docs/reference/workflow.md:17-37](file://docs/reference/workflow.md#L17-L37)

## Detailed Component Analysis

### Hybrid Ranking Engine
The retrieval engine computes base importance scores by merging normalized semantic and PageRank scores, then applies query-aware boosts and penalties. It classifies queries to adapt boost weights dynamically and ensures AI rule files are always prioritized.

```mermaid
classDiagram
class RetrievalEngine {
+float semantic_weight
+float pagerank_weight
+float symbol_boost
+float path_boost
+float domain_boost
+float test_penalty
+retrieve(query, changed_files, top_k) tuple[]
-_extract_query_tokens(query) set~str~
-_compute_symbol_scores(tokens, file_symbols) dict~str,float~
-_compute_path_scores(tokens, all_files) dict~str,float~
-_compute_domain_scores(tokens, all_files) dict~str,float~
-_classify_query(query, tokens) str
-_effective_weights(query_type) tuple~float~
-_is_test_file(file_path) bool
-_normalize(scores) dict~str,float~
-_merge_scores(semantic, pagerank) dict~str,float~
}
```

**Diagram sources**
- [src/ws_ctx_engine/retrieval/retrieval.py:140-369](file://src/ws_ctx_engine/retrieval/retrieval.py#L140-L369)

**Section sources**
- [src/ws_ctx_engine/retrieval/retrieval.py:140-369](file://src/ws_ctx_engine/retrieval/retrieval.py#L140-L369)
- [docs/reference/ranking.md:46-85](file://docs/reference/ranking.md#L46-L85)

### Token Budget Manager
The budget manager performs greedy knapsack selection to maximize importance within the token budget, allocating 80% for content and reserving 20% for metadata/manifest. It tolerates I/O errors gracefully and provides utilization insights.

```mermaid
flowchart TD
Start(["Start"]) --> ReadRanked["Read Ranked Files"]
ReadRanked --> Loop{"More Files?"}
Loop --> |Yes| CheckReadable["Check File Readable"]
CheckReadable --> |No| Skip["Skip File"] --> Loop
CheckReadable --> |Yes| Count["Count Tokens (tiktoken)"]
Count --> Within{"Within Content Budget?"}
Within --> |Yes| Add["Add to Selection"] --> Loop
Within --> |No| Stop["Stop Selection"]
Loop --> |No| ReturnSel["Return Selected Files + Tokens"]
```

**Diagram sources**
- [docs/reference/budget.md:83-104](file://docs/reference/budget.md#L83-L104)

**Section sources**
- [docs/reference/budget.md:32-104](file://docs/reference/budget.md#L32-L104)

### Output Packer (XML/ZIP)
The packer generates XML (paste) or ZIP (upload) outputs, with context shuffling to combat “Lost in the Middle” and smart compression for low-relevance files. It also supports secret redaction and session-based deduplication.

```mermaid
sequenceDiagram
participant User as "User"
participant Packer as "XMLPacker/ZIPPacker"
participant Shuffle as "shuffle_for_model_recall"
participant Secret as "SecretScanner"
User->>Packer : pack(selected_files, metadata, options)
Packer->>Shuffle : reorder files for recall
Shuffle-->>Packer : shuffled files
Packer->>Secret : scan/redact secrets (optional)
Secret-->>Packer : redacted content
Packer-->>User : output file (XML/ZIP)
```

**Diagram sources**
- [docs/reference/packer.md:38-106](file://docs/reference/packer.md#L38-L106)
- [docs/reference/packer.md:196-294](file://docs/reference/packer.md#L196-L294)

**Section sources**
- [docs/reference/packer.md:107-294](file://docs/reference/packer.md#L107-L294)

### Workflow Orchestration
The workflow module coordinates indexing and querying, with staleness detection and incremental updates. It supports programmatic search and integrates with CLI commands.

```mermaid
sequenceDiagram
participant CLI as "CLI"
participant WF as "Workflow"
participant IDX as "Indexer"
participant RET as "RetrievalEngine"
participant BUD as "BudgetManager"
participant PKR as "Packer"
CLI->>WF : index_repository()
WF->>IDX : parse + index + graph + domain_map
IDX-->>WF : persisted indexes
CLI->>WF : query_and_pack(query, changed_files)
WF->>RET : retrieve(query, changed_files)
RET-->>WF : ranked files
WF->>BUD : select_files(ranked)
BUD-->>WF : selected files
WF->>PKR : pack(selected)
PKR-->>CLI : output path
```

**Diagram sources**
- [docs/reference/workflow.md:269-300](file://docs/reference/workflow.md#L269-L300)

**Section sources**
- [docs/reference/workflow.md:48-191](file://docs/reference/workflow.md#L48-L191)

### Agent Workflows and AI Rule Persistence
Agent workflows leverage phase-aware ranking, semantic deduplication, and persistent AI rule files to ensure consistent, high-quality context delivery across multi-turn interactions.

```mermaid
flowchart TD
A["Agent Session"] --> B["Pack with --mode (discovery/edit/test)"]
B --> C["Apply AI Rule Boost (always top)"]
C --> D["Semantic Deduplication (--session-id)"]
D --> E["Smart Compression (--compress)"]
E --> F["Context Shuffling"]
F --> G["NDJSON Output (stdout)"]
```

**Diagram sources**
- [docs/integrations/agent-workflows.md:8-103](file://docs/integrations/agent-workflows.md#L8-L103)

**Section sources**
- [docs/integrations/agent-workflows.md:8-103](file://docs/integrations/agent-workflows.md#L8-L103)

## Dependency Analysis
Installation tiers and optional dependencies:
- Core: tiktoken, PyYAML, lxml, typer, rich.
- Fast: adds faiss-cpu, networkx, scikit-learn.
- All: adds python-igraph, sentence-transformers, torch, tree-sitter, leann.
- Dev: testing and linting tools.

```mermaid
graph TB
Core["Core"] --> Fast["Fast (faiss-cpu, networkx, sklearn)"]
Fast --> All["All (igraph, transformers, torch, tree-sitter, leann)"]
Core --> Minimal["Minimal (core only)"]
All --> Dev["Dev (pytest, black, ruff, mypy, hypothesis)"]
```

**Diagram sources**
- [pyproject.toml:67-122](file://pyproject.toml#L67-L122)

**Section sources**
- [pyproject.toml:55-122](file://pyproject.toml#L55-L122)

## Performance Considerations
- Primary stack targets: indexing under 5 minutes, query under 10 seconds for 10k files, with minimal memory footprint and compact index storage.
- Fallback backends maintain functionality within 2x of primary performance.
- Incremental indexing detects SHA256 changes and updates only affected files.
- Token counting uses tiktoken cl100k_base with ±2% accuracy versus actual LLM tokenization.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common scenarios and actionable steps:
- Missing optional dependencies: Install the recommended tier (e.g., ws-ctx-engine[all]) or configure backends explicitly.
- Stale indexes: Rebuild automatically or remove .ws-ctx-engine/ to force regeneration.
- Out-of-memory during embeddings: Switch to API embeddings or reduce batch size.
- Slow PageRank: Prefer python-igraph when available; fallback to NetworkX is still fast.
- Emergency mode: File size ranking only when all else fails; install recommended tier for optimal performance.

**Section sources**
- [README.md:386-427](file://README.md#L386-L427)
- [docs/reference/architecture.md:299-371](file://docs/reference/architecture.md#L299-L371)

## Conclusion
ws-ctx-engine delivers a production-ready, agent-friendly solution for packaging codebases into optimized LLM context. Its hybrid ranking, precise token budgeting, dual output formats, and robust fallbacks make it suitable for both human developers and AI agents. The modular architecture, incremental indexing, and comprehensive documentation support rapid adoption and reliable operation across diverse environments.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Practical Use Cases
- Code review: Use pack with changed files to highlight recent modifications and their dependencies.
- Bug investigation: Query for symptoms or error-related logic; adjust token budget for depth.
- Documentation generation: Focus on public APIs and core modules; export ZIP for structured review.
- Onboarding: Provide curated entry points and reading order for new contributors.

**Section sources**
- [README.md:308-346](file://README.md#L308-L346)

### Output Formats Reference
- XML: Repomix-compatible single-file output for paste workflows.
- ZIP: Archive with preserved directory structure and a human-readable manifest.
- JSON/YAML/MD: Structured outputs for programmatic consumption and validation.

**Section sources**
- [docs/guides/output-formats.md:1-131](file://docs/guides/output-formats.md#L1-L131)
- [docs/reference/packer.md:107-294](file://docs/reference/packer.md#L107-L294)