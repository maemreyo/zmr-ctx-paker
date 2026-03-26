# Roadmap v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize ws-ctx-engine from alpha (crash-on-default) to a beta-quality competitive tool with intelligent compression, correct gitignore semantics, and incremental indexing.

**Architecture:** Sequential milestones — M1 (critical hotfix, prerequisite for all) → M2/M3/M4/M5 (can be tackled in any order after M1) → M6 (largest, last). Each milestone produces independently testable, working software.

**Tech Stack:** Python 3.11+, Typer CLI, pathspec>=0.12 (GitIgnoreSpec), FAISS (IndexIDMap2), tree-sitter, sentence-transformers, importlib.metadata, numpy (.npy embedding cache)

> **⚠️ Subsystem note:** This plan covers 6 milestones spanning ~15–22 days. Milestones M2–M6 are independent subsystems after M1 completes. If working with a team or in parallel worktrees, split M2, M3/M5, M4, and M6 into separate sessions after M1 lands.

---

## File Map

### M1 — Hotfix + Config Quick Cleanup
- Modify: `src/ws_ctx_engine/cli/cli.py:339–366` — add `_set_console_log_level`, fix `--version` usage
- Modify: `src/ws_ctx_engine/__init__.py:15` — replace hardcoded version with `importlib.metadata`
- Modify: `.ws-ctx-engine.yaml.example` — comment out aspirational fields
- Modify: `README.md` — sync missing commands, fix `--changed-files` inconsistency
- Test: `tests/unit/test_cli.py`

### M2 — Ignore Semantics + Language Honesty
- Modify: `pyproject.toml` — add `pathspec>=0.12` to core dependencies
- Modify: `src/ws_ctx_engine/chunker/base.py:1–49` — replace fnmatch with `GitIgnoreSpec`, add `INDEXED_EXTENSIONS`, add `collect_gitignore_patterns()`
- Modify: `src/ws_ctx_engine/cli/cli.py:60–89` — replace `_extract_gitignore_patterns` to use `GitIgnoreSpec` + support `!negation`
- Test: `tests/unit/test_base_chunker.py`, `tests/unit/test_cli.py`

### M3 — CLI UX + Output Polish
- Modify: `src/ws_ctx_engine/cli/cli.py` — `--stdout` flag, `--copy` flag, token count display
- Modify: `src/ws_ctx_engine/packer/xml_packer.py` — return token count from `pack()`
- Modify: `src/ws_ctx_engine/output/json_formatter.py` — return token count from `render()`
- Create: `docs/output-schema.md` — JSON Schema spec
- Modify: `README.md` — pipe examples, stdout/copy docs
- Test: `tests/unit/test_cli.py`

### M4 — Compression Layer
- Create: `src/ws_ctx_engine/output/compressor.py` — Tree-sitter signature extraction
- Modify: `src/ws_ctx_engine/cli/cli.py` — `--compress` flag
- Modify: `src/ws_ctx_engine/packer/xml_packer.py` — integrate compressor
- Modify: `src/ws_ctx_engine/packer/zip_packer.py` — integrate compressor
- Create: `docs/compression.md` — compression guide
- Test: `tests/unit/test_compressor.py` (new)

### M5 — Config Cleanup (Residual)
- Modify: `src/ws_ctx_engine/config/config.py` — remove/mark aspirational fields
- Test: `tests/unit/test_config.py`

### M6 — Incremental Indexing
- Modify: `src/ws_ctx_engine/vector_index/vector_index.py:529–` — migrate `FAISSIndex` to `IndexIDMap2`
- Modify: `src/ws_ctx_engine/workflow/indexer.py` — incremental reindex + hash diff detection
- Modify: `src/ws_ctx_engine/models/models.py` — add `to_dict()`/`from_dict()` + `EmbeddingCache`
- Modify: `src/ws_ctx_engine/cli/cli.py` — `--incremental` flag on `index` command
- Test: `tests/unit/test_vector_index.py`, `tests/unit/test_models.py`, `tests/integration/test_query_workflow.py`

---

## M1 — Hotfix + Config Quick Cleanup

### Task 1.1: Fix `_set_console_log_level` crash

**Files:**
- Modify: `src/ws_ctx_engine/cli/cli.py:39–44`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing test**

Note: `--help` is intercepted before the `main()` callback fires, so it won't trigger `_set_console_log_level`. Use a real subcommand to exercise the crash path.

```python
# tests/unit/test_cli.py — add to existing file
from typer.testing import CliRunner
from ws_ctx_engine.cli.cli import app

def test_wsctx_default_quiet_no_crash(tmp_path):
    """wsctx pack with default --quiet=True must not crash (invokes main() callback)."""
    runner = CliRunner()
    # Use a real subcommand so the @app.callback() main() fires; use a real path
    result = runner.invoke(app, ["pack", str(tmp_path)])
    # May fail due to empty repo — that is OK. Must NOT fail with NameError.
    assert "NameError" not in (result.output or "")
    assert result.exception is None or "NameError" not in str(result.exception)

def test_wsctx_no_quiet_no_crash(tmp_path):
    """wsctx --no-quiet pack must not crash."""
    runner = CliRunner()
    result = runner.invoke(app, ["--no-quiet", "pack", str(tmp_path)])
    assert "NameError" not in (result.output or "")
    assert result.exception is None or "NameError" not in str(result.exception)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_cli.py::test_wsctx_default_quiet_no_crash -v
```
Expected: FAIL with `NameError: name '_set_console_log_level' is not defined`

- [ ] **Step 3: Add `_set_console_log_level` to `cli.py`**

In `src/ws_ctx_engine/cli/cli.py`, after the `_set_agent_mode` function (after line 44), add:

```python
def _set_console_log_level(level: int) -> None:
    logging.getLogger("ws_ctx_engine").setLevel(level)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_cli.py::test_wsctx_default_quiet_no_crash tests/unit/test_cli.py::test_wsctx_no_quiet_no_crash -v
```
Expected: PASS

- [ ] **Step 5: Smoke test on live CLI**

```bash
wsctx --help
wsctx --version
```
Expected: no crash, no NameError

- [ ] **Step 6: Commit**

```bash
git add src/ws_ctx_engine/cli/cli.py tests/unit/test_cli.py
git commit -m "fix: define _set_console_log_level to fix default --quiet crash"
```

---

### Task 1.2: Dynamic `__version__` via `importlib.metadata`

**Files:**
- Modify: `src/ws_ctx_engine/__init__.py:15`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_cli.py — add
def test_version_matches_package_metadata():
    import importlib.metadata
    from ws_ctx_engine import __version__
    expected = importlib.metadata.version("ws-ctx-engine")
    assert __version__ == expected
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_cli.py::test_version_matches_package_metadata -v
```
Expected: FAIL — `__version__` is `"0.1.0"` but package metadata says `"0.1.10"`

- [ ] **Step 3: Replace hardcoded version in `__init__.py`**

Replace line 15 in `src/ws_ctx_engine/__init__.py`:

```python
# REMOVE:
__version__ = "0.1.0"

# ADD:
from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("ws-ctx-engine")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_cli.py::test_version_matches_package_metadata -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ws_ctx_engine/__init__.py tests/unit/test_cli.py
git commit -m "fix: use importlib.metadata for dynamic __version__"
```

---

### Task 1.3: Comment out aspirational YAML fields

**Files:**
- Modify: `.ws-ctx-engine.yaml.example`

- [ ] **Step 1: Audit which fields are NOT implemented**

Read `src/ws_ctx_engine/config/config.py` and compare against `.ws-ctx-engine.yaml.example`.
Fields to mark `# NOT YET IMPLEMENTED`:
- `advanced.pagerank_*`, `advanced.min/max_file_size`, `advanced.validate_roundtrip`

Fields to mark `# PLANNED — not active`:
- `performance.max_workers`, `performance.cache_embeddings`, `performance.incremental_index`

