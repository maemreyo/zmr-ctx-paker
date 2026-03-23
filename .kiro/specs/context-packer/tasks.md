# Implementation Plan: Context Packer

## Overview

This implementation plan follows a Test-Driven Development (TDD) approach, building Context Packer incrementally with property-based tests validating the 41 correctness properties from the design document. The system will be implemented in Python 3.11+ with comprehensive fallback strategies for production reliability.

## Tasks

- [ ] 1. Project setup and infrastructure
  - [ ] 1.1 Create Python package structure with pyproject.toml
    - Set up package metadata (name, version, dependencies)
    - Configure build system (setuptools or poetry)
    - Define dependency tiers: core, fast, all
    - _Requirements: 8.1, 11.1_

  - [ ] 1.2 Configure testing framework with pytest and hypothesis
    - Install pytest, hypothesis, pytest-benchmark
    - Create conftest.py with hypothesis profiles (ci, dev, debug)
    - Set up test directory structure (unit/, property/, integration/)
    - _Requirements: 15.1, 15.2_

  - [ ] 1.3 Set up logging infrastructure
    - Implement ContextPackerLogger with dual output (console + file)
    - Configure log levels and structured formatting
    - Create .context-pack/logs/ directory
    - _Requirements: 12.1, 12.4, 12.6_

  - [ ] 1.4 Create configuration management system
    - Define Config dataclass with all settings
    - Implement YAML loading with default fallback
    - Add validation for configuration values
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

- [ ] 2. Core data models
  - [ ] 2.1 Implement CodeChunk dataclass
    - Define fields: path, start_line, end_line, content, symbols_defined, symbols_referenced, language
    - Add token_count method using tiktoken
    - _Requirements: 1.1, 1.3, 1.4, 5.1_

  - [ ] 2.2 Implement IndexMetadata dataclass
    - Define fields: created_at, repo_path, file_count, backend, file_hashes
    - Add is_stale method for staleness detection
    - _Requirements: 9.5, 9.6_

  - [ ]* 2.3 Write property test for token counting consistency
    - **Property 12: Token Counting Consistency**
    - **Validates: Requirements 5.1**
    - Test that tiktoken produces same count for same content

- [ ] 3. AST Chunker implementation
  - [ ] 3.1 Implement ASTChunker abstract base class
    - Define parse() abstract method
    - _Requirements: 1.1_

  - [ ] 3.2 Implement TreeSitterChunker with py-tree-sitter
    - Parse Python, JavaScript, TypeScript files
    - Extract function and class boundaries
    - Extract symbol definitions and references
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 3.3 Implement RegexChunker as fallback
    - Use regex patterns for basic function/class detection
    - Support Python, JavaScript, TypeScript
    - _Requirements: 1.5_

  - [ ] 3.4 Add fallback logic with error handling
    - Try TreeSitterChunker first, fall back to RegexChunker on failure
    - Log warning when fallback is triggered
    - _Requirements: 1.5, 1.6, 10.1, 10.2_

  - [ ]* 3.5 Write property test for AST parsing completeness
    - **Property 1: AST Parsing Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    - Test that valid source files produce correct Code_Chunks

  - [ ]* 3.6 Write property test for parser fallback resilience
    - **Property 2: Parser Fallback Resilience**
    - **Validates: Requirements 1.5, 1.6**
    - Test that parser failures trigger fallback without crashing

  - [ ]* 3.7 Write unit tests for AST Chunker
    - Test parsing Python file with functions and classes
    - Test parsing JavaScript file with arrow functions
    - Test handling syntax errors gracefully
    - Test extracting correct symbol definitions and references
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Vector Index implementation
  - [ ] 5.1 Implement VectorIndex abstract base class
    - Define build(), search(), save(), load() abstract methods
    - _Requirements: 2.1, 2.3_

  - [ ] 5.2 Implement LEANNIndex (primary backend)
    - Build graph-based vector index with 97% storage savings
    - Implement semantic search with cosine similarity
    - Implement save/load with metadata
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 5.3 Implement FAISSIndex (fallback backend)
    - Build HNSW index using faiss-cpu
    - Implement semantic search
    - Implement save/load
    - _Requirements: 2.1, 2.3, 2.4_

  - [ ] 5.4 Implement embedding generation with sentence-transformers
    - Use all-MiniLM-L6-v2 model
    - Support batch processing
    - Add memory monitoring
    - _Requirements: 2.1_

  - [ ] 5.5 Add OpenAI API fallback for embeddings
    - Implement API-based embedding generation
    - Handle API errors gracefully
    - _Requirements: 2.6_

  - [ ] 5.6 Add backend selection logic with fallback
    - Try LEANN first, fall back to FAISS on failure
    - Try local embeddings first, fall back to API on OOM
    - Log all fallback transitions
    - _Requirements: 2.4, 2.5, 2.6, 10.1, 10.2_

  - [ ]* 5.7 Write property test for vector index search ordering
    - **Property 3: Vector Index Search Ordering**
    - **Validates: Requirements 2.1, 2.3**
    - Test that search results are ordered by descending cosine similarity

  - [ ]* 5.8 Write property test for backend fallback automation
    - **Property 4: Backend Fallback Automation**
    - **Validates: Requirements 2.4, 2.5, 10.1, 10.2**
    - Test that primary backend failures trigger automatic fallback

  - [ ]* 5.9 Write property test for embedding fallback chain
    - **Property 5: Embedding Fallback Chain**
    - **Validates: Requirements 2.6**
    - Test that memory failures trigger API fallback

  - [ ]* 5.10 Write unit tests for Vector Index
    - Test building index from chunks
    - Test search returns correct top-K results
    - Test save and load preserves index
    - Test fallback to FAISS when LEANN unavailable
    - _Requirements: 2.1, 2.3, 2.4, 2.5_

