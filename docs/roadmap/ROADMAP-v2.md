# ROADMAP v2 — ws-ctx-engine

> Cập nhật: 2026-03-26
> Tổng hợp từ: comparison report (ws-ctx-engine vs Repomix), roadmap-v1, review-1, review-2

---

## Tóm tắt điều hành

Roadmap v1 là stabilization plan đúng hướng — đúng thứ tự ưu tiên, đúng milestone ordering — nhưng có **4 lỗi kỹ thuật cụ thể** cần sửa và **1 milestone chiến lược bị bỏ sót** làm giảm đáng kể giá trị cạnh tranh.

Roadmap v2 này tổng hợp toàn bộ corrections, bổ sung milestone mới, và đặt nền cho story cạnh tranh dài hạn.

**Trạng thái hiện tại**: Alpha có crash bug mặc định.
**Mục tiêu**: Beta usable trong ~3–4 tuần.

---

## Định vị chiến lược

### Câu hỏi khác nhau giữa hai tools

- **Repomix**: _"Làm sao đóng gói repo thành output tốt nhất cho AI?"_ → Ưu tiên breadth, packaging ergonomics, UX đơn giản, compression dumb.
- **ws-ctx-engine**: _"Trong repo này, file nào thực sự đáng được đưa vào context dưới token budget hữu hạn?"_ → Ưu tiên selection quality, retrieval depth, agent-native workflow.

Unit of value khác nhau: Repomix tối ưu **artifact đầu ra**; ws-ctx-engine tối ưu **quyết định chọn nội dung nào nên vào artifact**.

### Story cạnh tranh đúng (sau khi hoàn thành roadmap này)

> **ws-ctx-engine**: Intelligent context engine cho code agents.
>
> Retrieval-first với hybrid ranking (semantic + PageRank + heuristics) — **chọn đúng phần codebase quan trọng nhất** trước, rồi **compress thông minh theo relevance** để fit vào token budget.

```
Repomix workflow:   [codebase] → pack mọi thứ / filter thủ công → dumb compress → [AI context]
ws-ctx-engine:      [codebase] → retrieve intelligently → smart compress by relevance → [AI context]
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

---

## Corrections từ Review (trước khi implement)

Bốn lỗi kỹ thuật trong roadmap v1 cần được sửa trong các milestone tương ứng:

### C1 — Pathspec: Dùng `GitIgnoreSpec`, không phải `PathSpec.from_lines`

Roadmap v1 đề xuất `PathSpec.from_lines('gitignore', patterns)`. Đây **không phải** cách chính xác nhất.

`pathspec` v1.0 có hai implementation khác nhau:

```python
# CÁCH ROADMAP V1 ĐỀ XUẤT — Partial gitignore compliance
spec = PathSpec.from_lines('gitignore', patterns)
# → Follows gitignore DOCUMENTATION, nhưng không handle edge cases Git thực tế làm khác docs
# → "foo/*" sẽ không match files trong subdirectories

# CÁCH ĐÚNG — Full git behavior replication
from pathspec import GitIgnoreSpec
spec = GitIgnoreSpec.from_lines(patterns)
# → Replicates Git's ACTUAL BEHAVIOR (bao gồm edge cases)
# → Handle re-include inside excluded directory (!pattern)
# → Last-pattern-wins theo đúng cách Git làm
```

Confirmation từ pathspec v1.0 changelog (January 2026): `"GitIgnoreSpecPattern implements Git's edge-cases. The form PathSpec.from_lines('gitwildmatch') is now deprecated because it does not fully match the behavior of the gitignore docs or Git itself."`

**Fix**: Dùng `GitIgnoreSpec.from_lines(patterns)` trong `chunker/base.py`. Requirement vẫn là `pathspec>=0.12` — không thay đổi.

**Note**: Không cần fallback về fnmatch — `pathspec` là pure Python, không có C extension, install trên bất kỳ platform nào mà không thể fail. Fallback chỉ tăng complexity vô ích.

### C2 — `__version__` phải dynamic, không hardcode

Roadmap v1 nói "sync `__version__` về `0.1.10`" — đây là hardcode, sẽ drift lại ngay sau release tiếp theo.

```python
# src/ws_ctx_engine/__init__.py — ĐÚNG (Python packaging standard 2025)
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ws-ctx-engine")
except PackageNotFoundError:
    # Chưa install (e.g., chạy trực tiếp từ source)
    __version__ = "0.0.0+dev"