Fields to mark `# NOT YET IMPLEMENTED` (logging routing):
- `logging.level`, `logging.file`

- [ ] **Step 2: Edit `.ws-ctx-engine.yaml.example`**

For each aspirational field, add the appropriate comment above its line. Example:

```yaml
performance:
  # PLANNED — not active: parallel processing not yet implemented
  # max_workers: 4
  # PLANNED — not active: embedding cache not yet implemented
  # cache_embeddings: true
  # PLANNED — not active: incremental indexing not yet implemented
  # incremental_index: false
```

- [ ] **Step 3: Verify the example file is valid YAML (excluding commented lines)**

```bash
python -c "import yaml; yaml.safe_load(open('.ws-ctx-engine.yaml.example'))" && echo "Valid YAML"
```
Expected: `Valid YAML`

- [ ] **Step 4: Commit**

```bash
git add .ws-ctx-engine.yaml.example
git commit -m "docs: mark aspirational YAML config fields as NOT YET IMPLEMENTED"
```

---

### Task 1.4: Audit `--changed-files` flag in README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Check if `--changed-files` is exposed in CLI**

```bash
wsctx --help
wsctx pack --help
wsctx index --help
```

- [ ] **Step 2: Check README for `--changed-files` mentions**

```bash
grep -n "changed-files\|changed_files" README.md
```

- [ ] **Step 3: Decision — if flag is NOT in CLI, remove it from README**

If the flag is not implemented in `cli.py`, remove or comment the section from README and replace with:

```markdown
> **Note:** Incremental indexing (`--incremental`) is planned for a future release.
```

- [ ] **Step 4: Also add the 6 missing commands to README Quick Start**

Verify these commands are documented (add any missing):
```bash
wsctx doctor
wsctx index <path>
wsctx pack <path>
wsctx query "<text>"
wsctx pack <path> --format xml
wsctx pack <path> --format json
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: sync README commands, remove undocumented --changed-files flag"
```

---

## M2 — Ignore Semantics + Language Honesty

### Task 2.1: Add pathspec dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `pathspec>=0.12` to core dependencies**

In `pyproject.toml`, in the `[project]` `dependencies` list, add `"pathspec>=0.12"`.

- [ ] **Step 2: Install and verify**

```bash
pip install -e ".[dev]"
python -c "from pathspec import GitIgnoreSpec; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add pathspec>=0.12 for GitIgnoreSpec support"
```

---

### Task 2.2: Migrate file matching to `GitIgnoreSpec`

**Files:**
- Modify: `src/ws_ctx_engine/chunker/base.py`
- Test: `tests/unit/test_base_chunker.py`

- [ ] **Step 1: Write failing tests for GitIgnoreSpec behavior**

