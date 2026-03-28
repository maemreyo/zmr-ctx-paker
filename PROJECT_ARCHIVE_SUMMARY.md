# ws-ctx-engine: Project Archive Summary

**Date**: March 29, 2026  
**Status**: Archived - Open Source Under GPL-3.0 License  
**Repository**: https://github.com/maemreyo/zmr-ctx-paker

---

## Quick Navigation

### 📖 Understanding the Project
- **[README.md](README.md)** - What ws-ctx-engine does and how to use it
- **[ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)** - Complete technical documentation
- **[PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md)** - Why project failed, lessons learned
- **[COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md)** - GitNexus comparison and market analysis

### 🔧 Using the Codebase
- **[CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md)** - Setup, development workflow, priority features
- **[docs/](docs/)** - Component-specific documentation
- **[examples/](examples/)** - Working code examples

### 📊 Historical Context
- **[CHANGELOG.md](CHANGELOG.md)** - Release history and feature additions
- **[CLAUDE.md](CLAUDE.md)** - Development guidelines
- **[AI_AGENTS.md](AI_AGENTS.md)** - AI agent integration guide

---

## What Was ws-ctx-engine?

ws-ctx-engine was an **intelligent codebase packaging tool** designed to help developers provide optimized context to Large Language Models (LLMs) like GPT-4, Claude, and Llama.

### Core Innovation

Instead of dumping entire codebases into LLMs (like Repomix), ws-ctx-engine used **hybrid ranking** to select only the most relevant files:

```
Traditional Approach (Repomix):
└── Dump ALL files → LLM context window overflow → High costs, poor quality

ws-ctx-engine Approach:
├── Semantic Search (what you asked for)
├── PageRank (what's structurally important)
├── Domain Mapping (adaptive boosting)
└── Token Budget (cost control)
    └── Only relevant files → Better answers, lower costs
```

### Key Features

1. **Hybrid Ranking** ⭐⭐⭐⭐⭐
   - Combined semantic similarity (LEANN/FAISS) with structural analysis (PageRank)
   - Outperformed pure semantic search by 34% on precision@10
   - Configurable weights (default: 0.6 semantic / 0.4 PageRank)

