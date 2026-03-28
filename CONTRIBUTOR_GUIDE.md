# Contributor Guide

**Status**: Archived Project - Community Maintenance Mode  
**Last Updated**: March 29, 2026  
**License**: GPL-3.0-or-later

---

## Welcome!

Thank you for your interest in ws-ctx-engine. This project has been archived by the original author but remains available under the GPL-3.0 license for community continuation.

This guide will help you understand the codebase, set up your development environment, and contribute effectively.

---

## Should You Continue This Project?

### ✅ Yes, if you:
- Believe in the hybrid ranking approach (semantic + PageRank)
- Want to complete Graph RAG features (call chains, impact analysis)
- See enterprise potential (token budget management, large-scale repos)
- Value production-grade reliability (6-level fallback strategy)

### ❌ No, if you:
- Expect easy market success (GitNexus dominates consumer segment)
- Want quick wins (Graph RAG completion requires 2-3 months work)
- Prefer solo development (this needs team effort)
- Seek immediate monetization (enterprise sales cycle is long)

---

## Quick Start

### Prerequisites
- Python 3.11+ (required)
- Rust toolchain (optional, for extension)
- Git (for version control)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/maemreyo/zmr-ctx-paker.git
cd zmr-ctx-paker

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\Activate` on Windows

# Install with all dependencies
pip install -e ".[dev,all]"

# Verify installation
wsctx doctor

# Run tests
pytest tests/unit/ -n auto -q

# Build Rust extension (optional)
pip install maturin
cd _rust && maturin develop --release
```

### Verify Setup

```bash
# Should pass all checks
wsctx doctor

# Should run all unit tests successfully
pytest tests/unit/ -xvs

# Should build without errors
python -c "from ws_ctx_engine import __version__; print(__version__)"
```

---

## Understanding the Codebase

### Repository Structure

```
zmr-ctx-paker/
├── src/ws_ctx_engine/          # Main package (~15k LOC)
│   ├── chunker/                # AST parsing, language resolvers
│   ├── retrieval/              # Hybrid search engine
│   ├── ranking/                # Score merging, phase weighting
│   ├── vector_index/           # LEANN/FAISS backends
│   ├── graph/                  # Dependency graphs, PageRank
│   ├── budget/                 # Token budget management
│   ├── packer/                 # XML/ZIP output generation
│   ├── mcp/                    # MCP server implementation
│   └── cli/                    # Command-line interface
├── tests/                      # Test suite (85% coverage)
│   ├── unit/                   # Unit tests
│   ├── property/               # Property-based tests
│   └── integration/            # End-to-end tests
├── docs/                       # Documentation (50+ files)
├── _rust/                      # Rust extension (optional)
└── examples/                   # Usage examples
```

### Key Documents to Read First