```python
# tests/unit/test_base_chunker.py — add
import tempfile, os
from pathlib import Path
from ws_ctx_engine.chunker.base import build_ignore_spec, collect_gitignore_patterns, _should_include_file

def test_negation_pattern_reinclude(tmp_path):
    """!pattern must re-include files excluded by earlier pattern."""
    (tmp_path / ".gitignore").write_text("*.log\n!important.log\n")
    (tmp_path / "debug.log").write_text("x")
    (tmp_path / "important.log").write_text("x")

    patterns = collect_gitignore_patterns(tmp_path)
    spec = build_ignore_spec(patterns)

    # debug.log must be excluded
    assert spec.match_file("debug.log"), "debug.log should be ignored"
    # important.log must be re-included (negation)
    assert not spec.match_file("important.log"), "important.log should NOT be ignored"

def test_subdirectory_gitignore_respected(tmp_path):
    """Patterns in subdirectory .gitignore must be scoped to that subdirectory."""
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / ".gitignore").write_text("*.tmp\n")
    (tmp_path / "root.tmp").write_text("x")
    (sub / "src.tmp").write_text("x")

    patterns = collect_gitignore_patterns(tmp_path)
    spec = build_ignore_spec(patterns)

    assert not spec.match_file("root.tmp"), "root.tmp should NOT be ignored (not in src/)"
    assert spec.match_file("src/src.tmp"), "src/src.tmp SHOULD be ignored"

def test_double_star_glob(tmp_path):
    """**/*.py must match files in subdirectories."""
    patterns = ["**/*.pyc"]
    spec = build_ignore_spec(patterns)
    assert spec.match_file("a/b/c.pyc")
    assert not spec.match_file("a/b/c.py")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/unit/test_base_chunker.py::test_negation_pattern_reinclude tests/unit/test_base_chunker.py::test_subdirectory_gitignore_respected tests/unit/test_base_chunker.py::test_double_star_glob -v
```
Expected: All FAIL (functions don't exist yet)

- [ ] **Step 3: Rewrite `chunker/base.py`**

Replace `src/ws_ctx_engine/chunker/base.py` with:

```python
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pathspec import GitIgnoreSpec

from ..models import CodeChunk

logger = logging.getLogger("ws_ctx_engine")

# Extensions with actual AST parsers. Files with other extensions will trigger a WARNING.
INDEXED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".md"
}


class ASTChunker(ABC):
    @abstractmethod
    def parse(self, repo_path: str, config=None) -> List[CodeChunk]:
        pass


def build_ignore_spec(patterns: List[str]) -> GitIgnoreSpec:
    """Build a gitignore spec that replicates actual Git behavior (including edge cases)."""
    return GitIgnoreSpec.from_lines(patterns)


def collect_gitignore_patterns(root: Path) -> List[str]:
    """Walk root recursively, collecting all .gitignore patterns with path normalization."""
    all_patterns: List[str] = []
    for gitignore_path in sorted(root.rglob(".gitignore")):
        relative_dir = gitignore_path.parent.relative_to(root)
        with open(gitignore_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.rstrip("\n").rstrip("\r")
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                # Scope subdirectory patterns to their directory
                if str(relative_dir) != ".":
                    if stripped.startswith("!"):
                        all_patterns.append(f"!{relative_dir}/{stripped[1:]}")
                    else:
                        all_patterns.append(f"{relative_dir}/{stripped}")
                else:
                    all_patterns.append(stripped)
    return all_patterns


def _should_include_file(
    file_path: Path,
    repo_root: Path,
    include_patterns: List[str],
    exclude_patterns: List[str],
) -> bool:
    relative_path = str(file_path.relative_to(repo_root))
    ext = file_path.suffix.lower()

    if ext and ext not in INDEXED_EXTENSIONS:
        logger.warning(
            f"[wsctx] No AST parser available for extension '{ext}' ({relative_path}). "
            "File will be included as plain text."
        )

    exclude_spec = build_ignore_spec(exclude_patterns)
    if exclude_spec.match_file(relative_path):
        return False

    include_spec = build_ignore_spec(include_patterns)
    return include_spec.match_file(relative_path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_base_chunker.py -v
```
Expected: All PASS

- [ ] **Step 5: Run full test suite to check no regressions**

```bash
pytest tests/unit/ -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add src/ws_ctx_engine/chunker/base.py tests/unit/test_base_chunker.py pyproject.toml
git commit -m "feat(M2): migrate to GitIgnoreSpec with negation + recursive .gitignore support"
```

---

### Task 2.3: Fix `_extract_gitignore_patterns` in `cli.py` to not strip negations

**Files:**
- Modify: `src/ws_ctx_engine/cli/cli.py:60–89`

The current implementation explicitly skips negation lines (`if line.startswith("!"): continue`). This breaks `!important.log` behavior. After M2.2, the CLI should delegate to `collect_gitignore_patterns()` from `chunker/base.py`.

- [ ] **Step 1: Write a test for the CLI gitignore helper**

```python
# tests/unit/test_cli.py — add
from ws_ctx_engine.cli.cli import _extract_gitignore_patterns
from pathlib import Path

def test_extract_negation_patterns_preserved(tmp_path):
    """_extract_gitignore_patterns must NOT strip !negation lines."""
    (tmp_path / ".gitignore").write_text("*.log\n!important.log\n")
    patterns = _extract_gitignore_patterns(tmp_path)
    assert "!important.log" in patterns or any("important" in p for p in patterns)
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_cli.py::test_extract_negation_patterns_preserved -v
```
Expected: FAIL — negation lines are currently stripped

- [ ] **Step 3: Refactor `_extract_gitignore_patterns` in `cli.py`**

Replace the function body (lines 60–89) to use `collect_gitignore_patterns`:

```python
from ..chunker.base import collect_gitignore_patterns as _collect_gitignore_patterns

def _extract_gitignore_patterns(repo_path: Path) -> list[str]:
    return _collect_gitignore_patterns(repo_path)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_cli.py::test_extract_negation_patterns_preserved -v
pytest tests/unit/ -v --tb=short
```
Expected: PASS, no regressions

- [ ] **Step 5: Commit**

```bash
git add src/ws_ctx_engine/cli/cli.py tests/unit/test_cli.py
git commit -m "fix(M2): preserve gitignore negation patterns in CLI gitignore extraction"
```

---

## M3 — CLI UX + Output Polish

### Task 3.1: Token count display after pack/query

**Files:**
- Modify: `src/ws_ctx_engine/cli/cli.py`
- Modify: `src/ws_ctx_engine/packer/xml_packer.py`
- Modify: `src/ws_ctx_engine/output/json_formatter.py`

- [ ] **Step 1: Write failing test for token count in pack output**

```python
# tests/unit/test_cli.py — add
def test_pack_command_shows_token_count(tmp_path, capsys):
    """pack command must display token count in output."""
    # Create a minimal python file to pack
    (tmp_path / "hello.py").write_text("def hello(): pass\n")
    runner = CliRunner()
    result = runner.invoke(app, ["pack", str(tmp_path), "--no-quiet"])
    # Token count should appear in output
    assert "token" in result.output.lower() or "token" in (result.stderr or "").lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_cli.py::test_pack_command_shows_token_count -v
```
Expected: FAIL (no token count in output yet)

- [ ] **Step 3: Check where pack outputs its final message**

Read `src/ws_ctx_engine/cli/cli.py` pack command (search for `console.print` near the end of `pack`):

```bash
grep -n "console.print\|packed\|✓\|success" src/ws_ctx_engine/cli/cli.py | head -30
```

- [ ] **Step 4: Add token count display to `pack` command in `cli.py`**

In the `pack` command's success block, retrieve `total_tokens` from the pack result and display:

```python
# After the pack call completes successfully:
total_tokens = result.get("total_tokens", 0)
token_budget = cfg.token_budget
console.print(
    f"[green]✓ Context packed[/green] "
    f"([bold]{total_tokens:,}[/bold] / {token_budget:,} tokens)"
)
```

For `--agent-mode`, include in NDJSON payload:
```python
_emit_ndjson({"event": "pack_complete", "total_tokens": total_tokens, "token_budget": token_budget})
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_cli.py -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add src/ws_ctx_engine/cli/cli.py
git commit -m "feat(M3): display token count after pack command"
```

---

### Task 3.2: `--stdout` flag

**Files:**
- Modify: `src/ws_ctx_engine/cli/cli.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_cli.py — add
def test_pack_stdout_flag_sends_content_to_stdout(tmp_path):
    """--stdout flag must send content to stdout, logs to stderr."""
    (tmp_path / "hello.py").write_text("def hello(): pass\n")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["pack", str(tmp_path), "--stdout", "--format", "xml"])
    assert result.exit_code == 0
    assert "<repository>" in result.output  # content on stdout

def test_pack_stdout_xml_is_valid(tmp_path):
    """--stdout with --format xml must produce parseable XML."""
    (tmp_path / "hello.py").write_text("def hello(): pass\n")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["pack", str(tmp_path), "--stdout", "--format", "xml"])
    from lxml import etree
    etree.fromstring(result.output.encode())  # must not raise
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_cli.py::test_pack_stdout_flag_sends_content_to_stdout tests/unit/test_cli.py::test_pack_stdout_xml_is_valid -v
```
Expected: FAIL — no `--stdout` option

- [ ] **Step 3: Add `--stdout` flag to `pack` command**

In the `pack` command signature, add:
```python
stdout: bool = typer.Option(
    False,
    "--stdout",
    help="Write packed output to stdout; logs go to stderr.",
)
```

In the pack command body, after generating the output string:
```python
if stdout:
    sys.stdout.write(output_str)
    sys.stdout.flush()
else:
    # existing file write behavior
    ...
```

When `--stdout` is active, redirect console (logs) to stderr:
```python
if stdout:
    console = Console(stderr=True)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_cli.py -v --tb=short
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ws_ctx_engine/cli/cli.py tests/unit/test_cli.py
git commit -m "feat(M3): add --stdout flag to pack command"
```

---

### Task 3.3: `--copy` clipboard flag

**Files:**
- Modify: `src/ws_ctx_engine/cli/cli.py`

- [ ] **Step 1: Add `--copy` flag to `pack` command**

Add option:
```python
copy: bool = typer.Option(
    False,
    "--copy",
    help="Copy packed output to clipboard.",
)
```

Implementation — use `pyperclip` if available, otherwise warn:
```python
if copy:
    try:
        import pyperclip
        pyperclip.copy(output_str)
        console.print("[green]✓ Copied to clipboard[/green]")
    except ImportError:
        console.print(
            "[yellow]⚠ --copy requires pyperclip: pip install pyperclip[/yellow]",
            err=True,
        )
```

Note: Do NOT add `pyperclip` to required deps — it's optional. Only import on demand.

- [ ] **Step 2: Test manually (no unit test needed for clipboard)**

```bash
wsctx pack . --copy --format xml
# Verify clipboard content with: pbpaste | head -5  (macOS)
```

- [ ] **Step 3: Add pipe examples to README**

Add section to README:
```markdown
## Pipe and Clipboard

```bash
# Pipe to clipboard (macOS)
wsctx pack . --format xml --stdout | pbcopy

# Pipe directly to Claude CLI
wsctx query "auth flow" --format xml --stdout | claude

# Use --copy flag (cross-platform)
wsctx pack . --copy

# Pipe to xmllint for validation
wsctx pack . --stdout --format xml | xmllint --noout -
```
```

- [ ] **Step 4: Commit**

```bash
git add src/ws_ctx_engine/cli/cli.py README.md
git commit -m "feat(M3): add --copy flag and pipe examples in README"
```

---

### Task 3.4: Create `docs/output-schema.md`

**Files:**
- Create: `docs/output-schema.md`

- [ ] **Step 1: Create the output schema doc**

Document the XML and JSON output formats with example schema. Include MCP response format.

Key sections:
1. XML format (fields: `<repository>`, `<metadata>`, `<files>`, `<file path= tokens=>`)
2. JSON format (fields: `metadata`, `files[]`, `total_tokens`)
3. NDJSON agent mode events (`index_start`, `pack_complete`, etc.)
4. MCP tool response format

- [ ] **Step 2: Commit**

```bash
git add docs/output-schema.md
git commit -m "docs(M3): add output format schema documentation"
```

---

## M4 — Compression Layer

### Task 4.1: Create `output/compressor.py` with Tree-sitter signature extraction

**Files:**
- Create: `src/ws_ctx_engine/output/compressor.py`
- Test: `tests/unit/test_compressor.py` (new)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_compressor.py — new file
import pytest
from ws_ctx_engine.output.compressor import compress_file_content, COMPRESSION_NODE_TYPES

def test_python_function_body_replaced_with_marker():
    """Python function body must be replaced with '# ... implementation'."""
    code = """\
def add(a, b):
    x = a + b
    return x
"""
    result = compress_file_content(code, ".py")
    assert "def add(a, b):" in result
    assert "# ... implementation" in result
    assert "x = a + b" not in result

def test_python_class_method_body_replaced():
    """Python class method bodies must be replaced."""
    code = """\
class Calc:
    def multiply(self, a, b):
        return a * b
"""
    result = compress_file_content(code, ".py")
    assert "class Calc:" in result
    assert "def multiply(self, a, b):" in result
    assert "# ... implementation" in result
    assert "return a * b" not in result

def test_unsupported_language_returns_original():
    """Files with unsupported extensions must be returned unchanged."""
    code = "hello world content"
    result = compress_file_content(code, ".unknown")
    assert result == code

def test_docstring_preserved_by_default():
    """Docstrings must be preserved when preserve_docstrings=True."""
    code = '''\
def greet(name):
    """Say hello."""
    return f"Hello, {name}"
'''
    result = compress_file_content(code, ".py", preserve_docstrings=True)
    assert '"""Say hello."""' in result

def test_compression_reduces_token_count():
    """Compressed content must have fewer tokens than original."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    code = "def heavy(x):\n" + "    y = x * 2\n" * 50 + "    return y\n"
    compressed = compress_file_content(code, ".py")
    assert len(enc.encode(compressed)) < len(enc.encode(code))
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_compressor.py -v
```
Expected: All FAIL (`ModuleNotFoundError: No module named 'ws_ctx_engine.output.compressor'`)

- [ ] **Step 3: Create `src/ws_ctx_engine/output/compressor.py`**

```python
"""
Compression layer for ws-ctx-engine.

Extracts function/class signatures using Tree-sitter, replacing bodies
with '# ... implementation' markers. Smart compression: high-relevance
files keep full content; lower-relevance files get signature-only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("ws_ctx_engine")

COMPRESSION_MARKER = "# ... implementation"

# Tree-sitter node types to compress per language
COMPRESSION_NODE_TYPES: dict[str, set[str]] = {
    "python": {"function_definition", "decorated_definition"},
    "javascript": {"function_declaration", "arrow_function", "method_definition"},
    "typescript": {"function_declaration", "method_definition", "interface_declaration"},
    "tsx": {"function_declaration", "method_definition"},
    "rust": {"function_item", "impl_item"},
}

# Map file extension → language key for COMPRESSION_NODE_TYPES
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rs": "rust",
}


