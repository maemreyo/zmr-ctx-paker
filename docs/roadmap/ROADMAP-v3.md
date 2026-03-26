# ROADMAP v3 — ws-ctx-engine

> Cập nhật: 2026-03-26
> Tổng hợp từ: ROADMAP-v2, agent-landscape-research-2026, deep-dive ws-ctx-engine
> Thay đổi chính so với v2: Bổ sung 5 "Agent-Primary Strengths" (M4.5, M3-ext, M2-ext), thêm M7-Perf/Rust, re-prioritize M4 co-critical với M2.

---

## Tóm tắt điều hành

Roadmap v2 có milestone ordering đúng và corrections kỹ thuật chính xác. Tuy nhiên, sau khi đối chiếu với **AI Agent landscape 2026** (Claude Code, Windsurf, Pulse và các agent nền tảng khác), phát hiện **5 điểm mù chiến lược** chưa được addressed — đây là những tính năng giúp ws-ctx-engine trở thành **engine tiêu chuẩn** cho agents, không chỉ là alternative cho Repomix.

Roadmap v3 tích hợp các điểm mù đó vào milestone plan mà **không phá vỡ thứ tự ưu tiên hiện tại**.

**Thay đổi lớn nhất:** M4 (Compression) được nâng lên **co-critical** ngang với M2 — cả hai là competitive differentiator cốt lõi và nên được implement song song nếu resource cho phép.

**Trạng thái hiện tại**: Alpha có crash bug mặc định.
**Mục tiêu**: Beta usable trong ~3–4 tuần (M1–M5). Agent-primary trong ~6–8 tuần (M1–M6).

---

## Định vị chiến lược

### Câu hỏi khác nhau giữa hai tools

- **Repomix**: _"Làm sao đóng gói repo thành output tốt nhất cho AI?"_ → Ưu tiên breadth, packaging ergonomics, UX đơn giản, compression dumb.
- **ws-ctx-engine**: _"Trong repo này, file nào thực sự đáng được đưa vào context dưới token budget hữu hạn, và làm cách nào để agent tiêu thụ context đó hiệu quả nhất?"_ → Ưu tiên selection quality, retrieval depth, **agent-native workflow**.

Unit of value khác nhau: Repomix tối ưu **artifact đầu ra**; ws-ctx-engine tối ưu **quyết định chọn nội dung nào + cách tổ chức nội dung đó cho agent**.

### Story cạnh tranh đúng (sau khi hoàn thành roadmap này)

> **ws-ctx-engine**: Intelligent context engine cho code agents.
>
> Retrieval-first với hybrid ranking (semantic + PageRank + Tree-sitter symbol + heuristics) — **chọn đúng phần codebase quan trọng nhất** trước, rồi **compress thông minh theo relevance**, **tổ chức output theo cognitive bias của model**, và **deduplicate session-level** để agent không lãng phí tokens.

```
Repomix workflow:      [codebase] → pack mọi thứ / filter thủ công → dumb compress → [AI context]
ws-ctx-engine:         [codebase] → retrieve intelligently → smart compress by relevance
                       → shuffle for model recall → deduplicate session tokens → [AI context]
```

Hai tools sẽ ở **hai lớp khác nhau** của cùng workflow — không phải thay thế trực tiếp.

### Điểm mạnh cốt lõi cần giữ nguyên

| Thế mạnh               | Chi tiết                                                             |
| ---------------------- | -------------------------------------------------------------------- |
| Hybrid ranking         | Semantic + PageRank + exact symbol + path/domain/test penalty        |
| Query classification   | Tự động nhận diện `symbol` vs `path-dominant` vs `semantic-dominant` |
| Token budget selection | Greedy knapsack dưới budget, reserve 20% cho metadata                |
| Agent security         | Path guard + RADE delimiters + read-only MCP + rate limiting         |
| Domain map             | keyword → directory/bounded context                                  |
| Review-oriented output | `REVIEW_CONTEXT.md`, reading order, dependency hints                 |

### 5 Agent-Primary Strengths bổ sung (mới trong v3)

Validated từ agent landscape research 2026. Đây là lý do agents như Claude Code, Windsurf, Pulse sẽ chọn ws-ctx-engine thay vì Repomix:

| Strength                        | Mô tả                                                                 | Milestone   |
| ------------------------------- | --------------------------------------------------------------------- | ----------- |
| Phase-Aware Context Selection   | `--mode [discovery\|edit\|test]` tự động điều chỉnh ranking weights   | M4.5 (mới) |
| Model-Specific Context Shuffling | Đặt high-rank files ở đầu + cuối XML để combat "Lost in the Middle"  | M4 (extend) |
| AI Rule Persistence             | `.cursorrules`, `AI_RULES.md`, `llm.txt` luôn được include (rank 10.0) | M2 (extend) |
| Semantic Deduplication          | Session-level hash cache; trả `[DEDUPLICATED]` thay vì repeat tokens | M4.5 (mới) |
| Output Format YAML / TOON       | `--format [xml\|yaml\|toon]` tiết kiệm 15–20% structural tokens      | M3 (extend) |

---

## Corrections từ Review v2 (giữ nguyên — chưa implement)

Bốn lỗi kỹ thuật trong roadmap v1 đã được document trong v2 và vẫn cần fix:

### C1 — Pathspec: Dùng `GitIgnoreSpec`, không phải `PathSpec.from_lines`

```python
# CÁCH ROADMAP V1 ĐỀ XUẤT — Partial gitignore compliance
spec = PathSpec.from_lines('gitignore', patterns)

# CÁCH ĐÚNG — Full git behavior replication
from pathspec import GitIgnoreSpec
spec = GitIgnoreSpec.from_lines(patterns)
# → Handle re-include inside excluded directory (!pattern)
# → Last-pattern-wins theo đúng cách Git làm
```