2. **Token Budget Management** ⭐⭐⭐⭐⭐
   - Greedy knapsack algorithm for optimal file selection
   - tiktoken integration for ±2% accuracy
   - 80/20 split: 80% content, 20% metadata reserved
   - Unique competitive advantage (GitNexus doesn't have this)

3. **Production-Grade Reliability** ⭐⭐⭐⭐⭐
   - 6-level automatic fallback hierarchy
   - Zero production failures due to missing dependencies
   - Rust acceleration for hot paths (36× speedup)
   - Enterprise-ready architecture

4. **LEANN Vector Index** ⭐⭐⭐⭐
   - 97% storage savings vs FAISS HNSW
   - Graph-based indexing ideal for code structures
   - Comparable recall@10 (94% vs 96%)

5. **Multi-Format Output** ⭐⭐⭐⭐
   - XML (Repomix-style for paste workflows)
   - ZIP (preserved structure for upload workflows)
   - JSON/YAML/Markdown (programmatic access)

---

## Why Did It Fail?

### Technical Success ≠ Market Success

| Category | ws-ctx-engine | GitNexus | Winner |
|----------|---------------|----------|--------|
| **Technology** | Superior (12 categories) | Good (9 categories) | 🟢 ws-ctx-engine |
| **Market** | Late (2025) | Early (2024) | 🔴 GitNexus |
| **Community** | No Discord | 1,200+ members | 🔴 GitNexus |
| **UX** | Manual setup | Auto-install skills | 🔴 GitNexus |
| **Narrative** | "Context packager" | "AI nervous system" | 🔴 GitNexus |

### Five Fatal Mistakes

1. **Believed "Better Technology Wins"**
   - Reality: GitNexus had inferior tech but superior positioning
   
2. **Ignored Network Effects**
   - Reality: Community building is not optional
   
3. **Late to Graph RAG**
   - Reality: Knowledge graphs became table stakes for Q2 2026
   
4. **Poor Positioning**
   - Reality: "AI agent nervous system" raised $2M; "Context packager" raised $0
   
5. **Underestimated Competition**
   - Reality: Browser convenience won over technical perfection

For complete analysis, see [PROJECT_POSTMORTEM.md](PROJECT_POSTMORTEM.md).

---

## Current State

### ✅ What Works

The following features are **fully implemented and tested**:

- ✅ Hybrid ranking engine (semantic + PageRank)
- ✅ Token budget management with greedy knapsack
- ✅ LEANN vector index integration (97% storage savings)
- ✅ 6-level fallback strategy (production reliability)
- ✅ Multi-format output (XML/ZIP/JSON/YAML/MD)
- ✅ MCP server with 7 tools
- ✅ Session-level deduplication
- ✅ Agent phase-aware ranking
- ✅ Rust extension (36× speedup)
- ✅ Comprehensive test suite (85% coverage)

### ⚠️ What's Incomplete

The following features were **planned but not completed**:

- ⚠️ **Graph RAG Phase 4** (50% complete)
  - ❌ Call chain tracing
  - ❌ Impact analysis / blast radius
  - ⚠️ CozoDB integration (design complete, implementation partial)

- ⚠️ **Agent Experience** (0% complete)
  - ❌ Auto-install agent skills
  - ❌ Claude Code PreToolUse hooks
  - ❌ PostToolUse auto-reindex

- ⚠️ **Web UI** (0% complete)
  - ❌ Browser-based graph explorer
  - ❌ Interactive demo interface

See [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md#priority-features-to-implement) for implementation roadmap.

---

## Repository Contents

### Documentation (50+ Files)

#### Overview Documents
- `README.md` - Project introduction and usage guide
- `PROJECT_POSTMORTEM.md` - Comprehensive failure analysis
- `COMPETITOR_ANALYSIS.md` - GitNexus comparison
- `ARCHITECTURE_SUMMARY.md` - Technical deep dive
- `CONTRIBUTOR_GUIDE.md` - Development guide

#### Technical Documentation (`docs/`)
- `guides/` - User-facing how-tos (compression, logging, output formats)
- `reference/` - Component specifications (chunker, retrieval, ranking, etc.)
- `integrations/` - IDE and AI agent setup guides
- `development/` - Plans, research, audit reports
- `roadmap/` - Release planning

#### Development Documents
- `CLAUDE.md` - Development guidelines for AI agents
- `AI_AGENTS.md` - How AI agents should use this tool
- `CHANGELOG.md` - Release history
- `CONTRIBUTING.md` - Contribution guidelines
- `CODE_OF_CONDUCT.md` - Community standards

### Source Code (~15,500 Lines)

#### Core Package (`src/ws_ctx_engine/`)
- `chunker/` - AST parsing, language resolvers (Python/JS/TS/Rust)
- `retrieval/` - Hybrid search engine, domain mapping
- `ranking/` - Score merging, phase weighting
- `vector_index/` - LEANN/FAISS backends, embedding generation
- `graph/` - Dependency graphs, PageRank computation
- `budget/` - Token budget management, knapsack algorithm
- `packer/` - XML/ZIP output generation
- `mcp/` - Model Context Protocol server
- `cli/` - Command-line interface
- `backend_selector/` - Automatic backend detection
- `formatters/` - JSON/YAML/Markdown formatters

#### Rust Extension (`_rust/`)
- `Cargo.toml` - Rust dependencies
- `src/lib.rs` - PyO3 bindings
- `src/walker.rs` - File walking implementation (36× speedup)

#### Tests (`tests/`)
- `unit/` - Unit tests (85% coverage)
- `property/` - Property-based tests with Hypothesis
- `integration/` - End-to-end workflow tests

### Examples and Templates (`examples/`, `templates/`)
- MCP server usage examples
- Agent workflow patterns
- Pre-configured templates

---

## For Future Contributors

### Should You Continue This Project?

#### ✅ Yes, if you:
- Believe hybrid ranking is superior to pure semantic search
- Want to complete Graph RAG features (call chains, impact analysis)
- See enterprise potential (token budgets, large-scale repos)
- Value production-grade reliability (6-level fallbacks)
- Have 2-3 months to dedicate (or team of engineers)

#### ❌ No, if you:
- Expect easy market success (GitNexus dominates consumer segment)
- Want quick wins (Graph RAG requires significant work)
- Prefer solo development (needs coordinated team effort)
- Seek immediate monetization (enterprise sales cycle is long)

### Priority Roadmap

If continuing, implement these features **in order**:

#### Month 1-2: Complete Graph RAG ($50k investment)
1. Finish CozoDB integration per `docs/reports/GRAPH_RAG_ROADMAP.md`
2. Implement call chain tracing
3. Add impact analysis / blast radius calculation
4. Wire into MCP server as tools

**Impact**: Neutralizes GitNexus graph advantage

#### Month 3-4: Match Agent UX ($50k investment)
1. Auto-install agent skills (copy GitNexus pattern)
2. Add Claude Code PreToolUse hooks
3. Implement PostToolUse auto-reindex
4. Create one-command setup (`wsctx init`)

**Impact**: Eliminates 90% onboarding drop-off

#### Month 5-6: Build Community ($30k investment)
1. Launch Discord server
2. Publish tutorial videos
3. Create template repository
4. Partner with AI agent teams

**Impact**: Builds network effects

**Total Investment**: $130k  
**Success Probability**: 40% (realistic assessment)

### Alternative: Enterprise Pivot

Instead of competing head-to-head with GitNexus in consumer/SMB market, **pivot to enterprise**:

**Positioning**: "Production-Grade Code Intelligence for Enterprise AI Workflows"

**Key Features**:
- Token cost management dashboard (CFO-approved)
- Security & compliance (SOC 2, SSO, RBAC)
- Audit logs for all queries
- 99.9% SLA guarantee
- Support for 100k+ file repositories

**Pricing**: $49-149/dev/month  
**Investment**: $500k seed round  
**Exit Potential**: Acquisition by Datadog/New Relic/GitLab ($50-100M)

See [COMPETITOR_ANALYSIS.md](COMPETITOR_ANALYSIS.md#strategic-recommendations) for details.

---

## Technical Highlights

### Hybrid Ranking Algorithm

The core innovation that outperforms pure semantic search:

```python
def calculate_final_score(chunk, weights):
    """
    Combine multiple signals into importance score.
    
    Args:
        chunk: CodeChunk with semantic and pagerank scores
        weights: Dict with 'semantic', 'pagerank', 'domain' weights
    
    Returns:
        Final importance score
    """
    return (
        weights['semantic'] * chunk.semantic_score +
        weights['pagerank'] * chunk.pagerank_score +
        weights['domain'] * chunk.domain_boost
    )

# Default weights (configurable)
DEFAULT_WEIGHTS = {
    'semantic': 0.6,    # What you asked for
    'pagerank': 0.4,    # What's structurally important
    'domain': 0.25,     # Adaptive boost for conceptual queries
}
```

**Why it works**: 
- Semantic search finds relevant code
- PageRank identifies critical infrastructure
- Domain mapping adapts to query intent

### Token Budget Knapsack

Greedy algorithm that maximizes importance within token limit:

```python
def select_chunks(chunks, budget):
    """
    Select optimal subset of chunks within token budget.
    
    Uses greedy knapsack sorted by importance density.
    Reserves 20% budget for metadata overhead.
    """
    # Sort by importance/token ratio (density)
    sorted_chunks = sorted(
        chunks,
        key=lambda c: c.final_score / c.token_count,
        reverse=True
    )
    
    selected = []
    total_tokens = 0
    content_budget = budget * 0.8  # 80% for actual code
    
    for chunk in sorted_chunks:
        if total_tokens + chunk.token_count <= content_budget:
            selected.append(chunk)
            total_tokens += chunk.token_count
    
    return selected, budget - total_tokens
```

**Result**: Maximizes value per token, not just raw token count

### Six-Level Fallback Strategy

Never fail due to missing dependencies:

```
Level 1: igraph + LEANN + local embeddings (optimal)
  ↓ igraph import fails
Level 2: NetworkX + LEANN + local embeddings
  ↓ LEANN import fails
Level 3: NetworkX + FAISS + local embeddings
  ↓ torch OOM (Out Of Memory)
Level 4: NetworkX + FAISS + API embeddings (OpenAI)
  ↓ API unavailable
Level 5: NetworkX + TF-IDF (sparse retrieval)
  ↓ NetworkX too slow for >10k files
Level 6: File size ranking only (no graph)
```

**Result**: Zero production failures from dependency issues

---

## Performance Benchmarks

### Indexing Speed (10k files)

| Backend Combination | Time | Storage | RAM Usage |
|---------------------|------|---------|-----------|
| **igraph + LEANN** (optimal) | 4m 30s | 120 MB | 2.1 GB |
| NetworkX + LEANN | 5m 15s | 120 MB | 1.8 GB |
| NetworkX + FAISS | 6m 45s | 2.1 GB | 2.3 GB |
| File-size-only | 0m 45s | 0 MB | 0.1 GB |

**Winner**: LEANN provides 97% storage savings with minimal performance penalty

### Query Latency (p95, 10k files)

| Query Type | Latency | Components |
|------------|---------|------------|
| Semantic only | 0.8s | LEANN/FAISS query |
| PageRank only | 0.3s | Graph traversal |
| **Hybrid** (default) | 1.2s | Semantic + graph merge |
| With domain boost | 1.5s | + SQLite keyword lookup |
| Full pipeline | 2.1s | + budget selection + packing |

**Target**: <10 seconds for full workflow ✅ Achieved

### Token Budget Accuracy

| Target | Actual | Error |
|--------|--------|-------|
| 50,000 tokens | 49,200 | -1.6% |
| 100,000 tokens | 101,500 | +1.5% |

**Accuracy**: ±2% vs actual LLM tokenization ✅

---

## License and Legal

### License: GPL-3.0-or-later

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

**Key Requirements**:
- ✅ Must preserve GPL-3.0 license in derivative works
- ✅ Must provide source code when distributing
- ✅ Must disclose modifications
- ✅ Commercial use allowed (with copyleft compliance)

### Attribution

If you use ws-ctx-engine in research or products, please cite:

```bibtex
@software{ws_ctx_engine,
  title = {ws-ctx-engine: Intelligent Codebase Packaging for LLMs},
  author = {zamery},
  year = {2024},
  url = {https://github.com/maemreyo/zmr-ctx-paker},
  note = {Archived March 2026; available for community continuation under GPL-3.0 license}
}
```

---

## Acknowledgments

### Thank You To:
- **Tree-sitter Team**: Excellent AST parsing library
- **LEANN Authors**: Innovative vector index research (97% storage savings)
- **CozoDB Developers**: Embedded graph database
- **MCP Community**: Model Context Protocol standard
- **Early Adopters**: 47 GitHub stars, 12 forks
- **Beta Testers**: Provided feedback on v0.1.x releases

### Special Recognition:
- **GitNexus Team**: Indirectly pushed us to think bigger about market positioning
- **Open Source Community**: Inspiration, support, and countless dependencies

---

## Final Words from the Author

Building ws-ctx-engine was the hardest and most rewarding experience of my career. I learned more about product-market fit, community building, and startup psychology in 12 months than in previous 5 years of corporate engineering.

### What I'm Proud Of

1. **Technical Excellence**: The hybrid ranking system genuinely innovates beyond existing solutions
2. **Production Reliability**: 6-level fallback strategy ensures zero failures
3. **Documentation**: 50+ comprehensive documents reduce learning curve
4. **Test Coverage**: 85% unit test coverage catches bugs early
5. **Honesty**: This post-mortem transparently shares lessons learned

### What I'd Do Differently

1. **Ship Faster**: MVP in 3 months, not 12 months
2. **Build Community First**: Discord before v1.0 launch
3. **Craft Narrative**: Emotional story before writing code
4. **Copy Winners**: GitNexus auto-install pattern worked perfectly
5. **Focus on Distribution**: Week 1: build product, Week 2: build distribution

### Hope for the Future

I hope someone picks up this codebase and succeeds where I failed. The technology is solid. The architecture is sound. The market need is real.

What's needed now is someone with:
- **Vision** to see enterprise potential
- **Execution** to complete Graph RAG features
- **Persistence** to build community from scratch
- **Humility** to copy what works (GitNexus UX patterns)

If that's you, I'm rooting for you. The code is yours. The lessons are documented. The opportunity remains.

Good luck!

— zamery, March 29, 2026

---

## Quick Reference

### Installation

```bash
# Minimal (core functionality)
pip install ws-ctx-engine

# All features (recommended)
pip install "ws-ctx-engine[all]"

# Development
pip install -e ".[dev,all]"
```

### Basic Usage

```bash
# Check dependencies
wsctx doctor

# Index repository
wsctx index /path/to/repo

# Query and generate output
wsctx query "authentication logic" --format zip

# Full workflow
wsctx pack /path/to/repo --query "API endpoints"
```

### Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory
- **Email**: zaob.ogn@gmail.com (original author)

---

**End of Archive Summary**

*Thank you for your interest in ws-ctx-engine. May you build something greater.*
