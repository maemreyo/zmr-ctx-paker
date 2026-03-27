# 🧹 Clean Code Preparation Report

**Date:** 2026-03-27  
**Project:** ws-ctx-engine  
**Total Size:** ~1.8GB (including venv)  
**Source Code:** ~2.6MB (src/)  

---

## 📊 Executive Summary

### 🔴 Critical Issues (Immediate Action Required)

| Issue | Impact | Priority | Action |
|-------|--------|----------|--------|
| **2 virtual environments** | +1.2GB disk | HIGH | Delete old venv |
| **Large output files** | +2.8MB | MEDIUM | Move to artifacts/ |
| **Huge mypy cache** | +50MB+ | LOW | Clean or gitignore |
| **Test result bloat** | +1.6MB | LOW | Archive old results |

### 🟡 Code Quality Issues

| File | Lines | Issue | Recommendation |
|------|-------|-------|----------------|
| `cli.py` | 1,791 | Too large | Split into subcommands |
| `vector_index.py` | 1,121 | Complex | Extract backend logic |
| `mcp/tools.py` | 980 | Monolithic | Split by tool category |

---

## 🗂️ Directory Analysis

### Large Directories

```
Rank  Size    Directory                      Action
─────────────────────────────────────────────────────
1     1.0G    venv/                          ⚠️ DELETE (old)
2     187M    _rust/                         ✅ Keep (Rust extension)
3     7.6M    tests/                         ✅ Keep (but organize)
4     4.4M    htmlcov/                       ⚠️ Gitignore
5     2.8M    output/                        ⚠️ Clean/Move
6     2.6M    src/                           ✅ Core codebase
7     1.6M    test_results/                  ⚠️ Archive old
8     924K    uv.lock                        ✅ Auto-generated
9     708K    docs/                          ✅ Documentation
```

### Generated Files (Should be in .gitignore)

#### 1. Virtual Environments - **1.2GB WASTED!**
```
❌ venv/                    (Python 3.11 - OLD)
❌ .venv/                   (Python 3.13 - Current)
```

**Action:** Delete `venv/` immediately - it's using Python 3.11 and taking 1GB!

```bash
rm -rf venv/
```

#### 2. MyPy Cache - ~50MB
```
.mypy_cache/
├── 3.11/numpy/__init__.data.json         (3.1MB)
├── 3.11/torch/_C/__init__.data.json      (2.5MB)
├── 3.11/torch/_C/_VariableFunctions.data.json (2.4MB)
└── ... (hundreds of files)
```

**Action:** Add to `.gitignore` or clean periodically

#### 3. Coverage Reports - 4.4MB
```
htmlcov/
├── *.html (coverage reports)
└── *.json
```

**Action:** Already in .gitignore? Verify and clean

#### 4. Build Artifacts
```
build/          (596KB)
dist/           (252KB)
*.egg-info/     (auto-generated)
```

**Action:** Should be in .gitignore

---

## 📝 Source Code Analysis

### Large Python Files (>500 lines)

#### 🔴 Critical (>1000 lines)

| File | Lines | Issue | Priority |
|------|-------|-------|----------|
| `src/ws_ctx_engine/cli/cli.py` | 1,791 | God class, too many responsibilities | HIGH |
| `src/ws_ctx_engine/vector_index/vector_index.py` | 1,121 | Complex backend logic | MEDIUM |

#### 🟡 Needs Attention (500-1000 lines)

| File | Lines | Issue | Priority |
|------|-------|-------|----------|
| `src/ws_ctx_engine/mcp/tools.py` | 980 | Many similar tool methods | MEDIUM |
| `src/ws_ctx_engine/workflow/query.py` | 729 | Workflow complexity | LOW |
| `src/ws_ctx_engine/graph/graph.py` | 687 | Graph abstraction OK | LOW |
| `src/ws_ctx_engine/retrieval/retrieval.py` | 660 | Retrieval logic OK | LOW |
| `src/ws_ctx_engine/workflow/indexer.py` | 562 | Indexer workflow OK | LOW |

### Test Files Analysis

#### Large Test Files (>500 lines)