@dataclass
class CompressionConfig:
    """Configuration for smart compression."""
    full_content_threshold: float = 0.7  # Files with relevance >= this get full content
    preserve_docstrings: bool = True


def compress_file_content(
    content: str,
    file_extension: str,
    preserve_docstrings: bool = True,
) -> str:
    """
    Extract function/class signatures, replacing bodies with COMPRESSION_MARKER.

    Falls back to returning original content if tree-sitter is unavailable
    or the language is not supported.
    """
    language = EXTENSION_TO_LANGUAGE.get(file_extension.lower())
    if language is None:
        return content  # Unsupported language — return unchanged

    try:
        return _compress_with_tree_sitter(content, language, preserve_docstrings)
    except ImportError:
        logger.debug("tree-sitter not available; skipping compression for %s", file_extension)
        return content
    except Exception as exc:
        logger.debug("Compression failed for %s: %s; returning original", file_extension, exc)
        return content


def _compress_with_tree_sitter(content: str, language: str, preserve_docstrings: bool) -> str:
    """Use Tree-sitter to parse and compress function/class bodies."""
    import tree_sitter  # noqa: PLC0415

    # Import language-specific parser
    lang_module_map = {
        "python": "tree_sitter_python",
        "javascript": "tree_sitter_javascript",
        "typescript": "tree_sitter_typescript",
        "tsx": "tree_sitter_typescript",
        "rust": "tree_sitter_rust",
    }
    lang_module = lang_module_map.get(language)
    if lang_module is None:
        return content

    import importlib
    try:
        lang_mod = importlib.import_module(lang_module)
        ts_language = tree_sitter.Language(lang_mod.language())
    except (ImportError, AttributeError):
        return content

    parser = tree_sitter.Parser(ts_language)
    tree = parser.parse(content.encode("utf-8"))

    node_types_to_compress = COMPRESSION_NODE_TYPES.get(language, set())
    if not node_types_to_compress:
        return content

    # Collect (start_byte, end_byte) replacements — from deepest to shallowest
    replacements: list[tuple[int, int, str]] = []
    _collect_body_replacements(tree.root_node, node_types_to_compress, content, replacements, preserve_docstrings)

    if not replacements:
        return content

    # Apply replacements in reverse order (deepest first, then outer)
    # Sort by start_byte descending to avoid offset issues
    replacements.sort(key=lambda r: r[0], reverse=True)

    encoded = bytearray(content.encode("utf-8"))
    for start, end, replacement in replacements:
        encoded[start:end] = replacement.encode("utf-8")

    return encoded.decode("utf-8")


def _collect_body_replacements(
    node: object,
    node_types: set[str],
    content: str,
    replacements: list[tuple[int, int, str]],
    preserve_docstrings: bool,
) -> None:
    """Recursively find function/class body nodes and record replacements."""
    # Access tree-sitter node attributes
    node_type: str = getattr(node, "type", "")
    children = getattr(node, "children", [])

    if node_type in node_types:
        # Find the body child node (typically last named child)
        body_node = _find_body_node(node)
        if body_node is not None:
            body_start: int = getattr(body_node, "start_byte", -1)
            body_end: int = getattr(body_node, "end_byte", -1)
            if body_start >= 0 and body_end > body_start:
                indent = _get_indent(content, body_start)
                docstring = ""
                if preserve_docstrings:
                    docstring = _extract_docstring(body_node, content)
                if docstring:
                    replacement = f"\n{indent}{docstring}\n{indent}{COMPRESSION_MARKER}\n"
                else:
                    replacement = f"\n{indent}{COMPRESSION_MARKER}\n"
                replacements.append((body_start, body_end, replacement))
                return  # Don't recurse into replaced body

    for child in children:
        _collect_body_replacements(child, node_types, content, replacements, preserve_docstrings)


def _find_body_node(node: object) -> Optional[object]:
    """Return the body child of a function/class node."""
    for child in getattr(node, "children", []):
        if getattr(child, "type", "") in {"block", "statement_block", "declaration_list"}:
            return child
    return None


def _get_indent(content: str, byte_offset: int) -> str:
    """Detect indentation level at the given byte offset."""
    text_before = content.encode("utf-8")[:byte_offset].decode("utf-8", errors="replace")
    last_line = text_before.rsplit("\n", 1)[-1] if "\n" in text_before else text_before
    return " " * (len(last_line) - len(last_line.lstrip()))


def _extract_docstring(body_node: object, content: str) -> str:
    """Extract the first string literal from the body (docstring), if any."""
    children = getattr(body_node, "children", [])
    for child in children:
        child_type = getattr(child, "type", "")
        if child_type in {"expression_statement", "string"}:
            # Check if this is a string literal (docstring)
            grandchildren = getattr(child, "children", [])
            for gc in grandchildren:
                if getattr(gc, "type", "") == "string":
                    start = getattr(gc, "start_byte", 0)
                    end = getattr(gc, "end_byte", 0)
                    return content.encode("utf-8")[start:end].decode("utf-8", errors="replace")
            if child_type == "string":
                start = getattr(child, "start_byte", 0)
                end = getattr(child, "end_byte", 0)
                return content.encode("utf-8")[start:end].decode("utf-8", errors="replace")
        break  # Only check the first statement
    return ""