```

PEP 396 (đặt `__version__` thủ công) đã bị rejected. Community 2025 consensus: dùng `importlib.metadata`.

### C3 — FAISS incremental update: Phải dùng `IndexIDMap2`

Roadmap v1 nói "vector index cần support `remove(deleted_paths)`" nhưng không cung cấp implementation path.

`IndexFlatIP` / `IndexFlatL2` **không có `remove_ids()` method**. Phải wrap trong `IndexIDMap2`:

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

Dùng `IndexIDMap2` (không phải `IndexIDMap`) vì thêm khả năng `reconstruct()` — hữu ích cho debug và verify embedding cache consistency.

### C4 — Incremental indexing cần embedding cache, không chỉ chunk serialization

Roadmap v1 chỉ nói "serialize chunks" nhưng bỏ sót embedding cache — đây thực ra là bottleneck chính.

Nếu không cache embedding theo content hash, incremental indexing chỉ tiết kiệm phần parsing (nhỏ), không tiết kiệm phần embedding (đây là bottleneck chính với sentence-transformers trên CPU).

Design đề xuất: lưu embeddings ra `.npy` file riêng với lookup dict:

```python
# Persist:
np.save(cache_dir / "embeddings.npy", all_embeddings)
json.dump({"hash_to_idx": hash_to_idx_map}, open(cache_dir / "embedding_index.json"))
```

Không nhúng embedding vectors vào JSON (mỗi vector 384–768 float, sẽ rất nặng).

---

## Milestone Plan

Tổng estimate: **15–22 ngày làm việc (~3–4 tuần với buffer)**.

---

### M1 — Hotfix + Config Quick Cleanup

**Thời gian**: 1–2 ngày
**Priority**: Prerequisite bắt buộc — không làm bất cứ gì khác trước khi xong M1.

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

### M2 — Ignore Semantics + Language Honesty

**Thời gian**: 2–3 ngày

**Scope**:

1. **Add `pathspec>=0.12`** vào `pyproject.toml` dependencies

2. **Migrate sang `GitIgnoreSpec`** trong `chunker/base.py` (xem Correction C1):

   ```python
   from pathspec import GitIgnoreSpec

   def build_ignore_spec(patterns: list[str]) -> GitIgnoreSpec:
       """Build gitignore spec that replicates actual Git behavior."""
       return GitIgnoreSpec.from_lines(patterns)

   def _should_include_file(path: str, spec: GitIgnoreSpec) -> bool:
       """Return True if file should be included (not ignored)."""
       return not spec.match_file(path)

   # Hoặc dùng batch operation:
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

5. **Emit `[WARNING]`** khi file matched nhưng extension không trong `INDEXED_EXTENSIONS`:
   > Không cần thay đổi default `include_patterns` để tránh breaking change — chỉ warn.

**Files thay đổi**:

- `pyproject.toml` — add `pathspec>=0.12`
- `src/ws_ctx_engine/chunker/base.py` — GitIgnoreSpec migration, INDEXED_EXTENSIONS, WARNING emit
- `src/ws_ctx_engine/chunker/tree_sitter.py` — minor, rely on base changes

**Acceptance criteria**:

```bash
# Tạo test repo:
echo "*.log\n!important.log" > .gitignore
wsctx pack .                         # important.log phải được include
wsctx pack . --include "**/*.java"   # Warning: no AST parser available
# Kiểm tra subdirectory .gitignore được respect
```

---

### M3 — CLI UX + Output Polish

**Thời gian**: 3–4 ngày

**Scope**:

1. **Token count display** sau pack/query:

   ```
   ✓ Context packed (41,200 / 150,000 tokens)
   ```

   Thêm `total_tokens` vào NDJSON agent mode payload.