- [ ] 6. RepoMap Graph implementation
  - [ ] 6.1 Implement RepoMapGraph abstract base class
    - Define build(), pagerank(), save(), load() abstract methods
    - _Requirements: 3.1, 3.2_

  - [ ] 6.2 Implement IGraphRepoMap (primary backend)
    - Build directed dependency graph from symbol references
    - Compute PageRank scores with C++ backend
    - Support changed file boosting
    - Implement save/load
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 6.3 Implement NetworkXRepoMap (fallback backend)
    - Build directed dependency graph
    - Compute PageRank scores with pure Python
    - Support changed file boosting
    - Implement save/load
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 6.4 Add backend selection logic with fallback
    - Try igraph first, fall back to NetworkX on failure
    - Log fallback transitions
    - _Requirements: 3.4, 3.5, 10.1, 10.2_

  - [ ]* 6.5 Write property test for dependency graph construction
    - **Property 6: Dependency Graph Construction**
    - **Validates: Requirements 3.1**
    - Test that symbol references create correct directed edges

  - [ ]* 6.6 Write property test for PageRank score validity
    - **Property 7: PageRank Score Validity**
    - **Validates: Requirements 3.2**
    - Test that PageRank scores sum to 1.0 (±0.001 tolerance)

  - [ ]* 6.7 Write property test for changed file score boosting
    - **Property 8: Changed File Score Boosting**
    - **Validates: Requirements 3.3**
    - Test that changed files have higher scores after boosting

  - [ ]* 6.8 Write unit tests for RepoMap Graph
    - Test building graph from symbol references
    - Test PageRank scores sum to 1.0
    - Test changed files receive boosted scores
    - Test fallback to NetworkX when igraph unavailable
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Retrieval Engine implementation
  - [ ] 8.1 Implement RetrievalEngine class
    - Initialize with VectorIndex, RepoMapGraph, and weights
    - Implement score normalization to [0, 1] range
    - Implement weighted score merging
    - Return sorted list of (file_path, importance_score) tuples
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 8.2 Write property test for score merging correctness
    - **Property 9: Score Merging Correctness**
    - **Validates: Requirements 4.1, 4.3, 4.4**
    - Test that merged score equals weighted sum of normalized scores

  - [ ]* 8.3 Write property test for score normalization range
    - **Property 10: Score Normalization Range**
    - **Validates: Requirements 4.4**
    - Test that all normalized scores are in [0, 1] range

  - [ ]* 8.4 Write property test for retrieval output format
    - **Property 11: Retrieval Output Format**
    - **Validates: Requirements 4.5**
    - Test that output is sorted list of (file_path, score) tuples

  - [ ]* 8.5 Write unit tests for Retrieval Engine
    - Test merging scores with correct weights
    - Test normalizing scores to [0, 1] range
    - Test handling missing semantic or PageRank scores
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 9. Budget Manager implementation
  - [ ] 9.1 Implement BudgetManager class
    - Initialize with token_budget and tiktoken encoding
    - Implement greedy knapsack selection algorithm
    - Reserve 20% budget for metadata
    - Return selected files and total token count
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 9.2 Write property test for greedy selection ordering
    - **Property 13: Greedy Selection Ordering**
    - **Validates: Requirements 5.2**
    - Test that files are processed in descending importance order

  - [ ]* 9.3 Write property test for budget enforcement
    - **Property 14: Budget Enforcement**
    - **Validates: Requirements 5.3, 5.4**
    - Test that total tokens never exceed 80% of budget

  - [ ]* 9.4 Write property test for budget manager output completeness
    - **Property 15: Budget Manager Output Completeness**
    - **Validates: Requirements 5.6**
    - Test that output includes both file list and token count

  - [ ]* 9.5 Write property test for greedy knapsack optimality
    - **Property 16: Greedy Knapsack Optimality**
    - **Validates: Requirements 5.7**
    - Test that no single file swap improves total importance score

  - [ ]* 9.6 Write unit tests for Budget Manager
    - Test selecting files within token budget
    - Test greedy selection maximizes importance score
    - Test reserving 20% for metadata
    - Test token counting accuracy within ±2%
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. XML Packer implementation
  - [ ] 11.1 Implement XMLPacker class
    - Generate Repomix-style XML structure
    - Include metadata header (repo name, file count, total tokens)
    - Wrap each file in <file path="..."> tags
    - Escape special XML characters
    - Include token count for each file
    - Use lxml for performance
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 11.2 Write property test for XML generation completeness
    - **Property 17: XML Generation Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.5**
    - Test that XML includes all required elements

  - [ ]* 11.3 Write property test for XML character escaping
    - **Property 18: XML Character Escaping**
    - **Validates: Requirements 6.4**
    - Test that special XML characters are escaped correctly

  - [ ]* 11.4 Write property test for XML round-trip validity
    - **Property 19: XML Round-Trip Validity**
    - **Validates: Requirements 6.7**
    - Test that generated XML can be parsed without errors

  - [ ]* 11.5 Write unit tests for XML Packer
    - Test XML output is valid and well-formed
    - Test metadata header is correct
    - Test file tags include paths and token counts
    - Test special characters are escaped
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.7_