def apply_compression_to_selected_files(
    selected_files: list[Any],
    config: Optional[CompressionConfig] = None,
) -> list[Any]:
    """
    Apply smart compression to selected files based on relevance score.

    High-relevance files (>= full_content_threshold) keep full content.
    Lower-relevance files get signature-only compression.
    """
    if config is None:
        config = CompressionConfig()

    compressed_count = 0
    original_total = 0
    compressed_total = 0

    for f in selected_files:
        relevance = getattr(f, "relevance_score", 0.0)
        content = getattr(f, "content", "")
        ext = getattr(f, "extension", "") or ""
        original_total += len(content)

        if relevance < config.full_content_threshold:
            new_content = compress_file_content(content, ext, config.preserve_docstrings)
            if new_content != content:
                f.content = new_content
                compressed_count += 1
            compressed_total += len(f.content)
        else:
            compressed_total += len(content)

    if compressed_count > 0:
        logger.info(
            "Compressed %d files: %d → %d chars (%.0f%% reduction)",
            compressed_count,
            original_total,
            compressed_total,
            100 * (1 - compressed_total / max(original_total, 1)),
        )

    return selected_files
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_compressor.py -v
```
Expected: PASS (tree-sitter tests may skip if not installed — that's OK)

- [ ] **Step 5: Commit**

```bash
git add src/ws_ctx_engine/output/compressor.py tests/unit/test_compressor.py
git commit -m "feat(M4): add output/compressor.py with Tree-sitter signature extraction"
```

---

### Task 4.2: `--compress` flag in CLI + integrate with packers

**Files:**
- Modify: `src/ws_ctx_engine/cli/cli.py`
- Modify: `src/ws_ctx_engine/packer/xml_packer.py`
- Modify: `src/ws_ctx_engine/packer/zip_packer.py`

- [ ] **Step 1: Write failing test for `--compress` flag**

```python
# tests/unit/test_cli.py — add
def test_pack_compress_flag_accepted(tmp_path):
    """--compress flag must be accepted without error."""
    (tmp_path / "hello.py").write_text("def hello():\n    return 'hi'\n")
    runner = CliRunner()
    result = runner.invoke(app, ["pack", str(tmp_path), "--compress"])
    assert result.exit_code == 0

def test_pack_compress_inserts_marker(tmp_path):
    """--compress with XML format must contain '# ... implementation' markers."""
    (tmp_path / "hello.py").write_text(
        "def hello():\n    x = 1\n    y = 2\n    return x + y\n"
    )
    runner = CliRunner()
    result = runner.invoke(
        app, ["pack", str(tmp_path), "--compress", "--stdout", "--format", "xml"]
    )
    assert result.exit_code == 0
    assert "# ... implementation" in result.output
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_cli.py::test_pack_compress_flag_accepted tests/unit/test_cli.py::test_pack_compress_inserts_marker -v
```
Expected: FAIL — no `--compress` option

- [ ] **Step 3: Add `--compress` to `pack` command in `cli.py`**

```python
compress: bool = typer.Option(
    False,
    "--compress",
    help="Apply smart compression: replace function bodies with signature markers.",
)
```

Pass `compress=compress` through to the packing workflow. After retrieving selected files and before packing:

```python
if compress:
    from ..output.compressor import apply_compression_to_selected_files, CompressionConfig
    selected_files = apply_compression_to_selected_files(selected_files, CompressionConfig())
```

- [ ] **Step 4: Add token reduction display for `--compress`**

After compression, compare pre/post token counts and display:

```python
if compress and original_tokens and compressed_tokens:
    reduction_pct = int(100 * (1 - compressed_tokens / original_tokens))
    console.print(
        f"[green]✓ Context packed with compression:[/green] "
        f"{original_tokens:,} → {compressed_tokens:,} tokens "
        f"([bold]{reduction_pct}%[/bold] reduction)"
    )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_cli.py -v --tb=short
pytest tests/unit/test_compressor.py -v
```

- [ ] **Step 6: Create `docs/compression.md`**

Document the compression feature:
- What it does (signature-only compression)
- Smart vs dumb compression comparison with Repomix
- Supported languages (Python, TypeScript, JavaScript, Rust)
- How relevance threshold works
- Examples of compressed output

- [ ] **Step 7: Commit**

```bash
git add src/ws_ctx_engine/cli/cli.py src/ws_ctx_engine/packer/xml_packer.py src/ws_ctx_engine/packer/zip_packer.py docs/compression.md tests/unit/test_cli.py
git commit -m "feat(M4): add --compress flag with smart relevance-based compression"
```

---

## M5 — Config Cleanup (Residual)

### Task 5.1: Audit and clean `config.py` aspirational fields

**Files:**
- Modify: `src/ws_ctx_engine/config/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Read `config/config.py` in full**

```bash
cat src/ws_ctx_engine/config/config.py
```

- [ ] **Step 2: Identify aspirational fields**

Fields that appear in the dataclass but are NOT actively used by the pipeline:
- Any `pagerank_*` tuning params
- `max_workers`, `cache_embeddings`, `incremental_index`
- `logging.level`, `logging.file`

- [ ] **Step 3: For each aspirational field, add a `# NOT YET IMPLEMENTED` comment in the dataclass**

Do NOT remove them (that would be a breaking change for users with existing configs). Just document clearly:

```python
# NOT YET IMPLEMENTED — accepted but has no effect
max_workers: int = 4
```

- [ ] **Step 4: Write a test that verifies aspirational fields load without error**

```python
# tests/unit/test_config.py — add
def test_aspirational_config_fields_load_without_error(tmp_path):
    """Loading config with aspirational fields must not raise."""
    config_yaml = """\
performance:
  max_workers: 8
  cache_embeddings: true
"""
    config_file = tmp_path / ".ws-ctx-engine.yaml"
    config_file.write_text(config_yaml)
    from ws_ctx_engine.config import Config
    cfg = Config.load(str(config_file))
    assert cfg is not None
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/unit/test_config.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/ws_ctx_engine/config/config.py tests/unit/test_config.py
git commit -m "docs(M5): mark aspirational config fields as NOT YET IMPLEMENTED"
```

---

## M6 — Incremental Indexing

### Task 6.1: Migrate FAISSIndex to `IndexIDMap2`

**Files:**
- Modify: `src/ws_ctx_engine/vector_index/vector_index.py:529–`
- Test: `tests/unit/test_vector_index.py`

- [ ] **Step 1: Write failing test for FAISS remove_ids capability**

```python
# tests/unit/test_vector_index.py — add
import pytest

def test_faiss_index_supports_remove_ids():
    """FAISSIndex must support remove_ids (requires IndexIDMap2, not IndexHNSWFlat)."""
    try:
        import faiss
        import numpy as np
    except ImportError:
        pytest.skip("faiss-cpu not installed")

    from ws_ctx_engine.vector_index.vector_index import FAISSIndex
    from ws_ctx_engine.models import CodeChunk

    chunks = [
        CodeChunk(
            path="a.py", start_line=1, end_line=5,
            content="def foo(): pass", symbols_defined=["foo"],
            symbols_referenced=[], language="python"
        ),
        CodeChunk(
            path="b.py", start_line=1, end_line=5,
            content="def bar(): pass", symbols_defined=["bar"],
            symbols_referenced=[], language="python"
        ),
    ]

    idx = FAISSIndex()
    idx.build(chunks)
    # After build, remove_ids must work
    idx.remove_paths(["a.py"])
    results = idx.search("foo function", top_k=5)
    result_paths = [r[0] for r in results]
    assert "a.py" not in result_paths, "Removed path must not appear in search results"
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_vector_index.py::test_faiss_index_supports_remove_ids -v
```
Expected: FAIL — `FAISSIndex` uses `IndexHNSWFlat` which has no `remove_ids`; no `remove_paths` method exists

- [ ] **Step 3: Migrate `FAISSIndex` in `vector_index.py` to use `IndexIDMap2`**

Locate `FAISSIndex` class at line 529. Key changes:

**Performance trade-off note:** This migration changes the underlying index from `IndexHNSWFlat` (approximate nearest-neighbour, fast for large repos) to `IndexFlatIP` (exact inner-product search, O(n) scan). This is a deliberate trade for `remove_ids()` support. For repos with <10k files the performance difference is negligible; document this in a code comment.

