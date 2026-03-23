# Requirements Document

## Introduction

Context Packer là một công cụ Python để đóng gói codebase thành context tối ưu cho Large Language Models (LLMs). Hệ thống sử dụng hybrid ranking (semantic search + PageRank) để chọn files quan trọng nhất, hỗ trợ dual-format output (XML và ZIP), và có fallback strategy cho mọi component để đảm bảo production-ready.

## Glossary

- **Context_Packer**: Hệ thống chính đóng gói codebase thành context cho LLM
- **AST_Chunker**: Component parse source code thành chunks với metadata
- **Vector_Index**: Component thực hiện semantic search trên code chunks
- **RepoMap_Graph**: Component xây dựng dependency graph và tính PageRank
- **Retrieval_Engine**: Component merge semantic và structural scores
- **Budget_Manager**: Component chọn files theo token budget
- **XML_Packer**: Component tạo output format XML (Repomix-style)
- **ZIP_Packer**: Component tạo output format ZIP với file structure
- **Code_Chunk**: Đơn vị code đã parse với metadata (path, symbols, content)
- **Token_Budget**: Giới hạn số tokens cho context window của LLM
- **Importance_Score**: Điểm số kết hợp semantic similarity và PageRank
- **Fallback_Strategy**: Cơ chế tự động chuyển sang backup solution khi primary fails
- **Tree_Sitter**: Primary AST parser với C bindings
- **LEANN**: Primary vector index với 97% storage savings
- **FAISS**: Fallback vector index (faiss-cpu)
- **igraph**: Primary graph library với C++ backend
- **NetworkX**: Fallback graph library (pure Python)
- **Sentence_Transformers**: Local embedding model
- **OpenAI_API**: Fallback embedding service

## Requirements

### Requirement 1: AST Parsing với Tree-Sitter

**User Story:** As a developer, I want to parse source code into structured chunks, so that the system can analyze code semantics and dependencies.

#### Acceptance Criteria

1. WHEN a Python source file is provided, THE AST_Chunker SHALL parse it into Code_Chunks with function and class boundaries
2. WHEN a JavaScript/TypeScript source file is provided, THE AST_Chunker SHALL parse it into Code_Chunks with function and class boundaries
3. WHEN parsing succeeds, THE AST_Chunker SHALL extract symbol definitions (function names, class names) for each Code_Chunk
4. WHEN parsing succeeds, THE AST_Chunker SHALL extract symbol references (imports, function calls) for each Code_Chunk
5. WHEN Tree_Sitter fails to parse a file, THE AST_Chunker SHALL fall back to regex-based parsing
6. WHEN regex parsing is used, THE AST_Chunker SHALL log a warning with the file path
7. FOR ALL valid source files, THE AST_Chunker SHALL complete parsing within 5 seconds per 1000 lines of code

### Requirement 2: Vector Index với LEANN

**User Story:** As a developer, I want semantic search on code chunks, so that I can find relevant code based on natural language queries.

#### Acceptance Criteria

1. WHEN Code_Chunks are provided, THE Vector_Index SHALL build embeddings using Sentence_Transformers model
2. WHEN building with LEANN, THE Vector_Index SHALL store the index with less than 100 MB for 10,000 files
3. WHEN a search query is provided, THE Vector_Index SHALL return top-K Code_Chunks ranked by cosine similarity
4. WHEN LEANN fails to build or import, THE Vector_Index SHALL automatically fall back to FAISS
5. WHEN using FAISS fallback, THE Vector_Index SHALL log the backend switch
6. WHEN Sentence_Transformers fails due to memory, THE Vector_Index SHALL fall back to OpenAI_API embeddings
7. FOR ALL search queries, THE Vector_Index SHALL return results within 2 seconds for a 10,000 file repository

### Requirement 3: RepoMap Graph với PageRank

**User Story:** As a developer, I want to rank files by structural importance, so that core dependencies are prioritized in the context.

#### Acceptance Criteria

1. WHEN Code_Chunks with symbol references are provided, THE RepoMap_Graph SHALL build a directed dependency graph
2. WHEN the graph is built, THE RepoMap_Graph SHALL compute PageRank scores for all files
3. WHEN changed files are specified, THE RepoMap_Graph SHALL boost their PageRank scores
4. WHEN igraph fails to import, THE RepoMap_Graph SHALL automatically fall back to NetworkX
5. WHEN using NetworkX fallback, THE RepoMap_Graph SHALL log the backend switch
6. WHEN computing PageRank with igraph, THE RepoMap_Graph SHALL complete within 1 second for 10,000 nodes
7. WHEN computing PageRank with NetworkX, THE RepoMap_Graph SHALL complete within 10 seconds for 10,000 nodes

### Requirement 4: Hybrid Retrieval Engine

**User Story:** As a developer, I want to combine semantic and structural ranking, so that both relevant and important files are selected.

#### Acceptance Criteria