- [ ] 12. ZIP Packer implementation
  - [ ] 12.1 Implement ZIPPacker class
    - Create ZIP archive with original directory structure
    - Place all files under files/ directory
    - Generate REVIEW_CONTEXT.md manifest in ZIP root
    - Include importance scores in manifest
    - Include inclusion explanations in manifest
    - Include suggested reading order in manifest
    - Use Python's zipfile library
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 12.2 Write property test for ZIP structure preservation
    - **Property 20: ZIP Structure Preservation**
    - **Validates: Requirements 7.1, 7.2, 7.3**
    - Test that ZIP preserves directory structure under files/

  - [ ]* 12.3 Write property test for ZIP manifest completeness
    - **Property 21: ZIP Manifest Completeness**
    - **Validates: Requirements 7.4, 7.5, 7.6**
    - Test that manifest includes all required information

  - [ ]* 12.4 Write unit tests for ZIP Packer
    - Test ZIP preserves directory structure
    - Test manifest includes all required information
    - Test files are under files/ directory
    - Test REVIEW_CONTEXT.md exists in ZIP root
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

- [ ] 13. Configuration and error handling
  - [ ] 13.1 Implement configuration loading and validation
    - Load from .context-pack.yaml with defaults
    - Validate all configuration values
    - Log errors for invalid values and use defaults
    - _Requirements: 8.1, 8.2, 8.8_

  - [ ]* 13.2 Write property test for configuration loading
    - **Property 22: Configuration Loading**
    - **Validates: Requirements 8.1, 8.3, 8.4, 8.5, 8.6, 8.7**
    - Test that valid YAML files are loaded correctly

  - [ ]* 13.3 Write property test for configuration error handling
    - **Property 23: Configuration Error Handling**
    - **Validates: Requirements 8.8**
    - Test that invalid values trigger defaults without crashing

  - [ ] 13.4 Implement BackendSelector with fallback logic
    - Auto-detect and select backends
    - Implement fallback chains for all components
    - Log all fallback transitions
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ]* 13.5 Write property test for graceful degradation
    - **Property 28: Graceful Degradation**
    - **Validates: Requirements 10.3, 10.4, 10.5, 10.6**
    - Test that component failures trigger simpler algorithms

  - [ ] 13.6 Implement error logging with actionable messages
    - Create ContextPackerError base exception
    - Add DependencyError and ConfigurationError subclasses
    - Include suggestions in all error messages
    - _Requirements: 12.1, 12.7_

  - [ ]* 13.7 Write property test for comprehensive error logging
    - **Property 34: Comprehensive Error Logging**
    - **Validates: Requirements 12.1, 12.7**
    - Test that errors include file path, line number, stack trace, and suggestions

  - [ ]* 13.8 Write property test for dual output logging
    - **Property 35: Dual Output Logging**
    - **Validates: Requirements 12.6**
    - Test that logs appear in both console and file

  - [ ]* 13.9 Write property test for log level filtering
    - **Property 36: Log Level Filtering**
    - **Validates: Requirements 12.4**
    - Test that only messages at configured level or higher are displayed

  - [ ]* 13.10 Write property test for verbose mode timing
    - **Property 37: Verbose Mode Timing**
    - **Validates: Requirements 12.5**
    - Test that verbose mode logs detailed timing information