| File | Lines | Issue |
|------|-------|-------|
| `tests/integration/test_cli.py` | 1,287 | Too many test cases |
| `tests/integration/test_cli_command_coverage.py` | 771 | Overlapping with above |
| `tests/integration/test_fallback_scenarios.py` | 664 | OK but long |
| `tests/unit/test_retrieval.py` | 603 | Comprehensive |
| `tests/unit/test_graph_bridge.py` | 586 | OK |
| `tests/property/test_cli_properties.py` | 586 | Property tests OK |

#### Duplicate Test Concerns

⚠️ **CLI Testing Overlap:**
- `test_cli.py` (1,287 lines)
- `test_cli_command_coverage.py` (771 lines)

**Recommendation:** Consider merging or better organization

---

## 🎯 Specific Recommendations

### Priority 1: Quick Wins (High Impact, Low Effort)

#### 1. Delete Old Virtual Environment ⚡
```bash
# Reclaim 1GB immediately
rm -rf venv/
```

**Impact:** -1GB disk space  
**Risk:** None (venv is regenerated)  
**Effort:** 1 command

#### 2. Clean Output Directory 📦
```bash
# Move large output files to archive
mkdir -p artifacts/output
mv output/*.yaml artifacts/output/
mv output/*.json artifacts/output/
mv output/*.md artifacts/output/
```

**Impact:** -2MB working directory  
**Risk:** None (regenerable)  
**Effort:** 5 minutes

#### 3. Update .gitignore 📝
```gitignore
# Add these if not already present

# Virtual environments
venv/
.venv/
.env/

# Type checking
.mypy_cache/

# Coverage
htmlcov/
.coverage
coverage.xml

# Build artifacts
build/
dist/
*.egg-info/
.eggs/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
mcp_tool_calls_*.log

# Test artifacts
test_results/stress_test/
test_results/mcp/comprehensive_test/
```

**Impact:** Cleaner repo  
**Risk:** None  
**Effort:** 10 minutes

---

### Priority 2: Code Refactoring (Medium Impact, Medium Effort)

#### 1. Split CLI Module 🔧

**Current:** `cli.py` (1,791 lines) - does everything

**Proposed Structure:**
```
cli/
├── __init__.py
├── main.py              # Main entry point (~100 lines)
├── commands/            # Subcommand modules
│   ├── index.py         # Index commands (~300 lines)
│   ├── query.py         # Query commands (~300 lines)
│   ├── mcp.py           # MCP commands (~300 lines)
│   ├── init.py          # Init commands (~200 lines)
│   └── doctor.py        # Doctor/cleanup commands (~200 lines)
└── utils.py             # Shared utilities (~200 lines)
```

**Benefits:**
- Easier to maintain
- Better testing isolation
- Clearer responsibilities
- Faster CI/CD

**Effort:** 2-3 hours  
**Risk:** LOW (well-tested code)

#### 2. Refactor MCP Tools Module 🛠️

**Current:** `mcp/tools.py` (980 lines) - all tools in one class

**Proposed Structure:**
```
mcp/
├── __init__.py
├── service.py           # MCPToolService main class (~200 lines)
├── tools/               # Tool implementations
│   ├── search.py        # Search tools (~200 lines)
│   ├── graph.py         # Graph tools (~250 lines)
│   ├── context.py       # Context tools (~200 lines)
│   └── admin.py         # Admin/status tools (~150 lines)
└── schemas.py           # Tool schemas (~100 lines)
```

**Benefits:**
- Better organization
- Easier to add new tools
- Clearer separation
- Better testing

**Effort:** 1-2 hours  
**Risk:** LOW (internal refactoring)

#### 3. Consolidate Test Files 🧪

**Merge overlapping tests:**
- `test_cli.py` + `test_cli_command_coverage.py` → `test_cli_comprehensive.py`

**Split large test files:**
- `test_retrieval.py` (603 lines) → `test_retrieval_search.py` + `test_retrieval_ranking.py`

**Benefits:**
- Faster test execution
- Better failure isolation
- Clearer test organization

**Effort:** 2-3 hours  
**Risk:** MEDIUM (need to ensure coverage)

---

### Priority 3: Long-term Improvements (Low Impact, High Effort)

