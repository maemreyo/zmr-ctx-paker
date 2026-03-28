# 📚 ws-ctx-engine Documentation Index

**Status**: Archived (March 29, 2026)  
**License**: GPL-3.0-or-later  
**Repository**: https://github.com/maemreyo/zmr-ctx-paker

---

## 🚀 Start Here

### First Time Visitor?

1. **[PROJECT_ARCHIVE_SUMMARY.md](PROJECT_ARCHIVE_SUMMARY.md)** ← **READ THIS FIRST**
   - Quick overview of what ws-ctx-engine is
   - Why it was archived
   - What you can do with the codebase
   - Priority roadmap for continuation

2. **[README.md](README.md)** - Project introduction and usage guide
   - Installation instructions
   - Basic commands
   - Configuration options
   - Examples

### Looking for Technical Details?

1. **[ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)** - Complete system design
   - Component breakdown
   - Data flow diagrams
   - API reference
   - Performance benchmarks

2. **[CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md)** - Development guide
   - Setup instructions
   - Priority features to implement
   - Common development tasks
   - Testing guidelines

### Understanding the Failure?

1. **[PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md)** - Comprehensive failure analysis
   - Timeline of events
   - Strategic mistakes
   - Tactical errors
   - Lessons learned

2. **[COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md)** - GitNexus comparison
   - Feature-by-feature comparison
   - Market analysis
   - SWOT analysis
   - Strategic recommendations

---

## 📖 Documentation by Category

### Overview Documents

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| [PROJECT_ARCHIVE_SUMMARY.md](PROJECT_ARCHIVE_SUMMARY.md) | Quick introduction | Everyone | 15 min read |
| [README.md](README.md) | Usage guide | Users | 20 min read |
| [PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md) | Failure analysis | Founders, contributors | 45 min read |
| [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md) | Market comparison | Strategists | 40 min read |
| [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) | Technical deep dive | Engineers | 60 min read |
| [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md) | Development guide | Contributors | 30 min read |

### User Guides (`docs/guides/`)

| Guide | Description |
|-------|-------------|
| [guides/compression.md](docs/guides/compression.md) | Smart compression and context shuffling |
| [guides/logging.md](docs/guides/logging.md) | Structured logging system |
| [guides/output-formats.md](docs/guides/output-formats.md) | XML, JSON, YAML, MD output schemas |
| [guides/performance.md](docs/guides/performance.md) | Performance tuning and Rust extension |

### Technical Reference (`docs/reference/`)

| Reference | Description |
|-----------|-------------|
| [reference/architecture.md](docs/reference/architecture.md) | System architecture overview |
| [reference/prd.md](docs/reference/prd.md) | Product requirements document |
| [reference/design-ideas.md](docs/reference/design-ideas.md) | Design philosophy and ideas |
| [reference/chunker.md](docs/reference/chunker.md) | AST-based code chunker |
| [reference/vector-index.md](docs/reference/vector-index.md) | Embedding + vector index (LEANN/FAISS) |
| [reference/graph.md](docs/reference/graph.md) | Dependency graph and PageRank |
| [reference/retrieval.md](docs/reference/retrieval.md) | Hybrid semantic + graph retrieval |
| [reference/ranking.md](docs/reference/ranking.md) | Ranking and score merging |
| [reference/budget.md](docs/reference/budget.md) | Token budget manager |
| [reference/packer.md](docs/reference/packer.md) | XML and ZIP output packer |
| [reference/output-formatters.md](docs/reference/output-formatters.md) | Output formatter modules |
| [reference/secret-scanner.md](docs/reference/secret-scanner.md) | Secret detection before packing |
| [reference/workflow.md](docs/reference/workflow.md) | Pipeline orchestration |
| [reference/cli.md](docs/reference/cli.md) | CLI commands reference |
| [reference/config.md](docs/reference/config.md) | YAML configuration reference |
| [reference/supporting-modules.md](docs/reference/supporting-modules.md) | Backend selector, logging, utilities |

### Integration Guides (`docs/integrations/`)

| Integration | Description |
|-------------|-------------|
| [integrations/mcp-server.md](docs/integrations/mcp-server.md) | MCP server reference |
| [integrations/agent-workflows.md](docs/integrations/agent-workflows.md) | AI agent workflow integration |
| [integrations/claude-desktop.md](docs/integrations/claude-desktop.md) | Claude Desktop setup |
| [integrations/cursor.md](docs/integrations/cursor.md) | Cursor IDE setup |
| [integrations/windsurf.md](docs/integrations/windsurf.md) | Windsurf IDE setup |

### Development Documents (`docs/development/`)

#### Plans
| Document | Description |
|----------|-------------|
| [development/plans/agent-integration-proposal.md](docs/development/plans/agent-integration-proposal.md) | Strategic proposal for agent-first architecture |
| [development/plans/agent-plan-v4.md](docs/development/plans/agent-plan-v4.md) | Comprehensive agent implementation plan (v4) |
| [development/plans/cli-init-plan-v1.md](docs/development/plans/cli-init-plan-v1.md) | `wsctx init` enhanced architecture plan (v1) |
| [development/plans/cli-init-plan-v2.md](docs/development/plans/cli-init-plan-v2.md) | `wsctx init` enhancement plan (v2) |

