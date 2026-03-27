# CLI Reference

<cite>
**Referenced Files in This Document**
- [cli.py](file://src/ws_ctx_engine/cli/cli.py)
- [cli.md](file://docs/reference/cli.md)
- [output-formats.md](file://docs/guides/output-formats.md)
- [budget.md](file://docs/reference/budget.md)
- [config.md](file://docs/reference/config.md)
- [config.py](file://src/ws_ctx_engine/config/config.py)
- [packer.md](file://docs/reference/packer.md)
- [ranking.md](file://docs/reference/ranking.md)
- [logging.md](file://docs/guides/logging.md)
- [cozo_store.py](file://src/ws_ctx_engine/graph/cozo_store.py)
- [metrics.py](file://src/ws_ctx_engine/graph/metrics.py)
- [tools.py](file://src/ws_ctx_engine/mcp/tools.py)
- [__init__.py](file://src/ws_ctx_engine/workflow/__init__.py)
- [__init__.py](file://src/ws_ctx_engine/packer/__init__.py)
</cite>

## Update Summary
**Changes Made**
- Added new `graph` sub-application with dedicated backup command
- Enhanced `status` command with comprehensive graph store health reporting
- Added graph store management capabilities with node counts, edge statistics, and health metrics
- Updated configuration to support graph store settings and persistence options

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Command Reference](#detailed-command-reference)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document is the comprehensive CLI reference for ws-ctx-engine. It documents all commands, their parameters, options, and usage patterns. It explains output formats, token budget management, compression, shuffling, agent-phase modes, configuration integration, logging, and error handling. Practical workflows for code review, bug investigation, and documentation generation are included, along with troubleshooting and performance optimization guidance.

**Updated** The CLI now includes a dedicated graph sub-application with backup functionality and enhanced status reporting with graph store health information, node counts, and edge statistics.

## Project Structure
The CLI is implemented as a Typer application with subcommands for doctor, index, search, query, pack, status, vacuum, reindex-domain, init-config, mcp, session management, and the new graph sub-application. The CLI delegates to workflow functions and integrates with configuration, packer, ranking, logger, and graph store modules.

```mermaid
graph TB
CLI["CLI App (Typer)"] --> Doctor["doctor"]
CLI --> Index["index"]
CLI --> Search["search"]
CLI --> Query["query"]
CLI --> Pack["pack"]
CLI --> Status["status"]
CLI --> Vacuum["vacuum"]
CLI --> ReindexDomain["reindex-domain"]
CLI --> InitConfig["init-config"]
CLI --> MCP["mcp"]
CLI --> Session["session.clear"]
CLI --> Graph["graph.backup"]
Graph --> GraphStore["GraphStore (CozoDB)"]
Index --> WFIndex["workflow.index_repository"]
Search --> WFSearch["workflow.search_codebase"]
Query --> WFQuery["workflow.query_and_pack"]
Pack --> WFQuery2["workflow.query_and_pack"]
Status --> Stats["index metadata reader"]
Status --> GraphStats["Graph store health reporter"]
Vacuum --> DB["DomainMapDB (SQLite)"]
ReindexDomain --> WFIndex2["workflow.indexer (domain_only)"]
InitConfig --> SmartCfg["_build_smart_config"]
MCP --> MCPServer["mcp_server.run_mcp_server"]
Session --> Dedup["session.dedup_cache.SessionDeduplicationCache"]
GraphStore --> Metrics["GraphMetrics"]
GraphStore --> Cozo["CozoDB Storage"]
```

**Diagram sources**
- [cli.py:329-1792](file://src/ws_ctx_engine/cli/cli.py#L329-L1792)
- [cozo_store.py:1-364](file://src/ws_ctx_engine/graph/cozo_store.py#L1-L364)
- [metrics.py:1-33](file://src/ws_ctx_engine/graph/metrics.py#L1-L33)
- [__init__.py:1-5](file://src/ws_ctx_engine/workflow/__init__.py#L1-L5)
- [__init__.py:1-9](file://src/ws_ctx_engine/packer/__init__.py#L1-L9)

**Section sources**
- [cli.py:27-62](file://src/ws_ctx_engine/cli/cli.py#L27-L62)

## Core Components
- CLI Application: Typer-based app with callbacks for global options and subcommands.
- Configuration: Dataclass-backed Config with YAML loading, validation, and defaults.
- Workflow: Indexing, search, and query-and-pack orchestration.
- Packer: Output generation in XML, ZIP, JSON, YAML, MD, and experimental TOON.
- Ranking: AI rule boost and phase-aware adjustments.
- Logger: Structured dual-output logging (console + file) with levels and metrics.
- Session Dedup: Best-effort semantic deduplication cache for agent sessions.
- Graph Store: Persistent graph storage with health monitoring and backup capabilities.

**Updated** The graph store provides persistent storage for code relationships with health monitoring, metrics collection, and backup functionality.

**Section sources**
- [cli.py:22-36](file://src/ws_ctx_engine/cli/cli.py#L22-L36)
- [config.py:16-111](file://src/ws_ctx_engine/config/config.py#L16-L119)
- [cozo_store.py:1-364](file://src/ws_ctx_engine/graph/cozo_store.py#L1-L364)
- [metrics.py:1-33](file://src/ws_ctx_engine/graph/metrics.py#L1-L33)
- [__init__.py:1-5](file://src/ws_ctx_engine/workflow/__init__.py#L1-L5)
- [packer.md:1-27](file://docs/reference/packer.md#L1-L27)
- [ranking.md:1-16](file://docs/reference/ranking.md#L1-L16)
- [logging.md:81-100](file://docs/guides/logging.md#L81-L100)

## Architecture Overview
The CLI orchestrates three major phases:
1. Indexing: Builds vector and graph indexes.
2. Retrieval: Searches indexes and ranks files.
3. Packing: Selects files by token budget, optionally shuffles and compresses, and writes output.

**Updated** The architecture now includes graph store management with backup capabilities and enhanced status reporting.

```mermaid
sequenceDiagram
participant U as "User"
participant CLI as "CLI"
participant CFG as "Config"
participant WF as "Workflow"
participant GS as "GraphStore"
participant PK as "Packer"
U->>CLI : "ws-ctx-engine graph backup <dest>"
CLI->>CFG : "_load_config()"
CLI->>GS : "Load graph store"
GS->>GS : "Check health & stats"
GS-->>CLI : "Node/edge counts, metrics"
CLI->>CLI : "Backup to destination"
CLI-->>U : "Success message with size"
U->>CLI : "ws-ctx-engine status <repo>"
CLI->>CFG : "_load_config()"
CLI->>GS : "Load graph store"
GS->>GS : "Collect stats"
GS-->>CLI : "Health, node_count, edge_count"
CLI-->>U : "Enhanced status report"
```

**Diagram sources**
- [cli.py:1686-1735](file://src/ws_ctx_engine/cli/cli.py#L1686-L1735)
- [cli.py:1210-1364](file://src/ws_ctx_engine/cli/cli.py#L1210-L1364)
- [cozo_store.py:142-162](file://src/ws_ctx_engine/graph/cozo_store.py#L142-L162)
- [metrics.py:26-33](file://src/ws_ctx_engine/graph/metrics.py#L26-L33)

## Detailed Command Reference

### Global Options
- --version, -V: Print version and exit.
- --agent-mode: Emit NDJSON on stdout; send human-readable logs to stderr.
- --quiet/--no-quiet: Suppress informational logs; show only warnings and errors.

These options are handled by the CLI callback and affect logging verbosity and output mode.

**Section sources**
- [cli.py:376-403](file://src/ws_ctx_engine/cli/cli.py#L376-L403)

### doctor
Purpose: Check optional dependencies and recommend installation tiers.

Usage:
- ws-ctx-engine doctor

Behavior:
- Reports presence/absence of recommended packages.
- On missing packages, suggests installing the full feature set.

Output:
- Human-readable table of dependencies and recommendations.
- Exit code 0 if all recommended packages present; 1 otherwise.

**Section sources**
- [cli.py:329-363](file://src/ws_ctx_engine/cli/cli.py#L329-L363)
- [cli.md:51-78](file://docs/reference/cli.md#L51-L78)

### index
Purpose: Build and save indexes for a repository.

Usage:
- ws-ctx-engine index <repo_path> [--config PATH | -c PATH] [--verbose | -v] [--incremental]

Arguments:
- repo_path: Path to the repository root directory.

Options:
- --config PATH, -c PATH: Path to custom configuration file.
- --verbose, -v: Enable verbose logging with detailed timing.
- --incremental: Only re-index files changed since last build.

Behavior:
- Validates repo path existence and directory.
- Preflight checks runtime dependencies.
- Calls workflow.index_repository with optional incremental mode.
- Emits NDJSON status on success.

Common workflows:
- Initial setup: doctor → init-config → index
- Post-changes: index --incremental

**Section sources**
- [cli.py:405-501](file://src/ws_ctx_engine/cli/cli.py#L405-L501)
- [cli.md:82-116](file://docs/reference/cli.md#L82-L116)

### search
Purpose: Search the indexed codebase and return ranked file paths.

Usage:
- ws-ctx-engine search "<query>" [--repo PATH | -r PATH] [--limit N | -l N] [--domain-filter STR] [--config PATH | -c PATH] [--verbose | -v] [--agent-mode]

Arguments:
- query: Natural language query for semantic search.

Options:
- --repo PATH, -r PATH: Repository root (default: current directory).
- --limit N, -l N: Maximum results (1-50).
- --domain-filter STR: Optional domain filter.
- --config PATH, -c PATH: Custom config path.
- --verbose, -v: Enable verbose logging.
- --agent-mode: Emit NDJSON metadata and results.

Behavior:
- Validates repo path.
- Preflight checks dependencies.
- Calls workflow.search_codebase and prints results or emits NDJSON.

**Section sources**
- [cli.py:503-644](file://src/ws_ctx_engine/cli/cli.py#L503-L644)
- [cli.md:119-156](file://docs/reference/cli.md#L119-L156)

### query
Purpose: Search indexes and generate output in the configured format.

Usage:
- ws-ctx-engine query "<query>" [--repo PATH | -r PATH] [--format FORMAT | -f FORMAT] [--budget N | -b N] [--config PATH | -c PATH] [--verbose | -v] [--secrets-scan] [--agent-mode] [--stdout] [--copy] [--compress] [--shuffle | --no-shuffle] [--mode discovery|edit|test] [--session-id ID] [--no-dedup]

Arguments:
- query: Natural language query for semantic search.

Options:
- --repo PATH, -r PATH: Repository root.
- --format FORMAT, -f FORMAT: Output format: xml, zip, json, yaml, md, toon.
- --budget N, -b N: Token budget for context window.
- --config PATH, -c PATH: Custom config path.
- --verbose, -v: Enable verbose logging.
- --secrets-scan: Enable secret scanning and redaction.
- --agent-mode: Emit NDJSON status.
- --stdout: Write output to stdout instead of file.
- --copy: Copy output to clipboard after packing.
- --compress: Apply smart compression.
- --shuffle/--no-shuffle: Reorder files to combat "Lost in the Middle."
- --mode discovery|edit|test: Adjust ranking weights for agent phases.
- --session-id ID: Session identifier for semantic deduplication.
- --no-dedup: Disable session-level semantic deduplication.

Behavior:
- Validates format and budget.
- Preflight checks dependencies.
- Calls workflow.query_and_pack with compression, shuffling, mode, and session options.
- Prints summary and output path; copies to clipboard if requested.

Practical examples:
- Code review: query "authentication logic" --format xml --compress
- Bug investigation: query "error handling" --budget 50000 --copy
- Documentation generation: query "API endpoints" --format md

**Section sources**
- [cli.py:697-931](file://src/ws_ctx_engine/cli/cli.py#L697-L931)
- [cli.md:159-206](file://docs/reference/cli.md#L159-L206)
- [output-formats.md:1-131](file://docs/guides/output-formats.md#L1-L131)
- [packer.md:295-351](file://docs/reference/packer.md#L295-L351)
- [ranking.md:36-86](file://docs/reference/ranking.md#L36-L86)

### pack
Purpose: Execute full pipeline: index, query, and pack.

Usage:
- ws-ctx-engine pack [repo_path] [--query QUERY | -q QUERY] [--changed-files PATH] [--format FORMAT | -f FORMAT] [--budget N | -b N] [--config PATH | -c PATH] [--verbose | -v] [--secrets-scan] [--agent-mode] [--stdout] [--copy] [--compress] [--shuffle | --no-shuffle] [--mode discovery|edit|test] [--session-id ID] [--no-dedup]

Arguments:
- repo_path: Repository root (default: current directory).

Options:
- --query QUERY, -q QUERY: Natural language query for semantic search.
- --changed-files PATH: Path to a file listing changed files (one per line) for PageRank boosting.
- Other options mirror query command.

Behavior:
- Loads config and validates formats/budgets.
- Checks/creates indexes automatically.
- Executes query and pack steps with the same options as query.
- Supports stdout, copy, and NDJSON status.

Practical examples:
- CI/CD review: git diff --name-only | ws-ctx-engine pack . -q "review changes" --format xml
- Production workflow: pack . -q "API layer" --format xml --compress --shuffle

**Section sources**
- [cli.py:934-1195](file://src/ws_ctx_engine/cli/cli.py#L934-L1195)
- [cli.md:210-256](file://docs/reference/cli.md#L210-L256)

### status
Purpose: Show index status and statistics with enhanced graph store reporting.

Usage:
- ws-ctx-engine status <repo_path> [--config PATH | -c PATH] [--agent-mode]

Behavior:
- Validates repo path and index presence.
- Reads metadata.json and computes sizes.
- **Updated** Displays comprehensive graph store health information including node counts, edge statistics, and schema version.
- Prints human-friendly stats or emits NDJSON.

**Updated** The status command now provides detailed graph store information:
- Graph store availability and health status
- Node count and edge count statistics
- Schema version information
- Query metrics (query_count, error_count, average latency)
- Overall readiness indicators (vector + graph, vector only, or no)

**Section sources**
- [cli.py:1210-1364](file://src/ws_ctx_engine/cli/cli.py#L1210-L1364)
- [cli.md:260-298](file://docs/reference/cli.md#L260-L298)
- [cozo_store.py:142-162](file://src/ws_ctx_engine/graph/cozo_store.py#L142-L162)
- [metrics.py:26-33](file://src/ws_ctx_engine/graph/metrics.py#L26-L33)

### vacuum
Purpose: Optimize SQLite database by running VACUUM.

Usage:
- ws-ctx-engine vacuum <repo_path> [--config PATH | -c PATH]

Behavior:
- Requires domain_map.db; runs VACUUM and reports new size.

**Section sources**
- [cli.py:1375-1459](file://src/ws_ctx_engine/cli/cli.py#L1375-L1459)
- [cli.md:301-326](file://docs/reference/cli.md#L301-L326)

### reindex-domain
Purpose: Rebuild only the domain map database (SQLite).

Usage:
- ws-ctx-engine reindex-domain <repo_path> [--config PATH | -c PATH]

Behavior:
- Rebuilds domain_map.db without touching vector/graph indexes.

**Section sources**
- [cli.py:1462-1525](file://src/ws_ctx_engine/cli/cli.py#L1462-L1525)
- [cli.md:330-351](file://docs/reference/cli.md#L330-L351)

### init-config
Purpose: Generate a smart .ws-ctx-engine.yaml for the repository.

Usage:
- ws-ctx-engine init-config [repo_path] [--force] [--include-gitignore | --no-include-gitignore] [--vector-index auto|native-leann|leann|faiss] [--graph auto|igraph|networkx] [--embeddings auto|local|api]

Behavior:
- Builds a payload with exclude patterns, backends, and preferences.
- Writes .ws-ctx-engine.yaml and updates .gitignore with ws-ctx-engine artifact patterns.

**Section sources**
- [cli.py:1528-1600](file://src/ws_ctx_engine/cli/cli.py#L1528-L1600)
- [cli.md:354-386](file://docs/reference/cli.md#L354-L386)

### mcp
Purpose: Run ws-ctx-engine as an MCP stdio server.

Usage:
- ws-ctx-engine mcp [--workspace PATH | -w PATH] [--mcp-config PATH] [--rate-limit TOOL=N]

Behavior:
- Starts MCP server bound to a workspace with optional rate limits.
- Parses rate-limit entries as TOOL=LIMIT.

**Section sources**
- [cli.py:646-694](file://src/ws_ctx_engine/cli/cli.py#L646-L694)
- [cli.md:390-414](file://docs/reference/cli.md#L390-L414)

### session clear
Purpose: Delete session-level semantic deduplication cache files.

Usage:
- ws-ctx-engine session clear [repo_path] [--session-id ID]

Behavior:
- Clears a specific session cache or all session caches in .ws-ctx-engine.

**Section sources**
- [cli.py:1746-1769](file://src/ws_ctx_engine/cli/cli.py#L1746-L1769)
- [cli.md:418-446](file://docs/reference/cli.md#L418-L446)

### graph backup
Purpose: Back up the graph store to a destination directory.

Usage:
- ws-ctx-engine graph backup <dest> [--workspace PATH | -w PATH]

Arguments:
- dest: Destination directory for the backup.

Options:
- --workspace PATH, -w PATH: Workspace path (defaults to current directory).

Behavior:
- **New** Validates graph store configuration and health.
- **New** Supports RocksDB and SQLite persistent storage backends.
- **New** Provides graceful error handling for missing sources, existing destinations, and memory stores.
- **New** Copies graph store data and reports backup size.

**Updated** The graph backup command provides:
- Memory store detection and appropriate error messages
- Source path validation and workspace resolution
- Destination existence checking
- Robust error handling with clear failure messages
- Backup size reporting in kilobytes

**Section sources**
- [cli.py:1686-1735](file://src/ws_ctx_engine/cli/cli.py#L1686-L1735)

## Dependency Analysis
Runtime dependency preflight resolves backends and validates environment requirements. It supports auto-selection among available modules and reports warnings/errors.

```mermaid
flowchart TD
Start(["Load Config"]) --> CheckEmbeddings["Check embeddings backend"]
CheckEmbeddings --> Local{"embeddings=local?"}
Local --> |Yes| ST["sentence-transformers required"]
Local --> |No| API{"embeddings=api?"}
API --> |Yes| OA["openai + api_key_env required"]
API --> |No| AutoEmb["auto: choose local or api if available"]
Start --> CheckVector["Check vector_index backend"]
CheckVector --> NativeLeann{"native-leann?"}
NativeLeann --> |Yes| LeannDep["leann required"]
NativeLeann --> |No| FAISS{"faiss?"}
FAISS --> |Yes| FAISSDep["faiss-cpu required"]
FAISS --> |No| AutoVec["auto: choose leann or faiss if available"]
Start --> CheckGraph["Check graph backend"]
CheckGraph --> IGraph{"igraph?"}
IGraph --> |Yes| IGraphDep["python-igraph required"]
IGraph --> |No| NX{"networkx?"}
NX --> |Yes| NXDep["networkx required"]
NX --> |No| AutoGr["auto: choose igraph or networkx if available"]
Start --> CheckGraphStore["Check graph store settings"]
CheckGraphStore --> RocksDB{"rocksdb?"}
RocksDB --> |Yes| RocksDep["pycozo required"]
RocksDB --> |No| SQLite{"sqlite?"}
SQLite --> |Yes| SQLiteDep["pycozo required"]
SQLite --> |No| Mem{"mem?"}
Mem --> |Yes| NoDep["No external deps"]
Start --> CheckGraphStore
ST --> ResolveEmb["Resolve embeddings backend"]
OA --> ResolveEmb
AutoEmb --> ResolveEmb
LeannDep --> ResolveVec["Resolve vector_index backend"]
FAISSDep --> ResolveVec
AutoVec --> ResolveVec
IGraphDep --> ResolveGr["Resolve graph backend"]
NXDep --> ResolveGr
AutoGr --> Done(["Proceed"])
```

**Diagram sources**
- [cli.py:256-326](file://src/ws_ctx_engine/cli/cli.py#L256-L326)

**Section sources**
- [cli.py:256-326](file://src/ws_ctx_engine/cli/cli.py#L256-L326)

## Performance Considerations
- Token budget: Tune token_budget to match your LLM's context window. The Budget module reserves ~80% for content and 20% for metadata/manifest.
- Compression: Use --compress to reduce output size by retaining full content for high-relevance files and signatures for others.
- Shuffling: Enable --shuffle to improve recall by placing top-ranked files at both ends of the context window.
- Incremental indexing: Use --incremental to re-index only changed files after initial index.
- Backend selection: Auto-resolution chooses the fastest available backends; install recommended packages for optimal performance.
- Verbosity: Use --verbose to capture timing metrics for profiling.
- **Updated** Graph store performance: Monitor node_count and edge_count in status output to gauge graph complexity. Use --verbose for detailed timing metrics.

## Troubleshooting Guide
Common issues and resolutions:
- Repository path not found or not a directory: Ensure the path exists and is a directory.
- Indexes not found: Run ws-ctx-engine index first to build indexes.
- Invalid format or budget: Verify --format is one of xml, zip, json, yaml, md, toon and --budget is positive.
- Dependency errors: Run ws-ctx-engine doctor to check required packages; install recommended extras.
- Permission errors: Ensure write permissions to .ws-ctx-engine and output directories.
- Clipboard issues: Some systems lack clipboard tools; the CLI warns and continues.
- **Updated** Graph store backup failures: Check that graph_store_storage is not "mem" and that source path exists. Ensure destination directory does not already exist.

Logging:
- Dual output: Console shows INFO and above; file captures DEBUG and above with structured timestamps.
- Verbose mode: Adds detailed timing for phases.
- Error context: Includes stack traces and contextual metadata.

**Section sources**
- [cli.py:446-500](file://src/ws_ctx_engine/cli/cli.py#L446-L500)
- [cli.py:632-643](file://src/ws_ctx_engine/cli/cli.py#L632-L643)
- [cli.py:810-822](file://src/ws_ctx_engine/cli/cli.py#L810-L822)
- [cli.py:1052-1064](file://src/ws_ctx_engine/cli/cli.py#L1052-L1064)
- [cli.py:1714-1735](file://src/ws_ctx_engine/cli/cli.py#L1714-L1735)
- [logging.md:81-100](file://docs/guides/logging.md#L81-L100)

## Conclusion
The ws-ctx-engine CLI provides a complete toolkit for indexing, searching, and packaging repository context for LLMs. With flexible output formats, token-aware budgeting, compression, shuffling, and agent-phase modes, it supports diverse workflows from code review to documentation generation. **Updated** The new graph sub-application enhances operational capabilities with backup functionality and comprehensive status reporting. Use configuration files, logging, and the dependency doctor to tailor performance and reliability to your environment.

## Appendices

### Output Formats and Use Cases
- XML: Repomix-compatible with CDATA sections; ideal for interoperability.
- ZIP: Archive with preserved structure and a human-readable manifest; ideal for offline review.
- JSON: Structured data for programmatic consumption.
- YAML: Human-readable variant of JSON.
- MD: Markdown output for lightweight documentation tasks.
- TOON: Experimental format (use with caution).

**Section sources**
- [output-formats.md:1-131](file://docs/guides/output-formats.md#L1-L131)
- [config.md:99-103](file://docs/reference/config.md#L99-L103)

### Token Budget Management
- Default budget: 100,000 tokens.
- Allocation: ~80% content, ~20% metadata/manifest.
- Accuracy: ±2% compared to API tokenizers.

**Section sources**
- [budget.md:106-116](file://docs/reference/budget.md#L106-L116)
- [config.md:99-103](file://docs/reference/config.md#L99-L103)

### Advanced Options Summary
- --mode discovery/edit/test: Adjusts ranking weights for agent phases.
- --session-id and --no-dedup: Control semantic deduplication cache behavior.
- --changed-files: Boost PageRank for specified files.
- --rate-limit: MCP server rate limiting (TOOL=LIMIT).
- --agent-mode: NDJSON output for programmatic consumption.

**Section sources**
- [cli.py:854-859](file://src/ws_ctx_engine/cli/cli.py#L854-L859)
- [cli.py:1096-1101](file://src/ws_ctx_engine/cli/cli.py#L1096-L1101)
- [cli.py:677-680](file://src/ws_ctx_engine/cli/cli.py#L677-L680)
- [cli.py:1752-1756](file://src/ws_ctx_engine/cli/cli.py#L1752-L1756)

### Graph Store Configuration
**New** The graph store provides persistent storage for code relationships with the following configuration options:

- graph_store_enabled: Enable/disable graph store functionality
- graph_store_storage: Storage backend ("mem", "rocksdb", or "sqlite")
- graph_store_path: Path to graph store data directory

**Section sources**
- [config.py:115-119](file://src/ws_ctx_engine/config/config.py#L115-L119)
- [cozo_store.py:41-56](file://src/ws_ctx_engine/graph/cozo_store.py#L41-L56)

### Graph Store Health Monitoring
**New** The graph store includes comprehensive health monitoring and metrics:

- Node count and edge count statistics
- Schema version tracking
- Query metrics (query_count, error_count, average latency)
- Health status reporting
- Graceful degradation when unhealthy

**Section sources**
- [cozo_store.py:142-162](file://src/ws_ctx_engine/graph/cozo_store.py#L142-L162)
- [metrics.py:8-33](file://src/ws_ctx_engine/graph/metrics.py#L8-L33)