Confirmation từ pathspec v1.0 changelog (January 2026): `GitIgnoreSpecPattern` implements Git edge-cases; `PathSpec.from_lines('gitwildmatch')` hiện deprecated.

**Fix**: Dùng `GitIgnoreSpec.from_lines(patterns)` trong `chunker/base.py`. Không cần fallback về fnmatch — `pathspec` là pure Python, không fail.

### C2 — `__version__` phải dynamic, không hardcode

```python
# src/ws_ctx_engine/__init__.py — ĐÚNG (Python packaging standard 2025)
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ws-ctx-engine")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
```

### C3 — FAISS incremental update: Phải dùng `IndexIDMap2`

```python
# KHÔNG làm được:
flat_index = faiss.IndexFlatIP(dim)
flat_index.remove_ids(...)  # ❌ AttributeError

# PHẢI wrap:
base = faiss.IndexFlatIP(dim)
index = faiss.IndexIDMap2(base)  # IndexIDMap2 > IndexIDMap vì có thêm reconstruct()
index.add_with_ids(vectors.astype(np.float32), ids.astype(np.int64))
index.remove_ids(np.array(deleted_ids, dtype=np.int64))  # ✅
```

### C4 — Incremental indexing cần embedding cache, không chỉ chunk serialization

Không cache embedding theo content hash → incremental indexing chỉ tiết kiệm phần parsing (nhỏ), không tiết kiệm phần embedding (bottleneck chính với sentence-transformers trên CPU).

```python
# Persist:
np.save(cache_dir / "embeddings.npy", all_embeddings)
json.dump({"hash_to_idx": hash_to_idx_map}, open(cache_dir / "embedding_index.json"))
```

Không nhúng embedding vectors vào JSON (mỗi vector 384–768 float, rất nặng).

---

## Milestone Plan

Tổng estimate: **20–30 ngày làm việc (~5–6 tuần với buffer)**.

---

### M1 — Hotfix + Config Quick Cleanup

**Thời gian**: 1–2 ngày
**Priority**: 🔴 Prerequisite bắt buộc — không làm bất cứ gì khác trước khi xong M1.

**Scope**:

1. **Fix crash bug `_set_console_log_level`** — hàm được gọi tại `cli.py` nhưng chưa được định nghĩa, gây crash khi `--quiet` (default=True):

   ```python
   # cli.py — thêm trước @app.callback()
   def _set_console_log_level(quiet: bool) -> None:
       import logging
       level = logging.WARNING if quiet else logging.INFO
       logging.getLogger("ws_ctx_engine").setLevel(level)
   ```

2. **`__version__` via `importlib.metadata`** — dynamic version, không hardcode (xem Correction C2)

3. **Audit `--changed-files` flag** — README nhắc đến flag này nhưng CLI không expose đúng như documented. Phải quyết định: implement đúng **hoặc** remove khỏi README. Inconsistency không được để lại sau M1.

4. **Comment out aspirational config fields** (~4 giờ, không cần milestone riêng):
   - `logging.level`, `logging.file` → remove hoặc comment out khỏi `.ws-ctx-engine.yaml.example`
   - `advanced.pagerank_*`, `advanced.min/max_file_size`, `advanced.validate_roundtrip` → đánh dấu `# NOT YET IMPLEMENTED`
   - `max_workers`, `cache_embeddings`, `incremental_index` → đánh dấu `# PLANNED — not active`

5. **README sync** — thêm 6 commands còn thiếu, fix format options sai

**Files thay đổi**:

- `src/ws_ctx_engine/cli/cli.py` — fix crash; add `_set_console_log_level`
- `src/ws_ctx_engine/__init__.py` — importlib.metadata version
- `.ws-ctx-engine.yaml.example` — comment out aspirational fields
- `README.md` — sync commands, fix format options

**Acceptance criteria**:

```bash
wsctx --help              # Không crash
wsctx --version           # Hiển thị đúng version từ pyproject.toml
wsctx pack .              # Không crash với default config
wsctx pack . --quiet      # Không crash (đây là crash case gốc)
```

---

### M2 — Ignore Semantics + Language Honesty + AI Rule Persistence ⭐ [v3: extend]

**Thời gian**: 3–4 ngày _(tăng từ 2–3 ngày do thêm AI Rule Persistence)_
**Priority**: 🔴 High — developer trust + agent-primary foundation

**Scope**:

1. **Add `pathspec>=0.12`** vào `pyproject.toml` dependencies

2. **Migrate sang `GitIgnoreSpec`** trong `chunker/base.py` (xem Correction C1):

   ```python
   from pathspec import GitIgnoreSpec

   def build_ignore_spec(patterns: list[str]) -> GitIgnoreSpec:
       """Build gitignore spec that replicates actual Git behavior."""
       return GitIgnoreSpec.from_lines(patterns)

   def _should_include_file(path: str, spec: GitIgnoreSpec) -> bool:
       return not spec.match_file(path)

   def get_files_to_include(root: str, spec: GitIgnoreSpec) -> set[str]:
       return set(spec.match_tree_files(root, negate=True))
   ```

3. **Recursive `.gitignore` discovery** — walk subdirectories, merge patterns với path normalization:

   ```python
   def collect_gitignore_patterns(root: Path) -> list[str]:
       all_patterns = []
       for gitignore_path in root.rglob('.gitignore'):
           relative_dir = gitignore_path.parent.relative_to(root)
           with open(gitignore_path) as f:
               for line in f:
                   line = line.strip()
                   if line and not line.startswith('#'):
                       if str(relative_dir) != '.':
                           all_patterns.append(f"{relative_dir}/{line}")
                       else:
                           all_patterns.append(line)
       return all_patterns
   ```

4. **`INDEXED_EXTENSIONS` constant** trong `chunker/base.py` — danh sách các extension có AST parser thực tế

5. **Emit `[WARNING]`** khi file matched nhưng extension không trong `INDEXED_EXTENSIONS`