1. Add `_id_to_path: dict[int, str]` as an instance variable alongside `_file_paths`. This is the stable mapping that survives removals without positional corruption.

2. Change `build()` to use `IndexIDMap2` wrapping `IndexFlatIP` and use a stable ID counter:
```python
def build(self, chunks: List[CodeChunk]) -> None:
    import faiss
    import numpy as np
    # ... existing embedding generation ...

    embeddings = np.array(all_embeddings, dtype=np.float32)
    dim = embeddings.shape[1]

    # NOTE: IndexFlatIP (exact search) replaces IndexHNSWFlat (approximate) to
    # gain remove_ids() support via IndexIDMap2. Acceptable for repos < 10k files;
    # revisit if query latency becomes a concern.
    base = faiss.IndexFlatIP(dim)
    self._index = faiss.IndexIDMap2(base)

    ids = np.arange(len(self._file_paths), dtype=np.int64)
    self._index.add_with_ids(embeddings, ids)
    self._embedding_dim = dim
    # Stable ID → path mapping (survives removals without positional shift)
    self._id_to_path: dict[int, str] = {i: p for i, p in enumerate(self._file_paths)}
    self._next_id: int = len(self._file_paths)
```

3. Add `remove_paths()` method that uses the stable `_id_to_path` mapping:
```python
def remove_paths(self, paths: list[str]) -> None:
    """Remove vectors for given file paths from the index."""
    import numpy as np

    paths_set = set(paths)
    ids_to_remove = [fid for fid, p in self._id_to_path.items() if p in paths_set]
    if not ids_to_remove:
        return
    self._index.remove_ids(np.array(ids_to_remove, dtype=np.int64))
    paths_removed: set[str] = set()
    for fid in ids_to_remove:
        paths_removed.add(self._id_to_path.pop(fid))
    # One O(n) pass instead of repeated O(n) list.remove() calls
    self._file_paths = [p for p in self._file_paths if p not in paths_removed]
```

4. Update `search()` to resolve IDs via `_id_to_path` instead of positional list indexing:
```python
def search(self, query: str, top_k: int = 10) -> List[tuple[str, float]]:
    # ... existing embedding of query ...
    distances, indices = self._index.search(query_vec, top_k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        path = self._id_to_path.get(int(idx))
        if path is not None:
            results.append((path, float(dist)))
    return results
```

4. Add `add_chunks()` method to `FAISSIndex` — needed by `incremental_update()` in Task 6.3:

```python
def add_chunks(
    self,
    chunks: List[CodeChunk],
    embedding_cache: Optional["EmbeddingCache"] = None,
) -> None:
    """Embed new chunks and add their vectors to the live IndexIDMap2."""
    import hashlib
    import numpy as np

    if not chunks:
        return
    if self._embedding_generator is None:
        raise RuntimeError("Index not built. Call build() first.")

    # Group by file path (same pattern as build())
    file_to_chunks: dict[str, list[CodeChunk]] = {}
    for c in chunks:
        file_to_chunks.setdefault(c.path, []).append(c)

    texts: list[str] = []
    new_paths: list[str] = []
    for file_path, file_chunks in file_to_chunks.items():
        new_paths.append(file_path)
        texts.append("\n".join(c.content for c in file_chunks))
        symbols: list[str] = []
        for c in file_chunks:
            symbols.extend(c.symbols_defined)
        self._file_symbols[file_path] = symbols

    # Resolve cache hits / misses
    to_embed_idx: list[int] = []
    embeddings: list = [None] * len(texts)
    for i, text in enumerate(texts):
        h = hashlib.sha256(text.encode()).hexdigest()
        if embedding_cache is not None:
            cached = embedding_cache.get(h)
            if cached is not None:
                embeddings[i] = cached
                continue
        to_embed_idx.append(i)

    if to_embed_idx:
        raw = self._embedding_generator.encode([texts[i] for i in to_embed_idx])
        for j, i in enumerate(to_embed_idx):
            embeddings[i] = raw[j]
            if embedding_cache is not None:
                h = hashlib.sha256(texts[i].encode()).hexdigest()
                embedding_cache.put(h, raw[j])

    vecs = np.array(embeddings, dtype=np.float32)
    new_ids = np.arange(
        self._next_id, self._next_id + len(new_paths), dtype=np.int64
    )
    self._index.add_with_ids(vecs, new_ids)

    for fid, path in zip(new_ids, new_paths):
        self._id_to_path[int(fid)] = path
        self._file_paths.append(path)
    self._next_id += len(new_paths)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/unit/test_vector_index.py -v --tb=short
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ws_ctx_engine/vector_index/vector_index.py tests/unit/test_vector_index.py
git commit -m "feat(M6): migrate FAISSIndex to IndexIDMap2, add remove_paths() and add_chunks()"
```

---

### Task 6.2: Add `to_dict()`/`from_dict()` + `EmbeddingCache` to `models.py`

**Files:**
- Modify: `src/ws_ctx_engine/models/models.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_models.py — add
from ws_ctx_engine.models.models import CodeChunk, EmbeddingCache
import tempfile, json
from pathlib import Path

def test_code_chunk_to_dict_roundtrip():
    chunk = CodeChunk(
        path="src/foo.py", start_line=1, end_line=10,
        content="def foo(): pass",
        symbols_defined=["foo"], symbols_referenced=[],
        language="python"
    )
    d = chunk.to_dict()
    restored = CodeChunk.from_dict(d)
    assert restored.path == chunk.path
    assert restored.content == chunk.content
    assert restored.symbols_defined == chunk.symbols_defined

def test_embedding_cache_put_and_get():
    cache = EmbeddingCache()
    import numpy as np
    vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    cache.put("abc123", vec)
    result = cache.get("abc123")
    assert result is not None
    np.testing.assert_array_almost_equal(result, vec)

def test_embedding_cache_miss_returns_none():
    cache = EmbeddingCache()
    assert cache.get("nonexistent_hash") is None

def test_embedding_cache_save_and_load(tmp_path):
    import numpy as np
    cache = EmbeddingCache()
    vec = np.array([0.5, 0.6], dtype=np.float32)
    cache.put("hash1", vec)
    cache.save(tmp_path)

    loaded = EmbeddingCache.load(tmp_path)
    result = loaded.get("hash1")
    assert result is not None
    np.testing.assert_array_almost_equal(result, vec)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/unit/test_models.py -v
```
Expected: FAIL — `to_dict`/`from_dict` not on `CodeChunk`, no `EmbeddingCache`

- [ ] **Step 3: Add `to_dict()`/`from_dict()` to `CodeChunk` in `models.py`**

```python
def to_dict(self) -> dict:
    return {
        "path": self.path,
        "start_line": self.start_line,
        "end_line": self.end_line,
        "content": self.content,
        "symbols_defined": self.symbols_defined,
        "symbols_referenced": self.symbols_referenced,
        "language": self.language,
    }

@classmethod
def from_dict(cls, d: dict) -> "CodeChunk":
    return cls(
        path=d["path"],
        start_line=d["start_line"],
        end_line=d["end_line"],
        content=d["content"],
        symbols_defined=d["symbols_defined"],
        symbols_referenced=d["symbols_referenced"],
        language=d["language"],
    )
```

- [ ] **Step 4: Add `EmbeddingCache` class to `models.py`**

