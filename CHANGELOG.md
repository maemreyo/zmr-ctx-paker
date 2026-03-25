# Changelog
## [0.1.7] - 2026-03-25

### Added
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- `context-pack status` - Show index size, file count, backend info
- `context-pack vacuum` - Optimize SQLite database
- `context-pack reindex-domain` - Only rebuild domain_map.db (fast)
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
- Example configuration file (.context-pack.yaml.example)
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