2. **`--stdout` flag** — output nội dung ra stdout, log vẫn ra stderr:
   - `--stdout` không có `--agent-mode` → XML/JSON to stdout
   - `--stdout` với `--agent-mode` → NDJSON to stdout
   - Hai modes không conflict — restriction cũ trong roadmap v1 quá chặt

3. **`--copy` clipboard flag** — copy output vào clipboard

4. **JSON Schema + MCP response schema** → `docs/output-schema.md`

5. **Pipe examples** trong README:

   ```bash
   wsctx pack . --format xml --stdout | pbcopy
   wsctx query "auth flow" --format xml --stdout | claude
   ```

**Files thay đổi**:

- `src/ws_ctx_engine/cli/cli.py` — `--stdout`, `--copy`, token count display
- `src/ws_ctx_engine/output/json_formatter.py` — JSON Schema conformance
- `README.md` — pipe examples, stdout docs
- `docs/output-schema.md` — [NEW] JSON Schema + MCP response format spec

**Acceptance criteria**:

```bash
wsctx pack . --stdout --format xml | xmllint --noout -   # Valid XML
wsctx pack . --stdout --format json | python -m json.tool  # Valid JSON
wsctx pack . --stdout 2>/dev/null | wc -c  # Content → stdout; log → stderr
# Token count hiển thị trong terminal output (stderr)
```

---

### M4 — Compression Layer ⭐ [MỚI — Gap chiến lược]

**Thời gian**: 3–5 ngày
**Priority**: Cao — ROI cao nhất trong các milestones còn lại.

**Lý do thêm milestone này:**

Repomix `--compress` là production feature (~70% token reduction), được document chính thức, và là điểm user nhắc đến nhiều nhất khi so sánh tools. ws-ctx-engine đã có Tree-sitter foundation trong `chunker/tree_sitter.py` — đây là **foundation đã sẵn sàng**.

**Lợi thế khác biệt so với Repomix:**

Repomix compression là _dumb compression_ — compress mọi file được include bằng nhau. ws-ctx-engine có thể làm **smart compression** dựa trên relevance score:

```
High relevance files   → full content (LLM cần đọc kỹ, không compress)
Medium relevance files → signature-only (~70% savings)
Low relevance files    → signature + docstring only (~85% savings)
```

Đây là story mạnh hơn Repomix — không chỉ "compress như Repomix" mà là "compress thông minh hơn dựa trên relevance".

**Scope**:

1. **`--compress` flag** trong `pack` và `query` commands

2. **`output/compressor.py`** — file mới, dùng Tree-sitter đã có:

   ```python
   COMPRESSION_NODE_TYPES = {
       'python': ['function_definition', 'class_definition', 'decorated_definition'],
       'typescript': ['function_declaration', 'class_declaration', 'interface_declaration'],
       'javascript': ['function_declaration', 'class_declaration'],
       'rust': ['function_item', 'impl_item', 'struct_item'],
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

3. **Marker format**: Dùng `# ... implementation` — consistent với Python convention, dễ đọc hơn Repomix's `⋮----`.

4. **Token reduction display**:

   ```
   ✓ Context packed with compression: 127,450 → 41,200 tokens (67% reduction)
   ```

5. **Language support** (tối thiểu): Python + TypeScript/JavaScript. Rust nếu parser đã có. Fallback: không compress cho unsupported languages.

6. **`docs/compression.md`** — [NEW] compression guide, signature extraction examples

**Files thay đổi**:

- `src/ws_ctx_engine/output/compressor.py` — [NEW]
- `src/ws_ctx_engine/cli/cli.py` — `--compress` flag
- `src/ws_ctx_engine/output/xml_packer.py` / `zip_packer.py` — integrate compressor
- `README.md` — compression docs
- `docs/compression.md` — [NEW]

**Acceptance criteria**:

```bash
wsctx pack . --compress                                              # Không crash
wsctx pack . --compress --format xml | grep "# ... implementation"  # Marker có mặt
# Token count với --compress thấp hơn không có --compress (40%+ reduction target)
wsctx pack . --compress --stdout | xmllint --noout -                 # Valid XML
```

---

### M5 — Config Cleanup (Residual)