6. **[MỚI — v3] AI Rule Persistence** — auto-detect và boost các AI rule files:

   Agents ngày càng dựa vào `.cursorrules`, `AI_RULES.md`, `llm.txt`, `.claude/instructions.md` để nhận project context. Các files này phải **luôn được include** trong mọi pack, bất kể query là gì.

   ```python
   # ranking/ranker.py
   AI_RULE_FILES = {
       ".cursorrules",
       "AI_RULES.md",
       "llm.txt",
       "AGENTS.md",
       ".claude/instructions.md",
       ".github/copilot-instructions.md",
   }

   AI_RULE_BOOST = 10.0  # Override mọi relevance score khác

   def apply_ai_rule_boost(file_path: str, base_score: float) -> float:
       """Files khớp AI_RULE_FILES luôn được include với rank tối đa."""
       filename = Path(file_path).name
       relative = str(Path(file_path))
       if filename in AI_RULE_FILES or any(relative.endswith(r) for r in AI_RULE_FILES):
           return base_score + AI_RULE_BOOST
       return base_score
   ```

   Config support:
   ```yaml
   # .ws-ctx-engine.yaml
   ai_rules:
     auto_detect: true           # default: true
     extra_files: ["MY_RULES.md"]  # user-defined additions
     boost: 10.0
   ```

**Files thay đổi**:

- `pyproject.toml` — add `pathspec>=0.12`
- `src/ws_ctx_engine/chunker/base.py` — GitIgnoreSpec migration, INDEXED_EXTENSIONS, WARNING emit
- `src/ws_ctx_engine/chunker/tree_sitter.py` — minor, rely on base changes
- `src/ws_ctx_engine/ranking/ranker.py` — AI_RULE_FILES, apply_ai_rule_boost()
- `src/ws_ctx_engine/config/config.py` — ai_rules config block
- `README.md` — document AI rule persistence behavior

**Acceptance criteria**:

```bash
# Gitignore behavior
echo "*.log\n!important.log" > .gitignore
wsctx pack .                         # important.log phải được include
wsctx pack . --include "**/*.java"   # Warning: no AST parser available

# AI Rule Persistence
echo "# Project rules" > .cursorrules
wsctx pack . --query "fix button bug"  # .cursorrules phải có mặt trong output
wsctx pack . --query "update database"  # .cursorrules vẫn có mặt dù unrelated
```

---

### M3 — CLI UX + Output Polish + Output Formats ⭐ [v3: extend]

**Thời gian**: 4–5 ngày _(tăng từ 3–4 ngày do thêm YAML/TOON format)_
**Priority**: 🟠 High — UX parity + agent interoperability

**Scope**:

1. **Token count display** sau pack/query:

   ```
   ✓ Context packed (41,200 / 150,000 tokens)
   ```

   Thêm `total_tokens` vào NDJSON agent mode payload.

2. **`--stdout` flag** — output nội dung ra stdout, log vẫn ra stderr:
   - `--stdout` không có `--agent-mode` → XML/JSON/YAML to stdout
   - `--stdout` với `--agent-mode` → NDJSON to stdout
   - Hai modes không conflict

3. **`--copy` clipboard flag** — copy output vào clipboard

4. **JSON Schema + MCP response schema** → `docs/output-schema.md`

5. **Pipe examples** trong README:

   ```bash
   wsctx pack . --format xml --stdout | pbcopy
   wsctx query "auth flow" --format xml --stdout | claude
   ```

6. **[MỚI — v3] Output Format: YAML và TOON** — `--format [xml|yaml|toon]`

   Một số models 2026 đang move toward compressed encodings để tiết kiệm 15–20% structural tokens. Research từ Anthropic engineering (early 2026) cho thấy YAML packs giảm overhead đáng kể so với XML trên large context windows.

   ```yaml
   # YAML format output example
   context:
     query: "auth flow"
     token_count: 41200
     files:
       - path: src/auth/handler.py
         relevance: 0.92
         content: |
           def handle_login(request):
               ...
   ```

   **TOON format** (Token-Optimized Output Notation): Experimental — chỉ implement nếu có user demand signal. Nếu implement, cần đo token savings thực tế với `tiktoken` trước khi document.

   Implementation path:
   ```python
   # output/formatters.py
   class OutputFormat(Enum):
       XML = "xml"
       JSON = "json"
       YAML = "yaml"
       TOON = "toon"  # experimental

   def format_output(files: list[SelectedFile], fmt: OutputFormat) -> str:
       match fmt:
           case OutputFormat.XML:  return xml_packer.pack(files)
           case OutputFormat.JSON: return json_formatter.format(files)
           case OutputFormat.YAML: return yaml_formatter.format(files)
           case OutputFormat.TOON: return toon_formatter.format(files)  # experimental
   ```

   Rollout: XML (stable) → JSON (stable) → YAML (beta) → TOON (experimental, behind flag).

**Files thay đổi**:

- `src/ws_ctx_engine/cli/cli.py` — `--stdout`, `--copy`, token count display, `--format` extension
- `src/ws_ctx_engine/output/json_formatter.py` — JSON Schema conformance
- `src/ws_ctx_engine/output/yaml_formatter.py` — [NEW]
- `src/ws_ctx_engine/output/toon_formatter.py` — [NEW, experimental]
- `README.md` — pipe examples, stdout docs, format options
- `docs/output-schema.md` — [NEW] JSON Schema + YAML Schema + MCP response format spec

**Acceptance criteria**:

```bash
wsctx pack . --stdout --format xml | xmllint --noout -     # Valid XML
wsctx pack . --stdout --format json | python -m json.tool  # Valid JSON
wsctx pack . --stdout --format yaml | python -c "import yaml,sys; yaml.safe_load(sys.stdin)"  # Valid YAML
wsctx pack . --stdout 2>/dev/null | wc -c                  # Content → stdout; log → stderr
# Token count hiển thị trong terminal output (stderr)
# YAML output nhỏ hơn XML output (kiểm tra với wc -c)
```