#### Research
| Document | Description |
|----------|-------------|
| [development/research/leann.md](docs/development/research/leann.md) | LEANN vector index implementation research |

#### Audits
| Document | Description |
|----------|-------------|
| [development/audits/agent-plan-v4-audit.md](docs/development/audits/agent-plan-v4-audit.md) | Agent plan v4 implementation audit |
| [development/audits/chunker-issues.md](docs/development/audits/chunker-issues.md) | Chunker issues and improvement report |
| [development/audits/mcp-security.md](docs/development/audits/mcp-security.md) | MCP server security audit |
| [development/audits/repo-review.md](docs/development/audits/repo-review.md) | Full repository review |
| [development/audits/review-prompts.md](docs/development/audits/review-prompts.md) | Test query prompts for self-evaluation |

### Reports (`docs/reports/`)

| Report | Description |
|--------|-------------|
| [reports/GRAPH_RAG_ROADMAP.md](docs/reports/GRAPH_RAG_ROADMAP.md) | Graph-based RAG watch & integration roadmap |
| [reports/INDEX_MANAGEMENT_ROADMAP.md](docs/reports/INDEX_MANAGEMENT_ROADMAP.md) | Index management evolution plan |
| [reports/CODE_CHUNKING_STRATEGY_REPORT.md](docs/reports/CODE_CHUNKING_STRATEGY_REPORT.md) | Code chunking strategy evaluation |
| [reports/CHUNKING_STRATEGY_VERDICT.md](docs/reports/CHUNKING_STRATEGY_VERDICT.md) | Final verdict on chunking approach |
| [reports/CHONKIE_MARKDOWN_RESOLVER_INVESTIGATION.md](docs/reports/CHONKIE_MARKDOWN_RESOLVER_INVESTIGATION.md) | Chonkie library vs native implementation |
| [reports/REPOMIX_MCP_SKILLS_INTEGRATION_RESEARCH_REPORT.md](docs/reports/REPOMIX_MCP_SKILLS_INTEGRATION_RESEARCH_REPORT.md) | Repomix MCP integration research |

### Roadmap (`docs/roadmap/`)

| Document | Description |
|----------|-------------|
| [roadmap/ROADMAP.md](docs/roadmap/ROADMAP.md) | Release roadmap and milestone tracker |

---

## 🔍 Find Information By Topic

### Understanding What Happened

**Q: Why was this project archived?**
- Start with: [PROJECT_ARCHIVE_SUMMARY.md](PROJECT_ARCHIVE_SUMMARY.md#why-did-it-fail)
- Deep dive: [PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md)
- Market analysis: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md)

**Q: How does it compare to GitNexus?**
- Feature comparison: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#feature-comparison-matrix)
- Technical deep dive: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)
- Market positioning: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#market-analysis)

### Using the Codebase