```python
import json
import numpy as np
from pathlib import Path
from typing import Optional

class EmbeddingCache:
    """
    Content-hash → embedding vector cache.

    Persists embeddings to disk as .npy + JSON index to avoid re-embedding
    unchanged files on incremental index updates.
    """

    EMBEDDINGS_FILE = "embeddings.npy"
    INDEX_FILE = "embedding_index.json"

    def __init__(self) -> None:
        self._vectors: list[np.ndarray] = []
        self._hash_to_idx: dict[str, int] = {}

    def put(self, content_hash: str, vector: np.ndarray) -> None:
        idx = len(self._vectors)
        self._vectors.append(vector.astype(np.float32))
        self._hash_to_idx[content_hash] = idx

    def get(self, content_hash: str) -> Optional[np.ndarray]:
        idx = self._hash_to_idx.get(content_hash)
        if idx is None:
            return None
        return self._vectors[idx]

    def save(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        if self._vectors:
            np.save(cache_dir / self.EMBEDDINGS_FILE, np.stack(self._vectors))
        with open(cache_dir / self.INDEX_FILE, "w") as f:
            json.dump({"hash_to_idx": self._hash_to_idx}, f)

    @classmethod
    def load(cls, cache_dir: Path) -> "EmbeddingCache":
        instance = cls()
        index_path = cache_dir / cls.INDEX_FILE
        embeddings_path = cache_dir / cls.EMBEDDINGS_FILE
        if not index_path.exists() or not embeddings_path.exists():
            return instance
        with open(index_path) as f:
            data = json.load(f)
        instance._hash_to_idx = data.get("hash_to_idx", {})
        all_vecs = np.load(embeddings_path)
        instance._vectors = [all_vecs[i] for i in range(len(all_vecs))]
        return instance
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/unit/test_models.py -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/ws_ctx_engine/models/models.py tests/unit/test_models.py
git commit -m "feat(M6): add CodeChunk serialization and EmbeddingCache to models"
```

---

### Task 6.3: Incremental reindex logic in `indexer.py`

**Files:**
- Modify: `src/ws_ctx_engine/workflow/indexer.py`
- Modify: `src/ws_ctx_engine/cli/cli.py`
- Test: `tests/integration/test_query_workflow.py`

- [ ] **Step 1: Write failing integration test**

```python
# tests/integration/test_query_workflow.py — add
import tempfile
from pathlib import Path
import pytest

def test_incremental_index_only_reindexes_changed_file(tmp_path):
    """After full index, modifying one file must re-embed only that file."""
    pytest.importorskip("sentence_transformers")

    (tmp_path / "a.py").write_text("def alpha(): pass\n")
    (tmp_path / "b.py").write_text("def beta(): pass\n")

    from ws_ctx_engine.workflow.indexer import index_repository, incremental_update
    from ws_ctx_engine.config import Config

    cfg = Config()
    index_repository(str(tmp_path), config=cfg, index_dir=str(tmp_path / ".ws-ctx-engine"))

    # Modify a.py
    (tmp_path / "a.py").write_text("def alpha_modified(): return 42\n")

    result = incremental_update(
        str(tmp_path),
        config=cfg,
        index_dir=str(tmp_path / ".ws-ctx-engine"),
    )
    assert result.get("reindexed_files") == ["a.py"] or result.get("reindexed_count") == 1
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/integration/test_query_workflow.py::test_incremental_index_only_reindexes_changed_file -v
```
Expected: FAIL — no `incremental_update` function exists

- [ ] **Step 3: Read `workflow/indexer.py` to understand current structure**

```bash
head -100 src/ws_ctx_engine/workflow/indexer.py
```

- [ ] **Step 4: Add `incremental_update()` function to `indexer.py`**

This uses the `remove_paths()` added in Task 6.1 and the `EmbeddingCache` from Task 6.2. Prerequisite: Tasks 6.1 and 6.2 must be complete before implementing this task.

```python
def incremental_update(
    repo_path: str,
    config: Optional[Config] = None,
    index_dir: str = ".ws-ctx-engine",
) -> dict:
    """
    Update only changed/deleted files in an existing index.

    - Removes vectors for deleted/changed files using FAISSIndex.remove_paths().
    - Re-parses and re-embeds only changed/new files (using EmbeddingCache for hits).
    - Falls back to full rebuild if no existing index found.

    Returns dict with keys: reindexed_count, deleted_count, reindexed_files.
    """
    import hashlib
    import json
    from pathlib import Path

    from ..models.models import EmbeddingCache

    index_path = Path(index_dir)
    metadata_file = index_path / "metadata.json"

    # No existing index → full build
    if not metadata_file.exists():
        logger.info("No existing index found; running full index.")
        index_repository(repo_path, config=config, index_dir=index_dir)
        return {"reindexed_count": -1, "deleted_count": 0, "reindexed_files": []}

    with open(metadata_file) as f:
        meta = json.load(f)
    old_hashes: dict[str, str] = meta.get("file_hashes", {})

    # Compute current hashes (exclude the index dir itself)
    repo = Path(repo_path)
    index_abs = index_path.resolve()
    current_hashes: dict[str, str] = {}
    for fp in repo.rglob("*"):
        if not fp.is_file():
            continue
        try:
            if fp.resolve().is_relative_to(index_abs):
                continue
        except ValueError:
            pass
        rel = str(fp.relative_to(repo))
        try:
            current_hashes[rel] = hashlib.sha256(fp.read_bytes()).hexdigest()
        except (IOError, OSError):
            pass

    changed = [p for p, h in old_hashes.items() if p in current_hashes and current_hashes[p] != h]
    deleted = [p for p in old_hashes if p not in current_hashes]
    new_files = [p for p in current_hashes if p not in old_hashes]
    to_reindex = changed + new_files

    logger.info(
        "Incremental update: %d changed, %d new, %d deleted",
        len(changed), len(new_files), len(deleted),
    )

    if not to_reindex and not deleted:
        logger.info("Index is up-to-date; nothing to do.")
        return {"reindexed_count": 0, "deleted_count": 0, "reindexed_files": []}

    # Load existing vector index and embedding cache
    from ..vector_index import load_vector_index
    vector_idx = load_vector_index(str(index_path / "vector_index"))
    cache = EmbeddingCache.load(index_path)

    # Step 1: remove stale/deleted vectors
    paths_to_remove = list(set(deleted + changed))
    if paths_to_remove and hasattr(vector_idx, "remove_paths"):
        vector_idx.remove_paths(paths_to_remove)
        logger.info("Removed %d stale vectors from index", len(paths_to_remove))
    elif paths_to_remove:
        # LEANN or other backend without remove_paths — fall back to full rebuild
        logger.warning(
            "Backend '%s' does not support incremental remove; falling back to full rebuild.",
            type(vector_idx).__name__,
        )
        index_repository(repo_path, config=config, index_dir=index_dir)
        return {"reindexed_count": len(to_reindex), "deleted_count": len(deleted), "reindexed_files": to_reindex}

    # Step 2: parse + embed only changed/new files
    if to_reindex:
        from ..chunker import parse_with_fallback
        cfg = config or Config()
        new_chunks = [
            chunk for chunk in parse_with_fallback(repo_path, cfg)
            if chunk.path in set(to_reindex)
        ]
        if new_chunks:
            vector_idx.add_chunks(new_chunks, embedding_cache=cache)
            cache.save(index_path)
            logger.info("Re-embedded %d files (%d chunks)", len(to_reindex), len(new_chunks))

    # Step 3: save updated index + metadata
    vector_idx.save(str(index_path / "vector_index"))
    new_hashes = {**old_hashes, **{p: current_hashes[p] for p in to_reindex}}
    for p in deleted:
        new_hashes.pop(p, None)
    meta["file_hashes"] = new_hashes
    with open(metadata_file, "w") as f:
        json.dump(meta, f)

    return {
        "reindexed_count": len(to_reindex),
        "deleted_count": len(deleted),
        "reindexed_files": to_reindex,
    }
```

**Implementation note on LEANN:** If `load_vector_index()` returns a LEANN-based backend, it likely lacks `remove_paths()`. The code above gracefully falls back to full rebuild for those backends, documented in the log. After M6 ships, a LEANN-specific incremental path can be added.

- [ ] **Step 5: Add `--incremental` flag to `index` command in `cli.py`**

```python
incremental: bool = typer.Option(
    False,
    "--incremental",
    help="Only re-index files that have changed since last index.",
)
```