#### 1. Vector Index Refactoring

**Current:** `vector_index/vector_index.py` (1,121 lines)

**Issues:**
- Multiple backends in one file
- Complex inheritance hierarchy
- Hard to test all paths

**Proposed:**
```python
# Extract backend-specific logic
vector_index/
├── base.py              # Abstract base class
├── faiss_index.py       # FAISS implementation
├── leann_index.py       # LEANN implementation
└── factory.py           # Backend factory
```

**Effort:** 4-6 hours  
**Impact:** Better maintainability  
**Priority:** LOW (working well currently)

---

## 📋 Action Plan

### Week 1: Cleanup Phase

#### Day 1: Remove Bloat (30 minutes)
```bash
# Delete old venv
rm -rf venv/

# Clean mypy cache
rm -rf .mypy_cache/

# Clean old test results
rm -rf test_results/mcp/comprehensive_test/
rm -rf test_results/stress_test/
```

#### Day 2: Update .gitignore (1 hour)
- Add all generated patterns
- Verify with `git status --ignored`
- Commit changes

#### Day 3: Archive Output (30 minutes)
```bash
mkdir -p artifacts/output
mv output/*.{yaml,json,md} artifacts/output/
```

**Result:** ~1GB freed, cleaner working directory

---

### Week 2: Code Organization

#### Day 1-2: CLI Refactoring (3 hours)
- Create `cli/commands/` directory
- Extract subcommands into modules
- Update imports
- Run tests to verify

#### Day 3: MCP Tools Refactoring (2 hours)
- Create `mcp/tools/` directory
- Group tools by category
- Extract schemas
- Test all tools

**Result:** Better organized, easier to navigate

---

### Week 3: Test Improvements

#### Day 1: Merge CLI Tests (2 hours)
- Combine overlapping tests
- Remove duplicates
- Ensure full coverage

#### Day 2: Split Large Tests (2 hours)
- Break down >500 line test files
- Organize by feature
- Update CI config

**Result:** Faster, clearer test suite

---

## 📊 Metrics & Goals

### Before Cleanup
- **Disk Usage:** 1.8GB
- **Largest File:** 1,791 lines (cli.py)
- **Test Files:** 65 files, 27K lines
- **Generated Files:** Mixed with source

### After Cleanup (Target)
- **Disk Usage:** ~800MB (-55%)
- **Largest File:** <500 lines (after refactoring)
- **Test Files:** Organized, deduplicated
- **Generated Files:** Properly ignored

### Success Metrics
- ✅ 1GB+ disk space freed
- ✅ No file >1000 lines
- ✅ All generated files in .gitignore
- ✅ Clear directory structure
- ✅ Faster CI/CD (<5 min)

---

## 🚀 Quick Start Commands

### Immediate Cleanup
```bash
# 1. Delete old venv (reclaim 1GB)
rm -rf venv/

# 2. Clean caches
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf .mypy_cache/
rm -rf .pytest_cache/

# 3. Clean build artifacts
rm -rf build/ dist/ *.egg-info/

# 4. Archive old outputs
mkdir -p artifacts/output
mv output/*.yaml artifacts/output/ 2>/dev/null || true
mv output/*.json artifacts/output/ 2>/dev/null || true
```

### Verify Cleanup
```bash
# Check disk usage
du -sh * | sort -rh | head -10

# Find remaining large files
find . -type f -size +100k -not -path "*/\.*" | xargs ls -lhS
```

---

## ⚠️ Risks & Mitigations

### Risk 1: Accidental Deletion
**Mitigation:** Use `git status` before deleting, verify nothing important

### Risk 2: Breaking Imports
**Mitigation:** Run full test suite after each refactoring

### Risk 3: Lost Test Coverage
**Mitigation:** Use `pytest-cov` to track coverage before/after

---

## 📞 Need Help?

If you encounter issues:
1. Check git history for original structure
2. Run tests frequently during refactoring
3. Use `git stash` before major changes
4. Create backup branch: `git checkout -b backup-before-cleanup`

---

**Report Generated:** 2026-03-27  
**Next Review:** After cleanup phase completion  
**Owner:** Development team