- [ ] 14. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Index phase workflow
  - [ ] 15.1 Implement index_repository function
    - Parse codebase with AST Chunker (with fallback)
    - Build Vector Index (with fallback)
    - Build RepoMap Graph (with fallback)
    - Save indexes to .context-pack/
    - Save metadata for staleness detection
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [ ]* 15.2 Write property test for index persistence round-trip
    - **Property 24: Index Persistence Round-Trip**
    - **Validates: Requirements 9.1, 9.2, 9.3**
    - Test that save/load produces equivalent results

  - [ ]* 15.3 Write property test for backend auto-detection
    - **Property 25: Backend Auto-Detection**
    - **Validates: Requirements 9.4**
    - Test that loaded indexes correctly detect their backend

  - [ ]* 15.4 Write property test for index staleness detection
    - **Property 26: Index Staleness Detection**
    - **Validates: Requirements 9.5**
    - Test that modified files trigger staleness detection

  - [ ]* 15.5 Write property test for automatic index rebuild
    - **Property 27: Automatic Index Rebuild**
    - **Validates: Requirements 9.6**
    - Test that stale indexes are automatically rebuilt

- [ ] 16. Query phase workflow
  - [ ] 16.1 Implement query_and_pack function
    - Load indexes with auto-detection
    - Retrieve candidates with hybrid ranking
    - Select files within budget
    - Pack output in configured format (XML or ZIP)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 6.1, 7.1_

  - [ ]* 16.2 Write integration test for full workflow
    - Test index → query → pack for small repository
    - Verify output within token budget
    - Verify selected files have highest scores
    - _Requirements: 15.1, 15.4, 15.5_

- [ ] 17. CLI interface implementation
  - [ ] 17.1 Implement CLI with typer
    - Create context-pack command
    - Add index subcommand
    - Add query subcommand
    - Add pack subcommand
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ] 17.2 Add CLI flags and options
    - Add --format flag for output format
    - Add --budget flag for token budget
    - Add --config flag for custom config file
    - Add --verbose flag for detailed logging
    - _Requirements: 11.5, 11.6, 11.7_

  - [ ] 17.3 Implement CLI error handling and exit codes
    - Return 0 on success, non-zero on failure
    - Show helpful error messages for invalid arguments
    - _Requirements: 11.8_

  - [ ]* 17.4 Write property test for CLI index command
    - **Property 29: CLI Index Command**
    - **Validates: Requirements 11.2**
    - Test that index command creates indexes in .context-pack/

  - [ ]* 17.5 Write property test for CLI query command
    - **Property 30: CLI Query Command**
    - **Validates: Requirements 11.3**
    - Test that query command generates output

  - [ ]* 17.6 Write property test for CLI pack command
    - **Property 31: CLI Pack Command**
    - **Validates: Requirements 11.4**
    - Test that pack command executes full workflow

  - [ ]* 17.7 Write property test for CLI flag handling
    - **Property 32: CLI Flag Handling**
    - **Validates: Requirements 11.5, 11.6, 11.7**
    - Test that flags override config and defaults

  - [ ]* 17.8 Write property test for CLI exit codes
    - **Property 33: CLI Exit Codes**
    - **Validates: Requirements 11.8**
    - Test that exit codes are correct for success/failure

  - [ ]* 17.9 Write unit tests for CLI interface
    - Test index command creates indexes
    - Test query command generates output
    - Test pack command runs full workflow
    - Test invalid arguments show helpful errors
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