**Thời gian**: 0.5–1 ngày

_Bulk của cleanup đã được gộp vào M1. Đây là những gì còn lại._

**Scope**:

- Verify `advanced.*` fields không được parse/dùng — nếu đang bị ignored silently, document điều đó
- Update docstrings trong `config/config.py`
- Remove hoặc đánh dấu experimental các fields còn lại trong config class

**Files thay đổi**:

- `src/ws_ctx_engine/config/config.py` — docstrings, remove residual aspirational fields

---

### M6 — Incremental Indexing

**Thời gian**: 5–7 ngày _(roadmap v1 estimate 3–5 ngày là quá lạc quan do bỏ sót FAISS migration và embedding cache)_

**Scope**:

1. **Migrate FAISS sang `IndexIDMap2`** (xem Correction C3):

   ```python
   def create_faiss_index(dim: int) -> faiss.IndexIDMap2:
       """Create FAISS index with ID mapping support for incremental updates."""
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
   # Persist:
   np.save(cache_dir / "embeddings.npy", all_embeddings)
   json.dump({"hash_to_idx": hash_to_idx_map}, open(cache_dir / "embedding_index.json"))
   ```

3. **Hash diff detection per file** trong `workflow/indexer.py` — so sánh với `IndexMetadata.file_hashes`

4. **Partial reparse + selective re-embed**:

   ```python
   def incremental_update(index, changed_paths, deleted_paths, new_chunks, embedding_cache):
       # Xóa vectors của files bị delete/changed
       ids_to_remove = get_chunk_ids_for_paths(deleted_paths + changed_paths)
       if ids_to_remove:
           index.remove_ids(np.array(ids_to_remove, dtype=np.int64))

       # Embed chỉ chunks mới (cache-miss)
       for chunk in new_chunks:
           content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
           if content_hash in embedding_cache:
               vec = embedding_cache[content_hash]   # Cache hit
           else:
               vec = embed(chunk.content)             # Cache miss — embed mới
               embedding_cache[content_hash] = vec
   ```

5. **Chunk serialization** — `to_dict()`/`from_dict()` trong `models/models.py`

6. **LEANN compatibility verification** — README đề cập LEANN là primary backend. Incremental update behavior của LEANN khác FAISS và cần verify riêng. Nếu LEANN không support incremental tương đương, M6 trước hết implement cho FAISS backend, sau đó port sang LEANN.

**Files thay đổi**:

- `src/ws_ctx_engine/vector_index/vector_index.py` / `faiss_index.py` — IndexIDMap2 migration
- `src/ws_ctx_engine/workflow/indexer.py` — incremental reindex logic, hash diff detection
- `src/ws_ctx_engine/models/models.py` — chunk serialization, embedding cache schema
- `src/ws_ctx_engine/cli/cli.py` — `--incremental` flag

**Acceptance criteria**:

```bash
wsctx index .                    # Full index build
touch src/modified_file.py       # Modify một file
wsctx index . --incremental      # Chỉ file đó được re-embedded (verify qua log)
rm src/deleted_file.py
wsctx index . --incremental      # File đó biến mất khỏi search results
wsctx query "test query"         # Query vẫn hoạt động đúng (non-regression)
```

---

### Future — Remote Repository Support

_Long-term item, không trong scope hiện tại nhưng cần strategic awareness._

```bash
wsctx pack https://github.com/user/repo
wsctx pack github:user/repo --branch main
```

Cần có: trust/no-trust config rõ ràng, sandbox cho remote content.

---

## Tổng hợp Timeline

| Milestone  | Nội dung                            | Estimate   | Priority                             |
| ---------- | ----------------------------------- | ---------- | ------------------------------------ |
| **M1**     | Hotfix + Config Quick Cleanup       | 1–2 ngày   | 🔴 Critical — prerequisite           |
| **M2**     | Ignore Semantics + Language Honesty | 2–3 ngày   | 🔴 High — developer trust            |
| **M3**     | CLI UX + Output Polish              | 3–4 ngày   | 🟠 High — UX parity                  |
| **M4**     | Compression Layer                   | 3–5 ngày   | 🟠 High — competitive differentiator |
| **M5**     | Config Cleanup (residual)           | 0.5–1 ngày | 🟡 Medium — polish                   |
| **M6**     | Incremental Indexing                | 5–7 ngày   | 🟡 Medium — performance              |
| **Future** | Remote Repository Support           | TBD        | 🟢 Low — long-term                   |