---

### M4 — Compression Layer + Context Shuffling ⭐ [CO-CRITICAL — v3: co-priority với M2, extend]

**Thời gian**: 4–6 ngày _(tăng từ 3–5 ngày do thêm Context Shuffling)_
**Priority**: 🔴 Co-critical — killer differentiator so với Repomix.

> **v3 note**: M4 được nâng từ "High" lên "Co-critical" ngang với M2. Lý do: Repomix là "packing tool"; ws-ctx-engine phải là "intelligence tool". Compression thông minh theo relevance + Context Shuffling là hai features không có ở Repomix và là lý do chính để agents chọn ws-ctx-engine. Nếu resource cho phép, implement M2 và M4 **song song**.

**Lý do M4 là competitive differentiator:**

Repomix `--compress` là dumb compression — compress mọi file đồng đều. ws-ctx-engine làm **smart compression** theo relevance score:

```
High relevance files   → full content (LLM cần đọc kỹ)
Medium relevance files → signature-only (~70% savings)
Low relevance files    → signature + docstring only (~85% savings)
```

**Scope**:

1. **`--compress` flag** trong `pack` và `query` commands

2. **`output/compressor.py`** — file mới, dùng Tree-sitter đã có:

   ```python
   COMPRESSION_NODE_TYPES = {
       'python':     ['function_definition', 'class_definition', 'decorated_definition'],
       'typescript': ['function_declaration', 'class_declaration', 'interface_declaration'],
       'javascript': ['function_declaration', 'class_declaration'],
       'rust':       ['function_item', 'impl_item', 'struct_item'],
   }

   def compress_file_content(
       content: str,
       file_extension: str,
       preserve_docstrings: bool = True,
   ) -> str:
       """Extract signatures, replace function bodies with marker."""
       ...

   def apply_compression_to_selected_files(
       selected_files: list[SelectedFile],
       config: CompressionConfig,
   ) -> list[SelectedFile]:
       """Smart compression: apply after retrieval selection, based on relevance score."""
       for f in selected_files:
           if f.relevance_score >= config.full_content_threshold:
               continue  # High relevance: giữ full content
           f.content = compress_file_content(f.content, f.extension)
       return selected_files
   ```

3. **Marker format**: Dùng `# ... implementation` — consistent với Python convention

4. **Token reduction display**:

   ```
   ✓ Context packed with compression: 127,450 → 41,200 tokens (67% reduction)
   ```

5. **Language support** (tối thiểu): Python + TypeScript/JavaScript. Rust nếu parser đã có.

6. **[MỚI — v3] Model-Specific Context Shuffling** — combat "Lost in the Middle"

   Research cho thấy LLMs recall thông tin ở đầu và cuối context tốt hơn ở giữa ("Lost in the Middle" phenomenon — Liu et al., 2023, vẫn relevant với các models 2026). Packer phải tổ chức output để tối ưu recall:

   ```
   [TOP]    → File rank 1, 2, 3 (highest relevance — model nhớ tốt nhất)
   [MIDDLE] → File rank 4..N-3 (supporting context)
   [BOTTOM] → File rank N-2, N-1, N (2nd highest relevance — model vẫn nhớ tốt)
   ```

   Implementation:
   ```python
   # output/xml_packer.py
   def shuffle_for_model_recall(
       files: list[SelectedFile],
       top_k: int = 3,
       bottom_k: int = 3,
   ) -> list[SelectedFile]:
       """
       Reorder files so highest-ranked appear at top AND bottom.
       Supporting files go in the middle.
       Combat 'Lost in the Middle' phenomenon.
       """
       if len(files) <= top_k + bottom_k:
           return files  # Không đủ files để shuffle
       top = files[:top_k]
       bottom = files[-bottom_k:]
       middle = files[top_k:-bottom_k]
       return top + middle + bottom

   # Config option:
   # output.context_shuffle: true  (default: true khi --agent-mode)
   ```

   Flag: `--shuffle/--no-shuffle` (default: on trong agent mode, off trong stdout-only mode).

7. **`docs/compression.md`** — [NEW] compression guide + context shuffling rationale

**Files thay đổi**:

- `src/ws_ctx_engine/output/compressor.py` — [NEW]
- `src/ws_ctx_engine/output/xml_packer.py` — integrate compressor + shuffle_for_model_recall()
- `src/ws_ctx_engine/cli/cli.py` — `--compress`, `--shuffle/--no-shuffle` flags
- `README.md` — compression docs, context shuffling docs
- `docs/compression.md` — [NEW]

**Acceptance criteria**:

```bash
wsctx pack . --compress                                              # Không crash
wsctx pack . --compress --format xml | grep "# ... implementation"  # Marker có mặt
# Token count với --compress thấp hơn không có --compress (40%+ reduction target)
wsctx pack . --compress --stdout | xmllint --noout -                 # Valid XML
# Agent mode: verify highest-rank file ở line 1 VÀ gần cuối output
wsctx pack . --agent-mode --query "auth" | python -c "import sys; content=sys.stdin.read(); print('shuffle OK')"
```

---

### M4.5 — Agent Intelligence Layer ⭐ [MỚI — v3]

**Thời gian**: 3–4 ngày
**Priority**: 🟠 High — agent-primary adoption driver

> Đây là milestone hoàn toàn mới trong v3, không có trong v2. Gộp hai agent-specific features: Phase-Aware Context Selection và Semantic Deduplication.

#### Feature 1: Phase-Aware Context Selection

Agents làm việc theo chu kỳ: **Discovery → Planning → Implementation → Verification**. Mỗi phase cần loại context khác nhau. Hiện tại ws-ctx-engine trả cùng một loại context bất kể agent đang ở phase nào.