1. WHEN semantic scores and PageRank scores are available, THE Retrieval_Engine SHALL merge them using configurable weights
2. THE Retrieval_Engine SHALL use default weights of 0.6 for semantic and 0.4 for PageRank
3. WHEN custom weights are provided in configuration, THE Retrieval_Engine SHALL use those weights
4. WHEN merging scores, THE Retrieval_Engine SHALL normalize both score types to [0, 1] range before combining
5. THE Retrieval_Engine SHALL return a ranked list of files with final Importance_Scores
6. FOR ALL score combinations, THE Retrieval_Engine SHALL preserve the relative ordering of top-ranked files

### Requirement 5: Token Budget Management

**User Story:** As a developer, I want to select files that fit within the LLM's context window, so that the packed context doesn't exceed token limits.

#### Acceptance Criteria

1. WHEN files with Importance_Scores are provided, THE Budget_Manager SHALL count tokens using tiktoken
2. WHEN selecting files, THE Budget_Manager SHALL use greedy knapsack algorithm sorted by Importance_Score descending
3. WHEN accumulating files, THE Budget_Manager SHALL stop when 80% of Token_Budget is reached
4. THE Budget_Manager SHALL reserve 20% of Token_Budget for metadata and manifest
5. WHEN token counting, THE Budget_Manager SHALL achieve accuracy within ±2% of actual LLM token count
6. THE Budget_Manager SHALL return the list of selected files with total token count
7. FOR ALL file selections, THE Budget_Manager SHALL maximize total Importance_Score within Token_Budget

### Requirement 6: XML Output Format

**User Story:** As a developer, I want to generate XML output, so that I can paste the context into Claude.ai or ChatGPT for one-shot review.

#### Acceptance Criteria

1. WHEN selected files are provided, THE XML_Packer SHALL generate a single XML file with Repomix-style structure
2. THE XML_Packer SHALL include metadata header with repository name, file count, and total tokens
3. WHEN packing files, THE XML_Packer SHALL wrap each file content in `<file path="...">` tags
4. THE XML_Packer SHALL escape special XML characters in file content
5. THE XML_Packer SHALL include token count for each file in the XML
6. WHEN generating XML, THE XML_Packer SHALL use lxml library for performance
7. FOR ALL generated XML, THE XML_Packer SHALL produce valid XML that passes schema validation

### Requirement 7: ZIP Output Format

**User Story:** As a developer, I want to generate ZIP output with preserved file structure, so that I can upload the context to Cursor or Claude Code for multi-turn workflow.

#### Acceptance Criteria

1. WHEN selected files are provided, THE ZIP_Packer SHALL create a ZIP archive with original directory structure
2. THE ZIP_Packer SHALL include all selected files under a `files/` directory in the ZIP
3. THE ZIP_Packer SHALL generate a `REVIEW_CONTEXT.md` manifest file in the ZIP root
4. WHEN generating manifest, THE ZIP_Packer SHALL list all included files with their Importance_Scores
5. WHEN generating manifest, THE ZIP_Packer SHALL explain why each file was included (changed, dependency, semantic match)
6. WHEN generating manifest, THE ZIP_Packer SHALL suggest a reading order based on Importance_Score
7. THE ZIP_Packer SHALL use Python's zipfile library for ZIP creation

### Requirement 8: Configuration Management

**User Story:** As a developer, I want to configure output format and ranking weights, so that I can customize the tool for different use cases.

#### Acceptance Criteria

1. THE Context_Packer SHALL read configuration from `.context-pack.yaml` file in the repository root
2. WHEN configuration file is missing, THE Context_Packer SHALL use default configuration values
3. THE Context_Packer SHALL support configuration of output format (xml or zip)
4. THE Context_Packer SHALL support configuration of Token_Budget (default 100,000)
5. THE Context_Packer SHALL support configuration of semantic_weight and pagerank_weight
6. THE Context_Packer SHALL support configuration of include_patterns and exclude_patterns for file filtering
7. THE Context_Packer SHALL support configuration of backend selection (auto, primary, or fallback) for each component
8. WHEN invalid configuration is provided, THE Context_Packer SHALL log an error and use default values

### Requirement 9: Incremental Indexing

**User Story:** As a developer, I want to build indexes once and reuse them, so that subsequent queries are fast without re-indexing.

#### Acceptance Criteria

1. WHEN indexing is complete, THE Context_Packer SHALL save Vector_Index to `.context-pack/vector.idx`
2. WHEN indexing is complete, THE Context_Packer SHALL save RepoMap_Graph to `.context-pack/graph.pkl`
3. WHEN starting a query, THE Context_Packer SHALL load existing indexes if they exist
4. WHEN loading indexes, THE Context_Packer SHALL auto-detect the backend used (LEANN vs FAISS, igraph vs NetworkX)
5. WHEN repository files have changed, THE Context_Packer SHALL detect stale indexes based on file modification times
6. WHEN indexes are stale, THE Context_Packer SHALL rebuild them automatically
7. FOR ALL index operations, THE Context_Packer SHALL complete loading within 5 seconds

### Requirement 10: Fallback Strategy Execution

**User Story:** As a developer, I want automatic fallback to backup solutions, so that the tool never fails due to missing dependencies.

