# Changelog

## [0.1.10] - 2026-03-25

### Changes
- 460d91d feat: merge .gitignore by default for index, search, query, and pack commands



## [0.1.9] - 2026-03-25

### Changes
- c55dcb0 feat: rebranding
- 0e3b6fc feat: context engine
- ffee4f6 docs: add comprehensive implementation plan for agent integration
- 52ea04d docs: update agent integration proposal with detailed MCP design
- b545269 docs: add strategic proposal for AI agent integration



## [0.1.8] - 2026-03-25

### Changes
- 9ca818c feat: enhance init script and templates
- e78990e feat: add version flag to CLI and init script
- 2f583b7 fix: ensure script permissions and centralize command strings
- 5e6b223 docs: add enhancement plan v2 for wsctx-init
- 3f9729a feat: add AI agent configuration installer with init script
- de06207 feat(init): add wsctx-init command for AI agent configuration
- 2febd1e feat(cli): add enhanced modular architecture plan for ws-ctx-engine init
- d12487c chore: bump version to 0.1.7 and update entry point script name
- 4b264ea chore: rename CLI tool from ws-ctx-engine to ws-ctx-engine
- d129d93 feat(vector_index): add NativeLEANN backend for 97% storage savings
- 45aa53d docs: add repository review and LEANN implementation research
- 8e8457b build: update project version and dependencies for release 0.1.4
- dec3a24 docs: Update README with ws-ctx-engine name and AI Agents section
- ab52943 docs: Add AI_AGENTS.md for agent usage
- a7c35c1 fix: properly exclude examples/zmr-koe/source from git
- bca7395 feat: Add status, vacuum, reindex-domain commands
- c3594b2 fix(retrieval): adjust domain boost for path-dominant queries
- 4486d70 feat(domain_map): add directories_for method for retrieval engine
- d27bfeb feat(cli): add status, vacuum, and reindex-domain commands
- 29dc469 feat(domain_map): replace pickle storage with SQLite database
- dfb6f4c feat(retrieval): add domain keyword map for adaptive query boosting
- 0758179 feat(retrieval): add domain keyword map and query classifier for conceptual queries
- 9d8a313 feat(retrieval): add symbol-based and path-based boosting to retrieval engine
- c9736c5 test: refactor self-tests script to use function and clean output
- c545007 feat: add self-test script and review prompts for ws-ctx-engine
- 4072a25 feat(chunker): enhance language resolvers and add comprehensive tests
- db32cf9 refactor(chunker): restructure code into modular language resolvers
- 37093a9 refactor: reorganize project structure into modules
- fe87402 refactor: restructure codebase into modular packages for better maintainability
- e700008 chore: remove backup file for chunker module
- a0d80d6 chore: include markdown files in test coverage patterns
- 84ae9c5 feat(chunker): extend chunker to support markdown and more AST types
- 5cef4ef docs: add chunker issues and improvement report
- 2423cb6 feat(tests): add comprehensive test suite and example configurations
- 45d9cf6 feat(ws-ctx-engine): Add complete project implementation with core modules and tests
- bf3e17f feat(ws-ctx-engine): Initialize project with specifications and documentation


## [0.1.7] - 2026-03-25

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py


## [0.1.6] - 2026-03-25

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py


## [0.1.5] - 2026-03-25

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py


## [0.1.4] - 2026-03-25

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py


## [0.1.3] - 2026-03-24

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py


## [0.1.2] - 2026-03-24

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py


## [0.1.1] - 2026-03-24

### Added
- `ws-ctx-engine status` - Show index size, file count, backend info
- `ws-ctx-engine vacuum` - Optimize SQLite database
- `ws-ctx-engine reindex-domain` - Only rebuild domain_map.db (fast)
- SQLite DomainMapDB backend for large repositories (>10K files)
- Phase 1-4: Parallel Write → Shadow Read → SQLite Primary → Cleanup

### Changed
- Tuned retrieval weights: domain_boost 0.4 → 0.25
- Improved query classification for better ranking
- Fixed DomainMapDB.drop-in compatibility with RetrievalEngine

### Fixed
- Missing `directories_for()` method in DomainMapDB
- Broken try block structure in query.py



All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with comprehensive documentation
- README.md with installation instructions and usage examples
- CONTRIBUTING.md with development guidelines
- CODE_OF_CONDUCT.md based on Contributor Covenant 2.1
- Example configuration file (.ws-ctx-engine.yaml.example)
- GPL-3.0-or-later license

## [0.1.0] - 2025-01-XX

### Added
- AST-based code parsing with Tree-sitter (primary) and regex fallback
- Vector indexing with LEANN (primary) and FAISS (fallback)
- Dependency graph analysis with igraph (primary) and NetworkX (fallback)
- Hybrid ranking combining semantic search and PageRank
- Token budget management with greedy knapsack algorithm
- Dual output formats: XML (Repomix-style) and ZIP (with manifest)
- Incremental indexing with staleness detection
- Comprehensive fallback strategies for all components
- CLI interface with index, query, and pack commands
- Configuration management via YAML files
- Structured logging with dual output (console + file)
- Property-based testing with Hypothesis
- Integration tests for full workflow
- Performance benchmarks for all components

### Features
- Support for Python, JavaScript, and TypeScript parsing
- Local embeddings with sentence-transformers
- OpenAI API fallback for embeddings
- Changed file boosting for PR reviews
- Configurable semantic and PageRank weights
- File filtering with include/exclude patterns
- Automatic backend selection and fallback
- Round-trip validation for AST parsing
- Token counting with ±2% accuracy

### Performance
- Indexing: <5 minutes for 10,000 files (primary backends)
- Query: <10 seconds for 10,000 files (primary backends)
- Parsing: <5 seconds per 1,000 lines of code
- LEANN: 97% storage savings vs traditional vector indexes

### Documentation
- Comprehensive README with quick start guide
- Detailed configuration documentation
- API documentation with Google-style docstrings
- Contributing guidelines
- Code of Conduct
- Example workflows for common use cases

[Unreleased]: https://github.com/maemreyo/zmr-ctx-paker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maemreyo/zmr-ctx-paker/releases/tag/v0.1.0