```
Discovery Mode:       Directory trees + high-level signatures (low token density)
Implementation Mode:  Verbatim code + related type defs (high token density)
Test/Verification:    Test files + mocked deps + assertion patterns
```

Implementation:

```python
# ranking/phase_ranker.py
from enum import Enum

class AgentPhase(Enum):
    DISCOVERY       = "discovery"
    EDIT            = "edit"
    TEST            = "test"

PHASE_WEIGHT_OVERRIDES = {
    AgentPhase.DISCOVERY: {
        "semantic_weight":   0.2,
        "symbol_weight":     0.1,
        "signature_only":    True,   # Force compression cho mọi file
        "include_tree":      True,   # Luôn include directory tree
        "max_token_density": 0.3,    # 30% budget cho code, 70% cho structure
    },
    AgentPhase.EDIT: {
        "semantic_weight":   0.5,
        "symbol_weight":     0.4,
        "signature_only":    False,
        "include_tree":      False,
        "max_token_density": 1.0,    # Full token budget cho verbatim code
    },
    AgentPhase.TEST: {
        "semantic_weight":   0.3,
        "symbol_weight":     0.3,
        "test_file_boost":   2.0,    # Boost test files
        "mock_file_boost":   1.5,
        "include_tree":      False,
        "max_token_density": 0.8,
    },
}

def apply_phase_weights(ranker_config: RankerConfig, phase: AgentPhase) -> RankerConfig:
    """Override ranking weights based on agent phase."""
    overrides = PHASE_WEIGHT_OVERRIDES[phase]
    return dataclasses.replace(ranker_config, **overrides)
```

CLI flag: `--mode [discovery|edit|test]`

```bash
wsctx query "what does this codebase do" --mode discovery   # Low-density, tree-first
wsctx query "fix the auth bug" --mode edit                  # High-density, verbatim
wsctx query "write tests for login" --mode test             # Test-file-boosted
```

#### Feature 2: Semantic Deduplication (Session-Level)

Agents hay gọi context tool nhiều lần trong một session, dẫn đến cùng files được pack lại nhiều lần — lãng phí tokens và tăng cost cho user.

Implementation: Local session cache với content hash. Nếu file đã được gửi trong cùng session, trả marker thay vì full content.

```python
# session/dedup_cache.py
import hashlib
import json
from pathlib import Path

class SessionDeduplicationCache:
    """
    Track files sent trong một agent session.
    Persist dưới dạng .ws-ctx-engine-session.json trong project root.
    """
    def __init__(self, session_id: str, cache_dir: Path):
        self.session_id = session_id
        self.cache_file = cache_dir / f".ws-ctx-engine-session-{session_id}.json"
        self.seen_hashes: dict[str, str] = self._load()

    def check_and_mark(self, file_path: str, content: str) -> tuple[bool, str]:
        """
        Returns (is_duplicate, content_or_marker).
        Nếu đã seen: trả (True, '[DEDUPLICATED: file_path — already sent in this session]')
        Nếu mới: mark as seen, trả (False, original_content)
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in self.seen_hashes:
            marker = f"[DEDUPLICATED: {file_path} — already sent in this session. Hash: {content_hash[:8]}]"
            return True, marker
        self.seen_hashes[content_hash] = file_path
        self._save()
        return False, content

    def _load(self) -> dict:
        try:
            return json.loads(self.cache_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self):
        self.cache_file.write_text(json.dumps(self.seen_hashes))


# CLI flags:
# --session-id STR      : Tên session (default: "default")
# --no-dedup            : Tắt deduplication
# wsctx session clear   : Xóa session cache
```

Token reporting với dedup:
```
✓ Context packed (41,200 tokens) — 3 files deduplicated (saved ~12,400 tokens)
```

**Files thay đổi (M4.5)**:

- `src/ws_ctx_engine/ranking/phase_ranker.py` — [NEW] phase weight overrides
- `src/ws_ctx_engine/session/dedup_cache.py` — [NEW] session-level hash cache
- `src/ws_ctx_engine/cli/cli.py` — `--mode` flag, `--session-id`, `--no-dedup`, `wsctx session clear`
- `src/ws_ctx_engine/workflow/pack_workflow.py` — integrate phase_ranker + dedup_cache
- `README.md` — phase-aware docs, session dedup docs
- `docs/agent-workflows.md` — [NEW] guide cho agent integration

**Acceptance criteria**:

```bash
# Phase-Aware
wsctx pack . --query "explore codebase" --mode discovery | wc -c   # < output của --mode edit
wsctx pack . --query "fix auth bug" --mode edit | grep "# ... implementation"  # Ít marker hơn discovery

# Semantic Deduplication
wsctx pack . --query "auth"  # First call: full content
wsctx pack . --query "auth" --session-id my-session  # Second call: [DEDUPLICATED] markers
wsctx session clear           # Xóa session cache
wsctx pack . --query "auth" --session-id my-session  # Full content lại sau clear
```

---

### M5 — Config Cleanup (Residual)

**Thời gian**: 0.5–1 ngày
**Priority**: 🟡 Medium — polish

_Bulk của cleanup đã được gộp vào M1. Đây là những gì còn lại._

**Scope**:

- Verify `advanced.*` fields không được parse/dùng — nếu đang bị ignored silently, document điều đó
- Update docstrings trong `config/config.py`
- Remove hoặc đánh dấu experimental các fields còn lại trong config class
- Verify ai_rules config block (từ M2) được document đầy đủ

**Files thay đổi**:

- `src/ws_ctx_engine/config/config.py` — docstrings, remove residual aspirational fields

---

### M6 — Incremental Indexing

**Thời gian**: 5–7 ngày _(estimate từ v2 vẫn đúng)_
**Priority**: 🟡 Medium — performance (repos > 5k files)

**Scope**:

1. **Migrate FAISS sang `IndexIDMap2`** (xem Correction C3):

   ```python
   def create_faiss_index(dim: int) -> faiss.IndexIDMap2:
       base = faiss.IndexFlatIP(dim)
       return faiss.IndexIDMap2(base)

   def update_chunks(
       index: faiss.IndexIDMap2,
       old_ids: list[int],
       new_embeddings: np.ndarray,
       new_ids: np.ndarray,
   ):
       if old_ids:
           index.remove_ids(np.array(old_ids, dtype=np.int64))
       index.add_with_ids(new_embeddings.astype(np.float32), new_ids.astype(np.int64))
   ```

2. **Embedding cache** (xem Correction C4) — content hash → vector, lưu ra `.npy` file:

   ```python
   np.save(cache_dir / "embeddings.npy", all_embeddings)
   json.dump({"hash_to_idx": hash_to_idx_map}, open(cache_dir / "embedding_index.json"))
   ```

3. **Hash diff detection per file** trong `workflow/indexer.py`

4. **Partial reparse + selective re-embed**:

   ```python
   def incremental_update(index, changed_paths, deleted_paths, new_chunks, embedding_cache):
       ids_to_remove = get_chunk_ids_for_paths(deleted_paths + changed_paths)
       if ids_to_remove:
           index.remove_ids(np.array(ids_to_remove, dtype=np.int64))
       for chunk in new_chunks:
           content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
           if content_hash in embedding_cache:
               vec = embedding_cache[content_hash]
           else:
               vec = embed(chunk.content)
               embedding_cache[content_hash] = vec
   ```

5. **Chunk serialization** — `to_dict()`/`from_dict()` trong `models/models.py`

6. **LEANN compatibility verification** — nếu LEANN không support incremental tương đương FAISS, M6 implement cho FAISS backend trước, port sang LEANN sau.

**Files thay đổi**:

- `src/ws_ctx_engine/vector_index/faiss_index.py` — IndexIDMap2 migration
- `src/ws_ctx_engine/workflow/indexer.py` — incremental reindex logic, hash diff detection
- `src/ws_ctx_engine/models/models.py` — chunk serialization, embedding cache schema
- `src/ws_ctx_engine/cli/cli.py` — `--incremental` flag

**Acceptance criteria**:

```bash
wsctx index .                    # Full index build
touch src/modified_file.py
wsctx index . --incremental      # Chỉ file đó được re-embedded (verify qua log)
rm src/deleted_file.py
wsctx index . --incremental      # File đó biến mất khỏi search results
wsctx query "test query"         # Query vẫn hoạt động đúng (non-regression)
```

---

### M7 — Performance / Rust Core ⭐ [MỚI — v3]

**Thời gian**: 7–10 ngày
**Priority**: 🟡 Medium-High — prerequisite cho enterprise adoption (repos > 10k files)

> Milestone mới hoàn toàn trong v3. Validated từ agent landscape research: với repos lớn (> 10k files), Python engine hiện tại quá chậm cho "human-in-the-loop" speeds — agents timeout hoặc degrade UX đáng kể.

**Vấn đề cụ thể:**

| Operation          | Python (current) | Target     | Rust speedup estimate |
| ------------------ | ---------------- | ---------- | --------------------- |
| File walk (10k)    | ~2–4s            | < 200ms    | 10–20x                |
| Gitignore matching | ~500ms           | < 50ms     | 8–12x                 |
| Chunk hashing      | ~300ms           | < 30ms     | 8–10x                 |
| Token counting     | ~1s              | < 100ms    | 8–12x                 |

**Approach**: PyO3-based Rust extension cho hot paths — không rewrite toàn bộ engine:

```
ws_ctx_engine/
└── _rust/                        # Rust extension module (PyO3)
    ├── src/
    │   ├── lib.rs                # PyO3 module entrypoint
    │   ├── walker.rs             # Fast parallel file walker
    │   ├── hasher.rs             # xxHash/Blake3 content hashing
    │   └── token_counter.rs     # tiktoken-rs port
    └── Cargo.toml
```

```rust
// src/walker.rs — parallel file walker với gitignore support
use pyo3::prelude::*;
use ignore::WalkBuilder;

#[pyfunction]
fn walk_files(root: &str, ignore_patterns: Vec<String>) -> PyResult<Vec<String>> {
    let walker = WalkBuilder::new(root)
        .hidden(true)
        .git_ignore(true)
        .build_parallel();
    // ...
}
```

**Rollout strategy**: Rust extension là optional — Python fallback nếu build fail:

```python
# chunker/base.py
try:
    from ws_ctx_engine._rust import walk_files, count_tokens, hash_content
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Python fallback implementations
```

**Scope (tối thiểu viable):**
- File walker với parallel traversal
- Content hasher (Blake3/xxHash — 10x faster than hashlib.sha256)
- Token counter (tiktoken-rs)
- CI/CD: manylinux wheels + macOS universal2 + Windows
- Benchmark suite: `scripts/benchmark.py` để đo regression

**Files thay đổi**:

- `_rust/` — [NEW] Rust extension
- `pyproject.toml` — maturin build backend, optional Rust feature flag
- `src/ws_ctx_engine/chunker/base.py` — try/except Rust import với Python fallback
- `src/ws_ctx_engine/utils/token_counter.py` — Rust-backed nếu available
- `.github/workflows/build-rust.yml` — [NEW] CI cho manylinux + macOS + Windows builds
- `docs/performance.md` — [NEW] benchmark guide

**Acceptance criteria**:

```bash
# Performance regression tests
python scripts/benchmark.py --repo /path/to/large-repo  # > 10k files
# File walk: < 500ms (vs 2–4s Python)
# Full pack: < 2s (vs 8–15s Python) cho repo 10k files

# Correctness (non-regression)
wsctx pack . --query "auth"  # Output giống hệt Python implementation
wsctx index .                # Index build thành công
python -c "from ws_ctx_engine._rust import walk_files; print('Rust OK')"
```