**Tổng**: 15–22 ngày làm việc (~3–4 tuần)

---

## Directory Structure (Sau tất cả milestones)

```
src/ws_ctx_engine/
├── cli/
│   └── cli.py                    # [M1] fix crash, __version__; [M3] --stdout, --copy, token count; [M4] --compress; [M6] --incremental
├── chunker/
│   ├── base.py                   # [M2] GitIgnoreSpec; INDEXED_EXTENSIONS; WARNING emit
│   └── tree_sitter.py            # [M2] minor; [M4] reuse cho compression
├── config/
│   └── config.py                 # [M1/M5] remove/mark aspirational fields
├── output/
│   ├── json_formatter.py         # [M3] JSON Schema conformance
│   ├── xml_packer.py             # [M3] --stdout support; [M4] integrate compressor
│   └── compressor.py             # [M4-NEW] Tree-sitter signature extraction
├── vector_index/
│   └── faiss_index.py            # [M6] IndexIDMap2 migration
├── workflow/
│   └── indexer.py                # [M6] incremental reindex + hash diff
├── models/
│   └── models.py                 # [M6] chunk serialization; embedding cache schema
└── __init__.py                   # [M1] importlib.metadata version

pyproject.toml                    # [M2] pathspec>=0.12
README.md                         # [M1/M3/M4] sync commands, pipe examples, compression docs
.ws-ctx-engine.yaml.example       # [M1/M5] remove/mark aspirational fields

docs/
├── output-schema.md              # [M3-NEW] JSON Schema + MCP response format spec
└── compression.md                # [M4-NEW] compression guide, signature extraction examples
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

M2 — Ignore Semantics (2–3 ngày):
[ ] Add pathspec>=0.12 vào pyproject.toml
[ ] Import GitIgnoreSpec (KHÔNG phải PathSpec)
[ ] Implement build_ignore_spec() với GitIgnoreSpec.from_lines()
[ ] Implement recursive .gitignore collection với path normalization
[ ] Add INDEXED_EXTENSIONS constant
[ ] Add WARNING log cho unindexable file extensions
[ ] Test: !negation patterns work; **/*.py đúng Git behavior

M3 — CLI UX (3–4 ngày):
[ ] Token count display sau pack/query
[ ] --stdout flag: log → stderr; loosen agent-mode restriction
[ ] --copy clipboard flag
[ ] JSON Schema + MCP response schema: docs/output-schema.md
[ ] Pipe examples trong README

M4 — Compression (3–5 ngày):
[ ] Create output/compressor.py với Tree-sitter
[ ] --compress flag trong pack + query commands
[ ] COMPRESSION_NODE_TYPES dict cho Python + TS/JS minimum
[ ] "# ... implementation" marker format
[ ] apply_compression_to_selected_files() với relevance threshold
[ ] Token reduction display
[ ] docs/compression.md

M5 — Config Cleanup (0.5–1 ngày):
[ ] Verify remaining aspirational config fields trong config.py
[ ] Update config.py docstrings

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
```

---

## Tài liệu tham khảo kỹ thuật

| Resource                                                   | Relevance                                         |
| ---------------------------------------------------------- | ------------------------------------------------- |
| `pathspec` PyPI — `GitIgnoreSpec` API                      | M2: correct class to use                          |
| pathspec CHANGES.rst — v1.0 breaking changes               | M2: `GitIgnoreSpec` vs `PathSpec` difference      |
| FAISS Special Operations wiki                              | M6: `IndexIDMap2`, `remove_ids` support           |
| Repomix compression docs (repomix.com/guide/code-compress) | M4: ~70% token reduction benchmark, marker format |
| `importlib.metadata` Python docs                           | M1: single-source version pattern                 |
| Adam Johnson: importlib.metadata (July 2025)               | M1: community 2025 consensus                      |