**Q: How do I install and use ws-ctx-engine?**
- Quick start: [README.md](README.md#quick-start)
- Configuration: [README.md](README.md#configuration)
- Examples: [examples/](examples/)

**Q: Can I continue development?**
- Yes! Read: [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md)
- Priority features: [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md#priority-features-to-implement)
- Setup guide: [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md#quick-start)

### Technical Implementation

**Q: How does hybrid ranking work?**
- Algorithm explanation: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md#hybrid-ranking-algorithm)
- Implementation: [src/ws_ctx_engine/retrieval/retrieval.py](src/ws_ctx_engine/retrieval/retrieval.py)
- Research: [docs/reports/GRAPH_RAG_ROADMAP.md](docs/reports/GRAPH_RAG_ROADMAP.md)

**Q: What about token budget management?**
- Knapsack algorithm: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md#budget-manager)
- Implementation: [src/ws_ctx_engine/budget/budget.py](src/ws_ctx_engine/budget/budget.py)
- Unique advantage: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#retrieval-quality)

**Q: Tell me about the fallback strategy**
- Six-level hierarchy: [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md#backend-selector)
- Implementation: [src/ws_ctx_engine/backend_selector/backend_selector.py](src/ws_ctx_engine/backend_selector/backend_selector.py)
- Production reliability: [PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md#technical-achievements)

### Continuing the Project

**Q: What features need to be completed?**
- Priority roadmap: [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md#priority-features-to-implement)
- Graph RAG plan: [docs/reports/GRAPH_RAG_ROADMAP.md](docs/reports/GRAPH_RAG_ROADMAP.md)
- Agent experience: [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md#1-complete-graph-rag-implementation)

**Q: What's the enterprise pivot strategy?**
- Enterprise focus: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#for-enterprise-pivot)
- Pricing model: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#pricing)
- Go-to-market: [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#go-to-market)

---

## 📊 Key Metrics

### Development Stats
- **Duration**: 12 months (Jan 2025 - Mar 2026)
- **Commits**: 150+
- **Contributors**: 1 (zamery)
- **Lines of Code**: ~15,500 Python, ~500 Rust
- **Test Coverage**: 85% unit, 70% integration

### Performance Benchmarks
- **Indexing Speed**: 4m 30s for 10k files (optimal backends)
- **Query Speed**: <10 seconds for full workflow
- **Storage**: LEANN provides 97% savings vs FAISS
- **Token Accuracy**: ±2% vs actual LLM tokenization

### Market Stats
- **GitHub Stars**: 47
- **Forks**: 12
- **PyPI Downloads**: ~500 total
- **Active Users**: ~10 estimated

See [PROJECT_ARCHIVE_SUMMARY.md](PROJECT_ARCHIVE_SUMMARY.md#performance-benchmarks) for details.

---

## 🎯 Quick Navigation by Role

### For Developers

**Getting Started**:
1. [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md#quick-start) - Setup environment
2. [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) - Understand system design
3. [examples/](examples/) - Run example code

**Priority Tasks**:
1. [Complete Graph RAG](CONTRIBUTOR_GUIDE.md#1-complete-graph-rag-implementation)
2. [Auto-install skills](CONTRIBUTOR_GUIDE.md#2-auto-install-agent-skills)
3. [Claude Code hooks](CONTRIBUTOR_GUIDE.md#3-claude-code-hooks)

**Reference**:
- [Component documentation](docs/reference/)
- [API reference](ARCHITECTURE_SUMMARY.md#data-models)
- [Testing guide](CONTRIBUTOR_GUIDE.md#testing-guidelines)

### For Founders/Strategists

**Market Analysis**:
1. [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md) - GitNexus comparison
2. [PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md) - Lessons learned
3. [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#strategic-recommendations) - Pivot strategies

**Strategic Options**:
- [Enterprise pivot](COMPETITOR_ANALYSIS.md#for-enterprise-pivot)
- [Acquisition scenario](COMPETITOR_ANALYSIS.md#acquisition-scenario)
- [Community building](CONTRIBUTOR_GUIDE.md#month-5-6-build-community)

### For Researchers

**Technical Innovations**:
- [Hybrid ranking algorithm](ARCHITECTURE_SUMMARY.md#ranking-module)
- [LEANN integration](ARCHITECTURE_SUMMARY.md#vector-index)
- [Token budget knapsack](ARCHITECTURE_SUMMARY.md#budget-manager)

**Research Opportunities**:
- Publish hybrid ranking paper
- Study LEANN for code structures
- Analyze fallback strategy effectiveness

### For Users

**Basic Usage**:
1. [README.md](README.md#quick-start) - Install and run
2. [guides/](docs/guides/) - How-to guides
3. [examples/](examples/) - Working examples

**Advanced Features**:
- [Configuration reference](README.md#configuration)
- [Output formats](guides/output-formats.md)
- [MCP integration](integrations/mcp-server.md)

---

## 🔗 External Resources

### Related Projects

- **GitNexus**: https://github.com/abhigyanpatwari/GitNexus
- **LEANN**: https://github.com/yichuan-w/LEANN
- **Tree-sitter**: https://tree-sitter.github.io/tree-sitter/
- **FAISS**: https://faiss.ai/
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **CozoDB**: https://docs.cozodb.org/

### Citation

If using in research:

```bibtex
@software{ws_ctx_engine,
  title = {ws-ctx-engine: Intelligent Codebase Packaging for LLMs},
  author = {zamery},
  year = {2024},
  url = {https://github.com/maemreyo/zmr-ctx-paker},
  note = {Archived March 2026; available under GPL-3.0 license}
}
```

---

## 📞 Getting Help

### Documentation Issues

- **Missing information?** → Open GitHub issue
- **Unclear explanation?** → Check [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) first
- **Need examples?** → See [examples/](examples/) directory

### Technical Questions

- **Bug reports** → GitHub Issues
- **Feature requests** → GitHub Discussions (if enabled)
- **Implementation help** → Read [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md)

### Contact

- **Email**: zaob.ogn@gmail.com (original author, may not respond promptly)
- **GitHub**: https://github.com/maemreyo/zmr-ctx-paker

---

## 📋 Document Maintenance

### Last Updated

All documents updated on **March 29, 2026** to reflect archived status.

### Document Status Legend

- ✅ **Complete**: Fully implemented and documented
- ⚠️ **Partial**: Implemented but incomplete
- ❌ **Planned**: Designed but not implemented
- 📝 **Historical**: Archive/post-mortem content

### Version History

- **v0.2.0a0** (March 2026) - Final release, archived
- **v0.1.x** (2025-2026) - Active development releases

See [CHANGELOG.md](CHANGELOG.md) for complete history.

---

**End of Documentation Index**

*This index serves as the entry point for all ws-ctx-engine documentation. Start with PROJECT_ARCHIVE_SUMMARY.md for quick overview, then navigate to specific documents based on your needs.*