---

### Future — Advanced RAG (Chunk-Level Selection)

**Thời gian**: TBD — Long-term item
**Priority**: 🟢 Low — post-stabilization

Validated trong agent research: Moving beyond file-level selection sang **chunk-level selection** với cross-file symbol tracking. Đây là M6 trong agent research taxonomy.

```
Current:  [query] → [file selection] → [file-level context]
Future:   [query] → [chunk selection] → [cross-file symbol graph] → [chunk-level context]
```

Yêu cầu: Tree-sitter symbol graph hoàn chỉnh, cross-file reference tracking, chunk-level FAISS index riêng biệt với file-level index.

---

### Future — Remote Repository Support

**Thời gian**: TBD
**Priority**: 🟢 Low — long-term

```bash
wsctx pack https://github.com/user/repo
wsctx pack github:user/repo --branch main
```

Cần có: trust/no-trust config rõ ràng, sandbox cho remote content.

---

## Tổng hợp Timeline

| Milestone  | Nội dung                                      | Estimate   | Priority                             |
| ---------- | --------------------------------------------- | ---------- | ------------------------------------ |
| **M1**     | Hotfix + Config Quick Cleanup                 | 1–2 ngày   | 🔴 Critical — prerequisite           |
| **M2**     | Ignore Semantics + Language Honesty + AI Rules | 3–4 ngày   | 🔴 High — developer trust + agent   |
| **M3**     | CLI UX + Output Polish + YAML/TOON            | 4–5 ngày   | 🟠 High — UX parity + interop       |
| **M4**     | Compression + Context Shuffling               | 4–6 ngày   | 🔴 Co-critical — killer differentiator |
| **M4.5**   | Agent Intelligence (Phase-Aware + Dedup)      | 3–4 ngày   | 🟠 High — agent-primary adoption    |
| **M5**     | Config Cleanup (residual)                     | 0.5–1 ngày | 🟡 Medium — polish                  |
| **M6**     | Incremental Indexing                          | 5–7 ngày   | 🟡 Medium — performance             |
| **M7**     | Performance / Rust Core                       | 7–10 ngày  | 🟡 Medium-High — enterprise scale   |
| **Future** | Advanced RAG (Chunk-Level)                    | TBD        | 🟢 Low — post-stabilization         |
| **Future** | Remote Repository Support                     | TBD        | 🟢 Low — long-term                  |

**Tổng**: 27–39 ngày làm việc (~6–8 tuần với buffer)

**Recommended parallel tracks** (nếu có 2 người):
- Track A: M1 → M2 → M4.5 → M6
- Track B: M3 → M4 → M5 → M7

---

## Directory Structure (Sau tất cả milestones)

```
src/ws_ctx_engine/
├── cli/
│   └── cli.py                    # [M1] crash fix; [M3] --stdout, --copy, --format; [M4] --compress, --shuffle; [M4.5] --mode, --session-id; [M6] --incremental
├── chunker/
│   ├── base.py                   # [M2] GitIgnoreSpec, INDEXED_EXTENSIONS, WARNING
│   └── tree_sitter.py            # [M2] minor; [M4] reuse cho compression
├── config/
│   └── config.py                 # [M1/M5] aspirational fields; [M2] ai_rules block
├── output/
│   ├── json_formatter.py         # [M3] JSON Schema conformance
│   ├── xml_packer.py             # [M3] --stdout; [M4] compressor + shuffle_for_model_recall()
│   ├── yaml_formatter.py         # [M3-NEW]
│   ├── toon_formatter.py         # [M3-NEW, experimental]
│   └── compressor.py             # [M4-NEW] Tree-sitter signature extraction
├── ranking/
│   ├── ranker.py                 # [M2] AI_RULE_FILES, apply_ai_rule_boost()
│   └── phase_ranker.py           # [M4.5-NEW] phase weight overrides
├── session/
│   └── dedup_cache.py            # [M4.5-NEW] session-level hash dedup
├── vector_index/
│   └── faiss_index.py            # [M6] IndexIDMap2 migration
├── workflow/
│   ├── indexer.py                # [M6] incremental reindex + hash diff
│   └── pack_workflow.py          # [M4.5] integrate phase_ranker + dedup_cache
├── models/
│   └── models.py                 # [M6] chunk serialization; embedding cache schema
└── __init__.py                   # [M1] importlib.metadata version

_rust/                            # [M7-NEW] PyO3 Rust extension
├── src/
│   ├── lib.rs
│   ├── walker.rs
│   ├── hasher.rs
│   └── token_counter.rs
└── Cargo.toml

pyproject.toml                    # [M2] pathspec>=0.12; [M7] maturin build backend
README.md                         # [M1/M3/M4/M4.5] sync
.ws-ctx-engine.yaml.example       # [M1/M2/M5] aspirational fields, ai_rules

docs/
├── output-schema.md              # [M3-NEW] JSON + YAML Schema + MCP spec
├── compression.md                # [M4-NEW] compression guide + context shuffling
├── agent-workflows.md            # [M4.5-NEW] phase-aware + session dedup guide
└── performance.md                # [M7-NEW] benchmark guide
```

---

## Checklist Implementation