- [ ] 18. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Pretty Printer for round-trip testing
  - [ ] 19.1 Implement PrettyPrinter class
    - Format Code_Chunks back to source code
    - Support Python, JavaScript, TypeScript
    - Preserve syntax validity
    - _Requirements: 14.1, 14.2, 14.3_

  - [ ]* 19.2 Write property test for pretty printer format validity
    - **Property 39: Pretty Printer Format Validity**
    - **Validates: Requirements 14.2, 14.3**
    - Test that formatted code is syntactically valid

  - [ ]* 19.3 Write property test for parser round-trip equivalence
    - **Property 40: Parser Round-Trip Equivalence**
    - **Validates: Requirements 14.4**
    - Test that parse → print → parse produces equivalent structure

  - [ ]* 19.4 Write property test for round-trip failure logging
    - **Property 41: Round-Trip Failure Logging**
    - **Validates: Requirements 14.5**
    - Test that round-trip failures are logged with details

  - [ ]* 19.5 Write unit tests for Pretty Printer
    - Test formatting Python Code_Chunks to valid Python
    - Test formatting JavaScript Code_Chunks to valid JavaScript
    - Test round-trip equivalence for various source files
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [ ] 20. Performance monitoring and metrics
  - [ ] 20.1 Add performance tracking to all phases
    - Track indexing time, files processed, index size
    - Track query time, files selected, total tokens
    - Track memory usage during operations
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ]* 20.2 Write property test for metrics reporting completeness
    - **Property 38: Metrics Reporting Completeness**
    - **Validates: Requirements 13.1, 13.2, 13.3**
    - Test that all required metrics are reported

  - [ ]* 20.3 Write performance benchmark tests
    - Test indexing completes within 5 minutes for 10k files (primary)
    - Test indexing completes within 10 minutes for 10k files (fallback)
    - Test querying completes within 10 seconds (primary)
    - Test querying completes within 15 seconds (fallback)
    - _Requirements: 13.4, 13.5, 13.6, 13.7_

- [ ] 21. Integration tests and fallback scenarios
  - [ ]* 21.1 Write integration test for XML output workflow
    - Test full workflow with XML output format
    - Verify XML is valid and within budget
    - _Requirements: 15.2, 6.7_

  - [ ]* 21.2 Write integration test for ZIP output workflow
    - Test full workflow with ZIP output format
    - Verify ZIP structure and manifest
    - _Requirements: 15.2, 7.1, 7.2, 7.3_

  - [ ]* 21.3 Write integration test for LEANN to FAISS fallback
    - Force LEANN failure and verify FAISS fallback
    - Verify performance within 2x of primary
    - _Requirements: 15.3, 10.7_

  - [ ]* 21.4 Write integration test for igraph to NetworkX fallback
    - Force igraph failure and verify NetworkX fallback
    - Verify performance within 2x of primary
    - _Requirements: 15.3, 10.7_

  - [ ]* 21.5 Write integration test for local to API embeddings fallback
    - Force local embeddings OOM and verify API fallback
    - Verify functionality is preserved
    - _Requirements: 15.3, 10.7_

  - [ ]* 21.6 Write integration test for error scenarios
    - Test missing files are handled gracefully
    - Test invalid config uses defaults
    - Test corrupted source files are skipped
    - _Requirements: 15.6_

- [ ] 22. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 23. Documentation and packaging
  - [ ] 23.1 Create README.md with usage examples
    - Document installation (minimal, fast, all)
    - Document CLI commands and flags
    - Document configuration file format
    - Include quick start guide

  - [ ] 23.2 Create example configuration file
    - Create .context-pack.yaml.example
    - Document all configuration options
    - Include comments explaining each setting

  - [ ] 23.3 Finalize package metadata
    - Update pyproject.toml with complete metadata
    - Add classifiers, keywords, URLs
    - Verify dependency specifications

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at logical breaks
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end workflows and fallback scenarios
- TDD approach: write tests first, then implement to pass the tests
- All 41 correctness properties from the design document are covered by property-based tests