In the `index` command body:
```python
if incremental:
    from ..workflow.indexer import incremental_update
    result = incremental_update(repo_path, config=cfg, index_dir=index_dir)
    console.print(
        f"[green]✓ Incremental update:[/green] "
        f"{result['reindexed_count']} files re-indexed, "
        f"{result['deleted_count']} removed."
    )
else:
    index_repository(repo_path, config=cfg, index_dir=index_dir)
```

- [ ] **Step 6: Add delete-then-search and full-rebuild non-regression tests**

```python
# tests/integration/test_query_workflow.py — add

def test_incremental_index_deleted_file_absent_from_results(tmp_path):
    """After incremental update, a deleted file must not appear in search results."""
    pytest.importorskip("sentence_transformers")

    (tmp_path / "a.py").write_text("def alpha(): pass\n")
    (tmp_path / "b.py").write_text("def beta(): pass\n")

    from ws_ctx_engine.workflow.indexer import index_repository, incremental_update
    from ws_ctx_engine.workflow.query import search_codebase
    from ws_ctx_engine.config import Config

    cfg = Config()
    index_dir = str(tmp_path / ".ws-ctx-engine")
    index_repository(str(tmp_path), config=cfg, index_dir=index_dir)

    # Delete b.py
    (tmp_path / "b.py").unlink()

    incremental_update(str(tmp_path), config=cfg, index_dir=index_dir)

    results = search_codebase("beta function", str(tmp_path), config=cfg, index_dir=index_dir)
    result_paths = [r[0] for r in results]
    assert "b.py" not in result_paths, "Deleted file must not appear in search results"


def test_full_rebuild_non_regression(tmp_path):
    """Full rebuild after incremental update must produce correct results."""
    pytest.importorskip("sentence_transformers")

    (tmp_path / "a.py").write_text("def alpha(): pass\n")

    from ws_ctx_engine.workflow.indexer import index_repository
    from ws_ctx_engine.workflow.query import search_codebase
    from ws_ctx_engine.config import Config

    cfg = Config()
    index_dir = str(tmp_path / ".ws-ctx-engine")

    # Full build → search → full rebuild → search again
    index_repository(str(tmp_path), config=cfg, index_dir=index_dir)
    results_before = search_codebase("alpha function", str(tmp_path), config=cfg, index_dir=index_dir)

    index_repository(str(tmp_path), config=cfg, index_dir=index_dir)
    results_after = search_codebase("alpha function", str(tmp_path), config=cfg, index_dir=index_dir)

    assert [r[0] for r in results_after] == [r[0] for r in results_before], \
        "Full rebuild must produce identical results"
```

- [ ] **Step 7: Run integration tests**

```bash
pytest tests/integration/test_query_workflow.py -v --tb=short
```

- [ ] **Step 8: LEANN compatibility check**

Read `src/ws_ctx_engine/vector_index/leann_index.py` and check whether it supports `remove_paths()`:

```bash
grep -n "remove\|incremental\|update" src/ws_ctx_engine/vector_index/leann_index.py
```

If LEANN doesn't support `remove_ids`, add a comment at the top of `leann_index.py`:
```python
# NOTE: LEANN does not yet support incremental updates (remove_ids / remove_paths).
# wsctx index --incremental falls back to full rebuild when LEANN backend is active.
```

- [ ] **Step 9: Commit**

```bash
git add src/ws_ctx_engine/workflow/indexer.py src/ws_ctx_engine/cli/cli.py tests/integration/test_query_workflow.py
git commit -m "feat(M6): add incremental_update() with true partial re-embed and --incremental flag"
```

---

### Task 6.4: Embedding cache integration

**Files:**
- Modify: `src/ws_ctx_engine/workflow/indexer.py`
- Modify: `src/ws_ctx_engine/vector_index/vector_index.py`

- [ ] **Step 1: Write failing test for embedding cache**

```python
# tests/unit/test_vector_index.py — add
def test_faiss_build_uses_embedding_cache(tmp_path):
    """Second build with same content must use cache (no re-embedding)."""
    pytest.importorskip("faiss")
    pytest.importorskip("sentence_transformers")
    import numpy as np
    from ws_ctx_engine.vector_index.vector_index import FAISSIndex
    from ws_ctx_engine.models import CodeChunk
    from ws_ctx_engine.models.models import EmbeddingCache

    chunks = [
        CodeChunk(
            path="a.py", start_line=1, end_line=3,
            content="def foo(): pass",
            symbols_defined=["foo"], symbols_referenced=[], language="python"
        )
    ]

    cache = EmbeddingCache()
    idx = FAISSIndex()
    idx.build(chunks, embedding_cache=cache)

    # Cache should now contain the embedding for "def foo(): pass"
    import hashlib
    content_hash = hashlib.sha256(chunks[0].content.encode()).hexdigest()
    assert cache.get(content_hash) is not None, "Embedding must be stored in cache"
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/unit/test_vector_index.py::test_faiss_build_uses_embedding_cache -v
```
Expected: FAIL — `build()` doesn't accept `embedding_cache` param

- [ ] **Step 3: Update `FAISSIndex.build()` to accept optional `embedding_cache`**

```python
def build(
    self,
    chunks: List[CodeChunk],
    embedding_cache: Optional["EmbeddingCache"] = None,
) -> None:
    import hashlib
    # ...existing setup...

    texts_to_embed = []
    cached_embeddings = {}
    for i, (file_path, text) in enumerate(zip(self._file_paths, texts)):
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        if embedding_cache is not None:
            cached = embedding_cache.get(content_hash)
            if cached is not None:
                cached_embeddings[i] = cached
                continue
        texts_to_embed.append((i, file_path, text, content_hash))

    # Embed only cache misses
    # ... generate embeddings for texts_to_embed ...
    # Store in cache
    if embedding_cache is not None:
        for (i, fp, text, h), vec in zip(texts_to_embed, new_embeddings):
            embedding_cache.put(h, vec)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_vector_index.py -v --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add src/ws_ctx_engine/vector_index/vector_index.py tests/unit/test_vector_index.py
git commit -m "feat(M6): integrate EmbeddingCache into FAISSIndex.build() for incremental speedup"
```

---

## Final Verification

After all milestones, run the full acceptance test suite:

- [ ] **M1 Acceptance**

```bash
wsctx --help              # No crash
wsctx --version           # Shows version from pyproject.toml (0.1.10)
wsctx pack .              # No crash with default config
wsctx pack . --quiet      # No crash (was the original crash case)
```

- [ ] **M2 Acceptance**

```bash
# Negation patterns
echo -e "*.log\n!important.log" > /tmp/test-repo/.gitignore
touch /tmp/test-repo/debug.log /tmp/test-repo/important.log
wsctx pack /tmp/test-repo  # important.log must be included, debug.log excluded

# Extension warning
wsctx pack . --include "**/*.java" 2>&1 | grep -i "WARNING\|no AST"
```

- [ ] **M3 Acceptance**

```bash
wsctx pack . --stdout --format xml | xmllint --noout -   # Valid XML
wsctx pack . --stdout --format json | python -m json.tool  # Valid JSON
wsctx pack . --stdout 2>/dev/null | wc -c               # Content → stdout; log → stderr
```

- [ ] **M4 Acceptance**

```bash
wsctx pack . --compress                                               # No crash
wsctx pack . --compress --stdout --format xml | grep "# ... implementation"  # Marker present
```

- [ ] **M6 Acceptance**

```bash
wsctx index .                    # Full index build
touch src/some_file.py           # Modify a file
wsctx index . --incremental      # Shows "1 files re-indexed"
wsctx query "test query"         # Works correctly (non-regression)
```

- [ ] **Full test suite**

```bash
pytest tests/ -v --tb=short
black . --check
ruff check .
mypy src/
```

- [ ] **Final commit if all green**

```bash
git tag v0.2.0-beta
```