#### Acceptance Criteria

1. WHEN a primary backend fails to import, THE Context_Packer SHALL automatically switch to the fallback backend
2. WHEN switching backends, THE Context_Packer SHALL log a warning with the component name and reason
3. WHEN all backends fail for a component, THE Context_Packer SHALL degrade gracefully to a simpler algorithm
4. IF Vector_Index fails completely, THEN THE Context_Packer SHALL fall back to TF-IDF ranking
5. IF RepoMap_Graph fails completely, THEN THE Context_Packer SHALL fall back to file size ranking
6. THE Context_Packer SHALL continue execution with degraded functionality rather than failing
7. WHEN using fallback backends, THE Context_Packer SHALL still meet performance targets within 2x of primary backend

### Requirement 11: CLI Interface

**User Story:** As a developer, I want a command-line interface, so that I can easily run the tool from my terminal or CI/CD pipeline.

#### Acceptance Criteria

1. THE Context_Packer SHALL provide a `context-pack` CLI command
2. WHEN running `context-pack index <repo_path>`, THE Context_Packer SHALL build and save indexes
3. WHEN running `context-pack query <query_text>`, THE Context_Packer SHALL search and generate output
4. WHEN running `context-pack pack <repo_path>`, THE Context_Packer SHALL perform full workflow (index + query + pack)
5. THE Context_Packer SHALL support `--format` flag to specify output format (xml or zip)
6. THE Context_Packer SHALL support `--budget` flag to specify Token_Budget
7. THE Context_Packer SHALL support `--config` flag to specify custom configuration file path
8. WHEN CLI execution completes, THE Context_Packer SHALL exit with status code 0 on success and non-zero on failure

### Requirement 12: Error Handling and Logging

**User Story:** As a developer, I want clear error messages and logs, so that I can debug issues and understand what the tool is doing.

#### Acceptance Criteria

1. WHEN an error occurs, THE Context_Packer SHALL log the error with file path, line number, and stack trace
2. WHEN a fallback is triggered, THE Context_Packer SHALL log a warning with the reason and fallback backend used
3. THE Context_Packer SHALL log progress messages for long-running operations (parsing, indexing, ranking)
4. THE Context_Packer SHALL support log levels (DEBUG, INFO, WARNING, ERROR)
5. WHEN running in verbose mode, THE Context_Packer SHALL log detailed timing information for each phase
6. THE Context_Packer SHALL write logs to both console and a log file in `.context-pack/logs/`
7. WHEN an unrecoverable error occurs, THE Context_Packer SHALL provide actionable suggestions for fixing the issue

### Requirement 13: Performance Monitoring

**User Story:** As a developer, I want to track performance metrics, so that I can verify the tool meets performance targets.

#### Acceptance Criteria

1. WHEN indexing completes, THE Context_Packer SHALL report total time, files processed, and index size
2. WHEN query completes, THE Context_Packer SHALL report query time, files selected, and total tokens
3. THE Context_Packer SHALL track memory usage during indexing and query phases
4. WHEN using primary backends, THE Context_Packer SHALL complete indexing within 5 minutes for 10,000 files
5. WHEN using fallback backends, THE Context_Packer SHALL complete indexing within 10 minutes for 10,000 files
6. WHEN querying, THE Context_Packer SHALL return results within 10 seconds for primary backends
7. WHEN querying, THE Context_Packer SHALL return results within 15 seconds for fallback backends

### Requirement 14: Parser Round-Trip Property

**User Story:** As a developer, I want to verify AST parsing correctness, so that I can trust the extracted code structure.

#### Acceptance Criteria

1. THE Context_Packer SHALL provide a Pretty_Printer component for formatting Code_Chunks back to source code
2. WHEN a valid Python file is parsed, THE Pretty_Printer SHALL format the Code_Chunks back to valid Python
3. WHEN a valid JavaScript file is parsed, THE Pretty_Printer SHALL format the Code_Chunks back to valid JavaScript
4. FOR ALL valid source files, parsing then printing then parsing SHALL produce equivalent Code_Chunks (round-trip property)
5. WHEN round-trip fails, THE Context_Packer SHALL log a warning with the file path and differences detected
6. THE Context_Packer SHALL include round-trip tests in the test suite for all supported languages

### Requirement 15: Integration Testing

**User Story:** As a developer, I want end-to-end integration tests, so that I can verify the complete workflow works correctly.

#### Acceptance Criteria

1. THE Context_Packer SHALL include integration tests for the full workflow (index → query → pack)
2. WHEN running integration tests, THE Context_Packer SHALL test both XML and ZIP output formats
3. WHEN running integration tests, THE Context_Packer SHALL test both primary and fallback backends
4. WHEN running integration tests, THE Context_Packer SHALL verify output token counts are within budget
5. WHEN running integration tests, THE Context_Packer SHALL verify selected files have highest Importance_Scores
6. THE Context_Packer SHALL include integration tests for error scenarios (missing files, invalid config)
7. FOR ALL integration tests, THE Context_Packer SHALL complete within 60 seconds on a standard development machine