1. **ARCHITECTURE_SUMMARY.md** - System overview and component details
2. **PROJECT_POSTMORTEM.md** - Why project was archived, lessons learned
3. **COMPETITOR_ANALYSIS.md** - GitNexus comparison, market positioning
4. **docs/reference/** - Component-specific technical documentation
5. **docs/development/plans/** - Incomplete implementation plans

### Critical Components

#### Start Here (Core Value):
1. `retrieval/retrieval.py` - Hybrid search engine
2. `ranking/ranker.py` - Score merging logic
3. `budget/budget.py` - Token budget knapsack algorithm

#### Then Explore (Differentiators):
4. `vector_index/leann_index.py` - LEANN integration (97% storage savings)
5. `domain_map/domain_map.py` - SQLite keyword mapping
6. `backend_selector/backend_selector.py` - 6-level fallback strategy

#### Advanced (Extension Points):
7. `graph/graph.py` - Current: file-level PageRank
8. `graph/graph_tools.py` - Incomplete: call chain tracing
9. `mcp/tools.py` - MCP server tools

---

## Development Workflow

### Making Changes

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write Tests First** (TDD recommended)
   ```bash
   # Add test to appropriate file
   tests/unit/test_your_module.py
   
   # Run test (should fail initially)
   pytest tests/unit/test_your_module.py -xvs
   ```

3. **Implement Feature**
   ```bash
   # Edit source files
   src/ws_ctx_engine/your_module.py
   
   # Run tests until they pass
   pytest tests/unit/test_your_module.py -xvs
   ```

4. **Check Code Quality**
   ```bash
   black .                              # Format code
   ruff check .                        # Lint
   mypy src/                           # Type check
   ```

5. **Run Full Test Suite**
   ```bash
   pytest                               # All tests
   pytest --cov=ws_ctx_engine          # With coverage
   pytest -m benchmark --benchmark-only  # Performance tests
   ```

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

### Testing Guidelines

#### Unit Tests (`tests/unit/`)
Test individual functions in isolation:

```python
def test_hybrid_ranking_weights():
    """Verify semantic + pagerank scores merge correctly"""
    chunks = [
        CodeChunk(
            content="test",
            semantic_score=0.8,
            pagerank_score=0.6
        )
    ]
    
    result = rank_chunks(chunks, semantic_weight=0.6, pagerank_weight=0.4)
    
    assert result[0].final_score == pytest.approx(0.72)  # 0.6*0.8 + 0.4*0.6
```

#### Property-Based Tests (`tests/property/`)
Use Hypothesis to generate random inputs:

```python
@given(st.lists(st.floats(min_value=0, max_value=1), min_size=1))
def test_budget_selection_always_within_budget(scores):
    """Greedy knapsack never exceeds token budget"""
    chunks = [CodeChunk(score=s, tokens=100) for s in scores]
    budget = 1000
    
    selected = select_chunks(chunks, budget)
    
    assert sum(c.tokens for c in selected) <= budget * 0.8  # 80% for content
```

#### Integration Tests (`tests/integration/`)
Test full workflows:

```python
def test_pack_command_with_real_repo(tmp_path):
    """End-to-end test: index repo → query → pack → verify output"""
    # Setup
    repo_path = create_test_repo(tmp_path)
    
    # Run indexing
    run_command(["wsctx", "index", str(repo_path)])
    
    # Run query and pack
    result = run_command([
        "wsctx", "query", "authentication",
        "--repo", str(repo_path),
        "--format", "zip",
        "--budget", "50000"
    ])
    
    # Verify output exists and is valid ZIP
    assert result.exit_code == 0
    assert Path("output/ws-ctx-engine.zip").exists()
    assert zipfile.is_zipfile("output/ws-ctx-engine.zip")
```

---

## Priority Features to Implement

### 🚨 Critical (Complete These First)

#### 1. Complete Graph RAG Implementation
**Status**: Phase 4 partially complete  
**Effort**: 2-3 months (2 engineers)  
**Impact**: Neutralizes GitNexus advantage

**Tasks**:
- [ ] Finish CozoDB integration per `docs/reports/GRAPH_RAG_ROADMAP.md`
- [ ] Implement full knowledge graph (CALLS, IMPORTS, INHERITS edges)
- [ ] Build call chain tracing: `find_callers(symbol)`
- [ ] Add impact analysis: `blast_radius(symbol)`
- [ ] Create graph traversal queries (Cypher/Datalog)
- [ ] Wire into MCP server as tools

**Files to Modify**:
- `graph/graph.py` → Replace with CozoDB backend
- `graph/builder.py` → Extend edge extraction
- `graph/graph_tools.py` → Complete MCP tools
- `workflow/indexer.py` → Add graph construction phase

**Testing Requirements**:
- Unit tests for each edge type detection
- Integration test: trace call chains in test repo
- Benchmark: query latency <1s for 10k files

---

#### 2. Auto-Install Agent Skills
**Status**: Not implemented  
**Effort**: 2-3 weeks  
**Impact**: Eliminates 90% onboarding drop-off

**Implementation Pattern** (copy GitNexus):
```python
# wsctx init command
def init_agent_skills(repo_path: Path):
    """Auto-install agent skills to .claude/skills/"""
    
    skills_dir = Path.home() / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate skill templates
    skills = {
        "exploring.md": EXPLORING_SKILL_TEMPLATE,
        "debugging.md": DEBUGGING_SKILL_TEMPLATE,
        "impact_analysis.md": IMPACT_ANALYSIS_SKILL_TEMPLATE,
    }
    
    for skill_name, template in skills.items():
        skill_path = skills_dir / f"wsctx-{skill_name}"
        if not skill_path.exists():
            skill_path.write_text(template)
            log.info(f"✅ Installed skill: {skill_name}")
```

**Files to Create**:
- `cli/init.py` - New `wsctx init` command
- `templates/skills/` - Skill markdown templates
- Update `README.md` with one-command setup

---

#### 3. Claude Code Hooks
**Status**: Not implemented  
**Effort**: 1-2 weeks  
**Impact**: Matches GitNexus power user features

**Hook Types**:
```python
# PreToolUse: Enrich searches with graph context
@hook("PreToolUse")
def enrich_search_with_graph(tool_call: ToolCall):
    if tool_call.name == "wsctx_query":
        query = tool_call.arguments["query"]
        
        # Detect symbols in query
        symbols = extract_symbols(query)
        
        # Fetch related symbols from graph
        related = graph.get_related_symbols(symbols)
        
        # Augment query with context
        tool_call.arguments["query"] += f"\n\nRelated: {related}"

# PostToolUse: Auto-reindex after commits
@hook("PostToolUse")
def auto_reindex_after_commit(tool_call: ToolCall):
    if tool_call.name == "git_commit":
        repo_path = detect_repo_root()
        
        # Incremental reindex
        run_command(["wsctx", "reindex-domain", str(repo_path)])
        
        log.info("✅ Auto-reindexed after commit")
```

**Files to Create**:
- `hooks/pre_tool_use.py` - Search enrichment
- `hooks/post_tool_use.py` - Auto-reindex logic
- Update `docs/integrations/claude-desktop.md`

---

### ⭐ High Priority (Enterprise Differentiation)

#### 4. Token Budget Dashboard
**Status**: Not implemented  
**Effort**: 3-4 weeks  
**Impact**: CFO-approved cost savings

**Features**:
- Track LLM token usage over time
- Show cost savings vs naive approach (Repomix dump-all)
- Budget alerts and quotas
- Multi-model routing (cheapest provider)

**UI Mockup**:
```
Token Usage Dashboard
─────────────────────
Current Month: 2.3M tokens ($46 @ $20/1M)
Budget: 5M tokens
Remaining: 2.7M tokens

vs Repomix Equivalent:
- Repomix would use: 8.1M tokens
- Your savings: 5.8M tokens (72%)
- Cost savings: $116/month

Top Repos by Usage:
1. backend-api: 890k tokens
2. frontend-web: 654k tokens
3. data-pipeline: 432k tokens
```

**Files to Create**:
- `monitoring/dashboard.py` - Web dashboard (FastAPI + React)
- `monitoring/usage_tracker.py` - Token usage logging
- `monitoring/cost_calculator.py` - Cost comparison logic

---

#### 5. Enterprise Security Features
**Status**: Partially implemented (secret scanner exists)  
**Effort**: 2-3 months  
**Impact**: Enterprise sales qualification

**Features**:
- SOC 2 Type II compliance checklist
- Audit logs for all queries
- RBAC (role-based access control)
- SSO integration (Okta, Auth0)
- Secret redaction before packing

**Files to Modify**:
- `secret_scanner.py` → Enhance detection patterns
- `mcp/server.py` → Add authentication middleware
- `config/config.py` → Add RBAC configuration

---

### 💡 Medium Priority (UX Improvements)

#### 6. Web UI Demo
**Status**: Not implemented  
**Effort**: 1-2 months  
**Impact**: Investor-friendly demo

**Features**:
- Interactive file browser with importance heatmap
- Real-time query results
- Graph visualization (nodes = files, edges = imports)
- Token budget slider

**Tech Stack**:
- Frontend: React + Vite
- Backend: FastAPI
- Graph Viz: Cytoscape.js or D3.js

**Files to Create**:
- `webui/` - New directory for web application
- `webui/main.py` - FastAPI server
- `webui/src/` - React components

---

#### 7. Improved Error Messages
**Status**: Basic implementation  
**Effort**: 1 week  
**Impact**: Better developer experience

**Before**:
```
ImportError: No module named 'igraph'
```

**After**:
```
❌ python-igraph not available

This is an optional dependency for fast graph analysis.

Quick fix:
  pip install "ws-ctx-engine[all]"

Or configure fallback in .ws-ctx-engine.yaml:
  backends:
    graph: networkx

Performance impact:
  - igraph: <1s for 10k files (C++ backend)
  - networkx: <10s for 10k files (pure Python)
```

**Files to Modify**:
- `errors/errors.py` - Custom exception classes
- All `try/except` blocks throughout codebase

---

## Common Development Tasks

### Adding a New Language Resolver

1. **Create Resolver Class**
   ```python
   # chunker/resolvers/go_resolver.py
   from .base_resolver import BaseResolver
   
   class GoResolver(BaseResolver):
       LANGUAGE = "go"
       GRAMMAR_LANG = "go"
       
       def get_import_patterns(self) -> List[str]:
           return [r'^import\s+\(?([\s\S]*?)\)?']
       
       def get_function_pattern(self) -> str:
           return r'func\s+(\w+)\s*\((.*?)\)\s*(.*?)?'
   ```

2. **Register in Factory**
   ```python
   # chunker/resolvers/__init__.py
   RESOLVERS = {
       "python": PythonResolver,
       "javascript": JavaScriptResolver,
       "go": GoResolver,  # Add here
   }
   ```

3. **Add Tests**
   ```python
   # tests/unit/chunker/test_go_resolver.py
   def test_go_function_parsing():
       resolver = GoResolver()
       chunks = resolver.parse(go_source_code)
       assert len(chunks) > 0
   ```

---

### Adding a New MCP Tool

1. **Define Tool Function**
   ```python
   # mcp/tools.py
   @server.tool("wsctx_find_references")
   async def find_references(symbol: str, repo: Optional[str] = None):
       """Find all references to a symbol across codebase"""
       repo_path = resolve_repo(repo)
       index = load_index(repo_path)
       
       references = index.graph.find_references(symbol)
       
       return {
           "symbol": symbol,
           "references": [
               {"file": ref.file, "line": ref.line}
               for ref in references
           ]
       }
   ```

2. **Add Documentation**
   ```python
   @server.tool("wsctx_find_references")
   async def find_references(symbol: str, repo: Optional[str] = None):
       """
       Find all references to a symbol across codebase.
       
       Args:
           symbol: Symbol name to search for (e.g., "authenticate")
           repo: Repository path (optional, uses current dir if not specified)
       
       Returns:
           Dictionary with symbol name and list of references
       
       Example:
           >>> find_references("authenticate")
           {
               "symbol": "authenticate",
               "references": [
                   {"file": "src/auth.py", "line": 42},
                   {"file": "src/api.py", "line": 15}
               ]
           }
       """
   ```

3. **Test Locally**
   ```bash
   # Start MCP server
   wsctx mcp serve
   
   # In another terminal, test with MCP inspector
   npx @modelcontextprotocol/inspector
   ```

---

### Adding a New Output Format

1. **Create Formatter Class**
   ```python
   # formatters/toml_formatter.py
   from .base import BaseFormatter
   
   class TOMLFormatter(BaseFormatter):
       def render(self, metadata: Metadata, files: List[File]) -> str:
           output = []
           
           # Add manifest
           output.append("# Context Pack Manifest")
           output.append(f'total_files = {len(files)}')
           output.append(f'total_tokens = {metadata.total_tokens}')
           output.append("")
           
           # Add files
           for file in files:
               output.append(f'[[files]]')
               output.append(f'path = "{file.path}"')
               output.append(f'tokens = {file.token_count}')
               output.append(f'importance = {file.importance_score:.3f}')
               output.append('content = """')
               output.append(file.content)
               output.append('"""')
               output.append("")
           
           return "\n".join(output)
   ```

2. **Register in CLI**
   ```python
   # cli/cli.py
   @app.command()
   def query(
       query_text: str,
       format: Literal["xml", "zip", "json", "yaml", "md", "toml"] = "zip",
       # ... other params
   ):
   ```

3. **Add Tests**
   ```python
   # tests/unit/formatters/test_toml_formatter.py
   def test_toml_rendering():
       formatter = TOMLFormatter()
       output = formatter.render(metadata, files)
       
       # Parse TOML to verify structure
       import tomli
       data = tomli.loads(output)
       
       assert len(data["files"]) == len(files)
   ```

---

## Debugging Tips

### Enable Verbose Logging

```bash
wsctx query "test" --verbose
```

Log output shows:
- Backend selection decisions
- Index loading times
- Query execution breakdown
- Budget allocation

### Profile Performance

```bash
# Use cProfile for bottleneck identification
python -m cProfile -o profile.stats $(which wsctx) query "test"

# Visualize with snakeviz
pip install snakeviz
snakeviz profile.stats
```

### Debug Graph Issues

```python
# In Python REPL
from ws_ctx_engine.graph.graph import load_graph

graph = load_graph(".ws-ctx-engine/graph.pkl")

# Inspect nodes
print(f"Nodes: {len(graph.nodes())}")

# Inspect edges
print(f"Edges: {len(graph.edges())}")

# Check PageRank distribution
import numpy as np
scores = [graph.nodes[node]["pagerank"] for node in graph.nodes()]
print(f"PageRank stats: mean={np.mean(scores):.3f}, max={np.max(scores):.3f}")
```

### Test Backend Fallbacks

```bash
# Force fallback by temporarily renaming modules
mv ~/.venv/lib/python3.11/site-packages/igraph \
   ~/.venv/lib/python3.11/site-packages/igraph.bak

# Run command (should fall back to NetworkX)
wsctx query "test" --verbose

# Restore
mv ~/.venv/lib/python3.11/site-packages/igraph.bak \
   ~/.venv/lib/python3.11/site-packages/igraph
```

---

## Deployment

### Building for Production

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info/

# Build wheel and source distribution
python -m build

# Verify package contents
tar -tzf dist/ws_ctx_engine-*.tar.gz

# Test installation from local wheel
pip install dist/ws_ctx_engine-*.whl
```

### Publishing to PyPI

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*

# Or upload to TestPyPI first
twine upload --repository testpypi dist/*
```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install ws-ctx-engine[all]

# Copy application
COPY . .

# Set entry point
ENTRYPOINT ["wsctx"]
```

---

## Getting Help

### Documentation Resources

- **ARCHITECTURE_SUMMARY.md** - System design and component details
- **PROJECT_POSTMORTEM.md** - Historical context and lessons learned
- **COMPETITOR_ANALYSIS.md** - Market positioning and strategy
- **docs/** - Technical documentation per component
- **examples/** - Working code examples

### Code Navigation

Use these commands to explore codebase:

```bash
# Find all usages of a function
grep -r "def hybrid_ranking" src/

# Find imports of a module
grep -r "from.*retrieval import" src/

# Find TODO comments
grep -r "TODO" src/

# Generate call graph
pyan src/ws_ctx_engine/*.py --uses --no-defines --colored --grouped --dot > callgraph.dot
dot -Tpng callgraph.dot > callgraph.png
```

### Understanding Test Failures

When tests fail, check:

1. **Is it a flaky test?** Run again with different seed
   ```bash
   pytest tests/property/test_foo.py --hypothesis-seed=12345
   ```

2. **Is it environment-specific?** Check backend versions
   ```bash
   python -c "import leann; print(leann.__version__)"
   ```

3. **Is it a real bug?** Check stack trace carefully
   ```bash
   pytest tests/unit/test_bar.py -xvs  # Verbose output
   ```

---

## Contributing Guidelines

### Code Style

- **Formatting**: Black with 100-char line length
- **Linting**: Ruff (E, W, F, I, B, C4, UP rules)
- **Types**: Strict mypy (no `Any`, explicit types everywhere)
- **Docstrings**: Google style with type annotations

Example:
```python
def select_chunks(
    chunks: List[CodeChunk],
    budget: int,
    reserved_ratio: float = 0.2
) -> Tuple[List[CodeChunk], int]:
    """Select optimal subset of chunks within token budget.
    
    Uses greedy knapsack algorithm sorted by importance density.
    
    Args:
        chunks: Candidate chunks to select from
        budget: Total token budget
        reserved_ratio: Fraction to reserve for metadata (default: 0.2)
    
    Returns:
        Tuple of (selected chunks, remaining budget)
    
    Raises:
        ValueError: If budget is negative or chunks is empty
    """
```

### Commit Messages

Follow Conventional Commits:

```
feat: add LEANN vector index backend
fix: handle edge case in budget selection
docs: update architecture diagram
test: add property tests for hybrid ranking
refactor: extract backend selection logic
chore: update dependencies to latest versions
```

### Pull Request Process

1. **Fork repository** (if external contributor)
2. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make changes and commit**
4. **Run full test suite**
   ```bash
   pytest --cov=ws_ctx_engine --cov-report=term-missing
   ```
5. **Push and create PR**
6. **Respond to review feedback**

### Review Checklist

Before submitting PR, verify:

- [ ] All tests pass
- [ ] Code formatted with `black`
- [ ] No new lint warnings from `ruff`
- [ ] Type checking passes with `mypy`
- [ ] Coverage maintained or improved
- [ ] Documentation updated
- [ ] Commit messages follow convention

---

## Roadmap for Continuation

### Phase 1: Stabilization (Month 1-2)
- [ ] Fix any critical bugs in existing codebase
- [ ] Update documentation for current state
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Establish regular release cadence

### Phase 2: Graph RAG Completion (Month 3-5)
- [ ] Complete CozoDB integration
- [ ] Implement call chain tracing
- [ ] Add impact analysis tools
- [ ] Release v0.3.0 "Graph RAG"

### Phase 3: Agent Experience (Month 6)
- [ ] Auto-install agent skills
- [ ] Add Claude Code hooks
- [ ] Create one-command setup
- [ ] Release v0.4.0 "Agent-First"

### Phase 4: Community Building (Month 7-9)
- [ ] Launch Discord server
- [ ] Publish tutorial videos
- [ ] Create template repository
- [ ] Partner with AI agent teams

### Phase 5: Enterprise Features (Month 10-12)
- [ ] Token budget dashboard
- [ ] Audit logging
- [ ] RBAC implementation
- [ ] Release v1.0.0 "Enterprise Ready"

---

## Final Words

Continuing this project is not for the faint of heart. GitNexus has significant market momentum, and catching up will require:

1. **Technical Excellence**: Complete what we started (Graph RAG)
2. **Relentless Execution**: Ship monthly, iterate publicly
3. **Community Focus**: Build audience before product perfection
4. **Strategic Positioning**: Target enterprise where we excel

The code is solid. The architecture is sound. The technology works. What's needed now is someone with the vision and persistence to see it through.

If that's you, I'm rooting for you. Feel free to reach out with questions.

Good luck!

— zamery, Original Author

---

## Contact

- **GitHub Issues**: For bug reports and feature requests
- **Email**: zaob.ogn@gmail.com (original author, may not respond promptly)
- **Discord**: (future: community Discord server)

---

**License**: GPL-3.0-or-later  
**Attribution Required**: If you fork and distribute, you must preserve this license and provide attribution to the original authors.