```
M1 — Hotfix (1–2 ngày):
[ ] Define _set_console_log_level trong cli.py
[ ] Replace hardcoded __version__ với importlib.metadata pattern
[ ] Add PackageNotFoundError guard
[ ] Audit --changed-files: implement hoặc remove khỏi README
[ ] Comment out aspirational YAML fields với note rõ ràng
[ ] Sync README: thêm 6 missing commands, fix format options
[ ] Test: wsctx pack . --quiet không crash

M2 — Ignore Semantics + AI Rules (3–4 ngày):
[ ] Add pathspec>=0.12 vào pyproject.toml
[ ] Import GitIgnoreSpec (KHÔNG phải PathSpec)
[ ] Implement build_ignore_spec() với GitIgnoreSpec.from_lines()
[ ] Implement recursive .gitignore collection với path normalization
[ ] Add INDEXED_EXTENSIONS constant
[ ] Add WARNING log cho unindexable file extensions
[ ] Test: !negation patterns work; **/*.py đúng Git behavior
[ ] [v3] Add AI_RULE_FILES set và apply_ai_rule_boost() trong ranker.py
[ ] [v3] Add ai_rules config block trong config.py
[ ] [v3] Test: .cursorrules luôn có mặt trong output bất kể query

M3 — CLI UX + Formats (4–5 ngày):
[ ] Token count display sau pack/query
[ ] --stdout flag: log → stderr
[ ] --copy clipboard flag
[ ] JSON Schema + MCP response schema: docs/output-schema.md
[ ] Pipe examples trong README
[ ] [v3] yaml_formatter.py: Valid YAML output
[ ] [v3] toon_formatter.py: Experimental TOON output (behind --format toon flag)
[ ] [v3] Measure YAML vs XML token savings với tiktoken
[ ] [v3] docs/output-schema.md: bổ sung YAML schema

M4 — Compression + Context Shuffling (4–6 ngày):
[ ] Create output/compressor.py với Tree-sitter
[ ] --compress flag trong pack + query commands
[ ] COMPRESSION_NODE_TYPES dict cho Python + TS/JS minimum
[ ] "# ... implementation" marker format
[ ] apply_compression_to_selected_files() với relevance threshold
[ ] Token reduction display
[ ] docs/compression.md
[ ] [v3] shuffle_for_model_recall() trong xml_packer.py
[ ] [v3] --shuffle/--no-shuffle flag
[ ] [v3] Test: highest-rank file ở top VÀ bottom của XML output
[ ] [v3] docs/compression.md: thêm context shuffling rationale

M4.5 — Agent Intelligence Layer (3–4 ngày):
[ ] [v3] phase_ranker.py: PHASE_WEIGHT_OVERRIDES + apply_phase_weights()
[ ] [v3] --mode [discovery|edit|test] flag trong cli.py
[ ] [v3] Test: discovery mode → smaller output + more signatures
[ ] [v3] Test: edit mode → verbatim code priority
[ ] [v3] dedup_cache.py: SessionDeduplicationCache với content hash
[ ] [v3] --session-id flag trong cli.py
[ ] [v3] --no-dedup flag
[ ] [v3] wsctx session clear command
[ ] [v3] Test: second pack với same session → [DEDUPLICATED] markers
[ ] [v3] Test: wsctx session clear → full content lại
[ ] [v3] docs/agent-workflows.md: phase-aware + dedup guide

M5 — Config Cleanup (0.5–1 ngày):
[ ] Verify remaining aspirational config fields trong config.py
[ ] Update config.py docstrings
[ ] Verify ai_rules block từ M2 documented đầy đủ

M6 — Incremental Indexing (5–7 ngày):
[ ] Migrate FAISS index → IndexIDMap2
[ ] Add embedding cache (.npy + hash_to_idx JSON)
[ ] Hash diff detection trong indexer.py
[ ] Chunk serialization to_dict()/from_dict() trong models.py
[ ] LEANN compatibility check + document nếu cần separate path
[ ] Incremental reindex logic với update_chunks()
[ ] --incremental flag trong wsctx index
[ ] Test: modify 1 file → only 1 file re-embedded (verify via log)
[ ] Test: delete 1 file → file biến mất khỏi search results
[ ] Test: full rebuild vẫn hoạt động (non-regression)

M7 — Performance / Rust Core (7–10 ngày):
[ ] [v3] Setup _rust/ với PyO3 + maturin
[ ] [v3] walker.rs: parallel file walker với gitignore
[ ] [v3] hasher.rs: Blake3/xxHash content hashing
[ ] [v3] token_counter.rs: tiktoken-rs port
[ ] [v3] Python fallback khi Rust unavailable (try/except ImportError)
[ ] [v3] CI: manylinux wheels + macOS universal2 + Windows build
[ ] [v3] Benchmark suite: scripts/benchmark.py
[ ] [v3] Test: > 10k file repo, file walk < 500ms
[ ] [v3] Test: correctness non-regression vs Python implementation
[ ] [v3] docs/performance.md: benchmark guide
```

---

## Tài liệu tham khảo kỹ thuật

| Resource                                                          | Relevance                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------ |
| `pathspec` PyPI — `GitIgnoreSpec` API                             | M2: correct class to use                               |
| pathspec CHANGES.rst — v1.0 breaking changes                      | M2: `GitIgnoreSpec` vs `PathSpec` difference           |
| FAISS Special Operations wiki                                     | M6: `IndexIDMap2`, `remove_ids` support                |
| Repomix compression docs (repomix.com/guide/code-compress)        | M4: ~70% token reduction benchmark, marker format      |
| `importlib.metadata` Python docs                                  | M1: single-source version pattern                      |
| Adam Johnson: importlib.metadata (July 2025)                      | M1: community 2025 consensus                           |
| Liu et al. 2023: "Lost in the Middle" (arXiv:2307.03172)         | M4: context shuffling rationale                        |
| PyO3 User Guide — maturin build system                            | M7: Rust extension setup                               |
| `ignore` crate (Rust) — BurntSushi                                | M7: parallel file walking với gitignore support        |
| tiktoken-rs (PyO3-based)                                          | M7: fast token counting từ Rust                        |
| `.cursorrules` community convention — cursor.sh                   | M2: AI rule file naming convention                     |
| `llm.txt` spec — llmstxt.org                                      | M2: standardized AI context file format                |
| Agent workflow research: Claude Code, Windsurf, Pulse (2026)      | M4.5: phase-aware context validation                   |
