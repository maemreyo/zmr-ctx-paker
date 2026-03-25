# ws-ctx-engine — Deep Research & Roadmap Evaluation Report

> **Ngày**: 2026-03-25
> **Phạm vi**: Tổng hợp từ comparison report + roadmap v1 + roadmap evaluation + web research thực tế
> **Mục tiêu**: Report đủ để review và implement — không cần tra cứu thêm

---

## Tóm tắt điều hành (TL;DR)

Roadmap v1 là kế hoạch stabilization đúng hướng nhưng có **4 vấn đề kỹ thuật cụ thể** cần sửa trước khi implement và **1 milestone chiến lược bị bỏ sót** làm giảm đáng kể giá trị cạnh tranh. Report này kết hợp audit kỹ thuật, web research thực tế về các thư viện liên quan, và đề xuất revised plan cuối cùng.

**Trạng thái dự án hiện tại**: Alpha có crash bug → cần đưa lên Beta usable trong ~3 tuần.

**Story cạnh tranh đúng**: Không phải "Repomix clone thông minh hơn" mà là **"retrieval-first context engine — chọn đúng file quan trọng nhất trước khi pack, sau đó compress để tiết kiệm token"**. Repomix làm tốt phần packaging; `ws-ctx-engine` làm tốt phần selection. Kết hợp cả hai trong một tool là story mạnh nhất.

---

## Phần 1 — Bối cảnh sản phẩm và định vị

### 1.1 Triết lý khác biệt cốt lõi

Repomix và ws-ctx-engine giải quyết các câu hỏi khác nhau:

- **Repomix**: _"Làm sao đóng gói repo này thành output tốt nhất cho AI?"_ → Ưu tiên breadth, UX đơn giản, packaging ergonomics, split output, compression.
- **ws-ctx-engine**: _"Trong repo này, file nào thực sự đáng được đưa vào context dưới token budget hữu hạn?"_ → Ưu tiên selection quality, retrieval depth, agent-native workflow.

Unit of value khác nhau: Repomix tối ưu cho **artifact đầu ra**; ws-ctx-engine tối ưu cho **quyết định chọn nội dung nào nên vào artifact**.

### 1.2 Điểm mạnh hiện tại (giữ nguyên, không cần đánh đổi)

| Thế mạnh               | Chi tiết                                                             |
| ---------------------- | -------------------------------------------------------------------- |
| Hybrid ranking         | Semantic + PageRank + exact symbol + path/domain/test penalty        |
| Query classification   | Tự động nhận diện `symbol` vs `path-dominant` vs `semantic-dominant` |
| Token budget selection | Greedy knapsack dưới budget, reserve 20% cho metadata                |
| Agent security         | Path guard + RADE delimiters + read-only MCP + rate limiting         |
| Domain map             | keyword → directory/bounded context                                  |
| Review-oriented output | `REVIEW_CONTEXT.md`, reading order, dependency hints                 |

### 1.3 Khoảng trống so với Repomix (cần fill theo thứ tự ROI)

| Gap                              | Mức độ                 | ROI của việc fix                   |
| -------------------------------- | ---------------------- | ---------------------------------- |
| Crash bug mặc định               | **Critical** — blocker | Unblock toàn bộ người dùng         |
| Docs/config drift                | Cao                    | Giảm mất tin tương ngay lập tức    |
| Ignore semantics                 | Cao                    | Developer trust                    |
| **Compression layer**            | **Cao**                | Differentiator cạnh tranh lớn nhất |
| CLI UX (stdout/copy/token count) | Trung bình             | UX parity với Repomix              |
| Incremental indexing             | Trung bình             | Performance cho repo lớn           |
| Remote repo support              | Thấp (long-term)       | Ecosystem breadth                  |

---

## Phần 2 — Audit kỹ thuật: Pathspec Library

### 2.1 Vấn đề trong roadmap v1

Roadmap v1 đề xuất: `PathSpec.from_lines('gitignore', patterns)`. Đây **không phải** cách chính xác nhất.

### 2.2 Kết quả research thực tế (pathspec v1.0.4, 2026)

Pathspec hiện có **hai implementation khác nhau** — đây là thay đổi breaking trong v1.0:

```
PathSpec.from_lines('gitignore', ...)
  → Follows gitignore DOCUMENTATION
  → KHÔNG handle edge cases mà Git thực tế làm khác docs
  → Ví dụ: "foo/*" sẽ không match files trong subdirectories

GitIgnoreSpec.from_lines(...)
  → Replicates Git's ACTUAL BEHAVIOR (bao gồm edge cases)
  → Handle re-include inside excluded directory (!pattern trong dir đã bị exclude)
  → Last-pattern-wins theo đúng cách Git làm
  → Sử dụng GitIgnoreSpecPattern internally (trước đây là GitWildMatchPattern)
```

**Confirmation từ pathspec v1.0 changelog và tác giả library** (verified từ GitHub issue #4944 của black, tháng 1/2026):

> "GitIgnoreSpecPattern is the previous GitWildMatchPattern implementation and is used by GitIgnoreSpec to implement Git's edge-cases. The form `PathSpec.from_lines('gitwildmatch', ...)` is now deprecated because it does not fully match the behavior of the gitignore docs or Git itself."

### 2.3 Lưu ý quan trọng về `negate` parameter

Khi dùng `GitIgnoreSpec` để tìm files cần **giữ lại** (không phải ignore), cần dùng `negate=True`:

```python
from pathspec import GitIgnoreSpec

spec = GitIgnoreSpec.from_lines(patterns)

# Tìm files nên IGNORE:
ignore_files = set(spec.match_tree_files('path/to/dir'))

# Tìm files nên GIỮ (negate=True):
keep_files = set(spec.match_tree_files('path/to/dir', negate=True))
```

### 2.4 Performance backends

pathspec v1.x hỗ trợ multiple regex backends: `'re2'`, `'hyperscan'`, `'simple'`. Default là `'best'` (auto-select re2 nếu available). Với repo lớn nhiều file, điều này có thể tăng performance đáng kể so với implementation cũ.

### 2.5 GitIgnoreSpec available từ version bao nhiêu?

`GitIgnoreSpec` được thêm vào pathspec **0.10.0**. Roadmap v1 đề xuất `pathspec>=0.12` — đây là an toàn và đúng (không cần downgrade requirement).

### 2.6 Implementation chính xác cho M2

```python
# pyproject.toml
# [project.dependencies]
# pathspec>=0.12  ← giữ nguyên requirement này

# chunker/base.py — ĐÚNG:
from pathspec import GitIgnoreSpec

def build_ignore_spec(patterns: list[str]) -> GitIgnoreSpec:
    """Build gitignore spec that replicates actual Git behavior."""
    return GitIgnoreSpec.from_lines(patterns)

def _should_include_file(path: str, spec: GitIgnoreSpec) -> bool:
    """Return True if file should be included (not ignored)."""
    return not spec.match_file(path)

# Hoặc dùng match_tree_files với negate cho batch operation:
def get_files_to_include(root: str, spec: GitIgnoreSpec) -> set[str]:
    return set(spec.match_tree_files(root, negate=True))
```

**Lưu ý**: Xóa bỏ fallback về fnmatch — pathspec là pure Python, không có C extension, sẽ không fail install trên bất kỳ platform nào. Fallback chỉ tăng complexity vô ích.

---

## Phần 3 — Audit kỹ thuật: FAISS Incremental Indexing

### 3.1 Vấn đề trong roadmap v1

Roadmap v1 nói "vector index cần support `update(new_chunks)` và `remove(deleted_paths)`" nhưng không cung cấp implementation detail về FAISS API limitations.

### 3.2 Kết quả research thực tế (FAISS documentation + GitHub issues)

**FAISS `IndexFlatIP` / `IndexFlatL2` KHÔNG có `remove_ids()` method trực tiếp.**

Để support deletion, **bắt buộc phải wrap trong `IndexIDMap`**:

```python
import faiss
import numpy as np

# KHÔNG làm được:
flat_index = faiss.IndexFlatIP(dim)
flat_index.remove_ids(...)  # ❌ AttributeError — method không tồn tại

# PHẢI wrap:
base_index = faiss.IndexFlatIP(dim)
index = faiss.IndexIDMap(base_index)
index.add_with_ids(vectors.astype(np.float32), ids.astype(np.int64))
index.remove_ids(np.array(deleted_ids, dtype=np.int64))  # ✅
```

### 3.3 `IndexIDMap` vs `IndexIDMap2` — Khi nào dùng cái nào?

|                                      | IndexIDMap                            | IndexIDMap2                                       |
| ------------------------------------ | ------------------------------------- | ------------------------------------------------- |
| Mục đích                             | Map external IDs → internal positions | Như IDMap nhưng store ngược lại internal→external |
| `remove_ids` support                 | ✅                                    | ✅                                                |
| `reconstruct` (lấy lại vector từ ID) | ❌                                    | ✅                                                |
| Phù hợp cho ws-ctx-engine            | ✅ (đủ dùng)                          | ✅ (nên dùng nếu cần debug/verify)                |

**Khuyến nghị**: Dùng `IndexIDMap2` — thêm khả năng reconstruct vector từ ID, hữu ích cho debug và verify embedding cache consistency.

### 3.4 Known issue với IndexIDMap add-remove-add cycle

Có một **known bug cũ** (issue #255, đã fix): Khi remove rồi add lại với cùng ID, `id_map.resize(ntotal)` cần được gọi. Bug này đã được fix trong FAISS >= 1.7.x. Nếu dùng phiên bản mới (faiss-cpu >= 1.7), không cần lo.

**Quan trọng**: Sau `remove_ids`, nếu cần add vectors mới với cùng chunk IDs (file được re-parsed), pattern đúng là:

```python
def update_chunks(index: faiss.IndexIDMap2,
                  old_ids: list[int],
                  new_embeddings: np.ndarray,
                  new_ids: np.ndarray):
    # Bước 1: Xóa vectors cũ
    if old_ids:
        index.remove_ids(np.array(old_ids, dtype=np.int64))
    # Bước 2: Thêm vectors mới
    index.add_with_ids(new_embeddings.astype(np.float32), new_ids.astype(np.int64))
```

### 3.5 Embedding cache — Gap quan trọng chưa được address

Roadmap v1 nói "serialize chunks" nhưng không mention embedding cache. Đây là vấn đề lớn về performance:

**Scenario incremental reindex:**

- File A không thay đổi → không cần reparse, không cần re-embed ← **phải có cache**
- File B thay đổi → reparse, re-embed từ scratch
- File C mới → parse, embed từ scratch

Nếu không cache embedding theo content hash, incremental indexing chỉ tiết kiệm phần parsing (~nhỏ), không tiết kiệm phần embedding — thường là bottleneck chính với sentence-transformers trên CPU.

**Design đề xuất cho `IndexMetadata`:**

```python
# models/models.py — thêm vào IndexMetadata
@dataclass
class IndexMetadata:
    file_hashes: dict[str, str]          # path → sha256 hex
    chunk_embedding_cache: dict[str, list[float]]  # content_hash → embedding vector
    # hoặc lưu ra file riêng để tránh JSON lớn:
    # chunk_embedding_cache_path: str   # path tới .npy file
    index_version: str
    created_at: str
```

**Trade-off**: Lưu embeddings trong JSON sẽ rất lớn (mỗi vector 384-768 float). Nên dùng numpy `.npy` file với lookup dict riêng:

```python
# Persist embeddings ra disk:
np.save(cache_dir / "embeddings.npy", all_embeddings)
json.dump({"hash_to_idx": hash_to_idx_map}, open(cache_dir / "embedding_index.json"))
```

### 3.6 LEANN backend — Cần verify riêng

README đề cập LEANN là primary backend với "97% storage savings". LEANN là graph-based ANN library (ít mainstream hơn FAISS). **Roadmap cần explicitly note**: Incremental update behavior của LEANN khác FAISS và cần được verify riêng. Nếu LEANN không support incremental update tương đương, M6 (Incremental Indexing) trước hết nên implement cho FAISS backend, sau đó port cho LEANN.

---

## Phần 4 — Research: Repomix Compression (đối chiếu để implement M4-new)

### 4.1 Trạng thái hiện tại của Repomix compression (verified tháng 3/2026)

Repomix `--compress` là **production feature** (không còn experimental flag), được document chính thức:

- Dùng Tree-sitter để extract essential code structures
- Giữ lại: class signatures, function signatures, interfaces, import statements
- Loại bỏ: function bodies (replace bằng `⋮----` marker)
- Token reduction: **~70%** (verified, không phải estimate)
- Available trong cả CLI (`--compress`), config (`output.compress: true`), và MCP tool parameter

**Ví dụ compression output của Repomix** (từ official docs):

```typescript
// Input:
const calculateTotal = (items: ShoppingItem[]) => {
  let total = 0;
  for (const item of items) {
    total += item.price * item.quantity;
  }
  return total;
}

// Output với --compress:
const calculateTotal = (items: ShoppingItem[]) => {
⋮----
}
```

### 4.2 Lợi thế của ws-ctx-engine nếu implement compression

Repomix compression là **dumb compression** — nó compress mọi file được include. ws-ctx-engine có thể làm **smart compression**: chỉ compress files được retrieval engine chọn, với khả năng **selective compression level** theo relevance score:

```
High relevance files  → full content (không compress, LLM cần đọc kỹ)
Medium relevance files → signature-only compression (~70% savings)
Low relevance files    → signature + docstring only (~85% savings)
```

Đây là story mạnh hơn Repomix — không chỉ "compress giống Repomix" mà là "compress thông minh hơn dựa trên relevance".

### 4.3 Implementation approach cho ws-ctx-engine (M4-new)

ws-ctx-engine đã có Tree-sitter parsing trong `chunker/tree_sitter.py` để tạo `CodeChunk`. Foundation này đủ để implement compression.

```python
# output/compressor.py — file mới
from tree_sitter import Language, Parser

COMPRESSION_NODE_TYPES = {
    'python': ['function_definition', 'class_definition', 'decorated_definition'],
    'typescript': ['function_declaration', 'class_declaration', 'interface_declaration'],
    'javascript': ['function_declaration', 'class_declaration'],
    'rust': ['function_item', 'impl_item', 'struct_item'],
    'go': ['function_declaration', 'method_declaration', 'type_declaration'],
}

def compress_file_content(
    content: str,
    file_extension: str,
    preserve_docstrings: bool = True,
) -> str:
    """
    Extract signatures only, replace function bodies with '# ...' marker.
    Returns compressed content string.
    """
    # Dùng tree_sitter parser đã có trong codebase
    # Walk AST, emit node captures theo COMPRESSION_NODE_TYPES
    # Replace body nodes với placeholder
    ...

def apply_compression_to_selected_files(
    selected_files: list[SelectedFile],
    config: CompressionConfig,
) -> list[SelectedFile]:
    """Apply compression after retrieval selection."""
    for f in selected_files:
        if f.relevance_score >= config.full_content_threshold:
            continue  # High relevance: giữ full content
        f.content = compress_file_content(f.content, f.extension)
    return selected_files
```

**Marker format**: Dùng `# ... implementation` thay vì Repomix's `⋮----` để dễ đọc hơn và consistent với Python convention.

---

## Phần 5 — Research: Version Management Best Practice

### 5.1 Vấn đề trong roadmap v1

Roadmap v1 nói "sync `__version__` về `0.1.10`" — đây là hardcode, sẽ drift lại.

### 5.2 Python packaging standard 2025: Single-source version

Pattern chuẩn hiện tại (Python 3.8+, recommended 2025):

```python
# src/ws_ctx_engine/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ws-ctx-engine")
except PackageNotFoundError:
    # Package chưa được install (e.g., chạy trực tiếp từ source)
    __version__ = "0.0.0+dev"
```

Cách này:

- Version được lấy dynamically từ `pyproject.toml` sau khi install
- Không bao giờ drift vì chỉ có một source of truth
- `PackageNotFoundError` guard đảm bảo không crash trong dev environment
- `PackageNotFoundError` available từ Python 3.8 trong stdlib — không cần extra dependency

**Lưu ý**: PEP 396 (đặt `__version__` thủ công) đã bị **rejected**. Community 2025 consensus là dùng `importlib.metadata`. Reference: discussion trên Python forum và Adam Johnson's article (July 2025).

### 5.3 Nơi dùng `__version__` trong codebase

- `cli.py`: `@app.callback(invoke_without_command=True)` → hiển thị version qua `typer.Option`
- NDJSON agent mode status payload: thêm `"engine_version": __version__`
- Output XML/JSON metadata block

---

## Phần 6 — Đánh giá cuối cùng từng Milestone (Revised)

### M1 — Hotfix + Config Quick Cleanup

**Verdict**: ✅ Đúng hoàn toàn. Là prerequisite bắt buộc.

**Scope đầy đủ** (bao gồm các item bị bỏ sót trong roadmap v1):

1. **Fix `_set_console_log_level` crash** — define hàm này trước `@app.callback()` trong `cli.py`:

   ```python
   def _set_console_log_level(quiet: bool) -> None:
       import logging
       level = logging.WARNING if quiet else logging.INFO
       logging.getLogger("ws_ctx_engine").setLevel(level)
   ```

2. **Sync `__version__` via `importlib.metadata`** — dùng dynamic version, không hardcode (xem Phần 5.2)

3. **Audit `--changed-files` flag** — comparison report xác nhận README nhắc đến flag này nhưng CLI không expose đúng như documented. Quyết định: implement đúng **hoặc** remove khỏi README. Không thể để inconsistency này tồn tại sau M1.

4. **Comment out aspirational config fields ngay** — nhanh (~4 giờ), không cần standalone milestone:
   - `logging.level`, `logging.file` → comment out hoặc remove khỏi `.ws-ctx-engine.yaml.example`
   - `advanced.pagerank_*`, `advanced.min/max_file_size`, `advanced.validate_roundtrip` → mark `# NOT YET IMPLEMENTED`
   - `max_workers`, `cache_embeddings`, `incremental_index` → mark `# PLANNED — not active`

5. **README sync** — thêm 6 commands còn thiếu, fix format options

**Acceptance criteria**:

- `wsctx --help` không crash
- `wsctx pack .` với default config không crash
- `wsctx --version` hiển thị đúng version từ pyproject.toml

**Estimate**: 1–2 ngày

---

### M2 — Ignore Semantics + Language Honesty

**Verdict**: ✅ Đúng hướng, với correction kỹ thuật quan trọng.

**Correction**: Dùng `GitIgnoreSpec` thay vì `PathSpec.from_lines('gitignore', ...)` (xem Phần 2 cho full explanation và code examples).

**Scope**:

1. Add `pathspec>=0.12` vào `pyproject.toml` dependencies
2. Refactor `_should_include_file` trong `chunker/base.py` dùng `GitIgnoreSpec`
3. Implement recursive `.gitignore` discovery (walk subdirectories, merge patterns)
4. Add `INDEXED_EXTENSIONS` constant trong `chunker/base.py`
5. Emit `[WARNING]` khi file matched nhưng không có AST parser

**Chi tiết recursive `.gitignore` discovery**:

```python
def collect_gitignore_patterns(root: Path) -> list[str]:
    """Walk directory tree, collect all .gitignore patterns with path normalization."""
    all_patterns = []
    for gitignore_path in root.rglob('.gitignore'):
        relative_dir = gitignore_path.parent.relative_to(root)
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Prefix với relative directory để scope đúng
                    if str(relative_dir) != '.':
                        all_patterns.append(f"{relative_dir}/{line}")
                    else:
                        all_patterns.append(line)
    return all_patterns
```

**Acceptance criteria**:

- `!negation` patterns hoạt động đúng
- `**/*.py` pattern match đúng behavior của Git
- File `.java` → warning rõ ràng, không silent skip
- Subdirectory `.gitignore` được respect

**Estimate**: 2–3 ngày

---

### M3 — CLI UX + Output Polish

**Verdict**: ✅ Đúng, với một correction về `--stdout` restriction.

**Correction**: Roadmap v1 nói `--stdout` và `--agent-mode` không được dùng cùng nhau. **Quá restrictive**. Pipe-to-LLM là use case quan trọng:

```bash
wsctx pack . --format xml --stdout | pbcopy
wsctx query "auth flow" --format xml --stdout | claude
wsctx pack . --stdout --agent-mode  # → NDJSON to stdout, valid use case
```

Logic đúng: `--stdout` với `--agent-mode` → output NDJSON to stdout; `--stdout` không có `--agent-mode` → output XML/JSON to stdout. Hai modes này không conflict.

**Scope**:

1. Token count display sau pack/query: `console.print(f"  Tokens: {total:,} / {budget:,}")`
2. `--stdout` flag với loosen restriction (xem trên)
3. `--copy` clipboard flag
4. JSON Schema cho output format + MCP response format → `docs/output-schema.md`
5. README examples: thêm pipe examples

**Acceptance criteria**:

- `wsctx pack . --stdout --format xml | head` output valid XML đến stdout
- Token count hiển thị sau mọi pack/query operation
- Không có log ra stdout khi `--stdout` được set (log vẫn đi stderr)

**Estimate**: 3–4 ngày

---

### M4-NEW — Compression Layer

**Verdict**: ⭐ Gap chiến lược quan trọng nhất bị bỏ sót trong roadmap v1. **Nên implement trước M5/M6.**

**Tại sao đây là priority cao**:

- Repomix compression là feature được user nhắc đến nhiều nhất khi so sánh tools
- ws-ctx-engine đã có Tree-sitter foundation → implementation effort thấp hơn build từ đầu
- ws-ctx-engine có thể làm **smart compression** (dựa trên relevance score) — differentiated hơn Repomix's dumb compression
- ROI cao nhất trong các milestones còn lại

**Scope**:

1. `--compress` flag trong `pack` và `query` commands
2. `output/compressor.py` mới — dùng Tree-sitter đã có
3. Giữ: signatures, docstrings (configurable), imports
4. Replace bodies với `# ... implementation` marker
5. Token reduction display: `"  Compression: 127,450 → 41,200 tokens (67% reduction)"`
6. Selective compression theo relevance score (optional, có thể để v2)

**Languages cần support (dùng Tree-sitter đã có trong codebase)**:

- Python, TypeScript/JavaScript — priority cao
- Rust, Go — nếu parsers đã có
- Fallback: không compress cho unsupported languages

**Acceptance criteria**:

- `wsctx pack . --compress` chạy không crash
- Token count reduction hiển thị sau compression
- Output vẫn valid XML/JSON với compressed content

**Estimate**: 3–5 ngày

---

### M5 — Config Cleanup (residual)

**Verdict**: ✅ Đúng — nhưng bulk của M5 đã được gộp vào M1. Đây chỉ là cleanup còn lại.

**Scope** (những gì chưa làm trong M1):

- Remove hoặc đánh dấu experimental các fields còn lại trong config class
- Verify `advanced.*` fields không được parse/dùng (nếu đang bị ignored silently, document điều đó)
- Update docstrings trong `config/config.py`

**Estimate**: 0.5–1 ngày

---

### M6 — Incremental Indexing

**Verdict**: ✅ Correct approach. Nhưng estimate trong roadmap v1 (3–5 ngày) **quá lạc quan**.

**Revised estimate**: 5–7 ngày (vì FAISS migration + embedding cache + LEANN verification)

**Scope** (với corrections từ Phần 3):

1. **Migrate FAISS index sang `IndexIDMap2`** — đây là migration step, không nhỏ nếu codebase hiện dùng `IndexFlatIP` trực tiếp
2. **Implement embedding cache** (content hash → vector) — tránh re-embed unchanged files
3. **Hash diff detection** per file trong `workflow/indexer.py`
4. **Partial reparse + selective re-embed**
5. **LEANN compatibility check** — document nếu LEANN cần separate implementation path
6. **Chunk serialization** — `to_dict()`/`from_dict()` trong `models/models.py`

**Implementation note cho FAISS migration**:

```python
# workflow/indexer.py
import faiss
import numpy as np

def create_faiss_index(dim: int) -> faiss.IndexIDMap2:
    """Create FAISS index with ID mapping support for incremental updates."""
    base = faiss.IndexFlatIP(dim)
    return faiss.IndexIDMap2(base)

def incremental_update(
    index: faiss.IndexIDMap2,
    changed_paths: list[str],
    deleted_paths: list[str],
    new_chunks: list[CodeChunk],
    embedding_cache: dict[str, np.ndarray],
) -> None:
    # Xóa vectors của files bị delete/changed
    ids_to_remove = get_chunk_ids_for_paths(deleted_paths + changed_paths)
    if ids_to_remove:
        index.remove_ids(np.array(ids_to_remove, dtype=np.int64))

    # Embed chỉ chunks mới (cache-miss)
    embeddings_to_add = []
    ids_to_add = []
    for chunk in new_chunks:
        content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
        if content_hash in embedding_cache:
            vec = embedding_cache[content_hash]  # Cache hit — không re-embed
        else:
            vec = embed(chunk.content)           # Cache miss — embed mới
            embedding_cache[content_hash] = vec
        embeddings_to_add.append(vec)
        ids_to_add.append(chunk.id)

    index.add_with_ids(
        np.array(embeddings_to_add, dtype=np.float32),
        np.array(ids_to_add, dtype=np.int64)
    )
```

**Acceptance criteria**:

- Modify 1 file, reindex → log hiển thị chỉ file đó được re-embedded
- Delete 1 file, reindex → file đó biến mất khỏi search results
- Full rebuild vẫn hoạt động như cũ (non-regression)

**Estimate**: 5–7 ngày

---

## Phần 7 — Revised Milestone Plan (Cuối cùng)

```
REVISED ORDER (tổng ~4–5 tuần):

M1 — Hotfix + Config Quick Cleanup          [1–2 ngày]
  ├── Fix _set_console_log_level crash
  ├── __version__ via importlib.metadata
  ├── Audit + fix --changed-files inconsistency
  ├── Comment out aspirational config fields
  └── README sync (6 missing commands)
  ✓ Acceptance: wsctx pack . không crash với default config

M2 — Ignore Semantics + Language Honesty    [2–3 ngày]
  ├── Add pathspec>=0.12 dependency
  ├── Use GitIgnoreSpec (NOT PathSpec.from_lines)
  ├── negate=True pattern cho "files to keep"
  ├── Recursive .gitignore discovery
  └── INDEXED_EXTENSIONS + WARNING emit
  ✓ Acceptance: !negation patterns work; Java files warn

M3 — CLI UX + Output Polish                 [3–4 ngày]
  ├── Token count display post-pack/query
  ├── --stdout flag (loosen agent-mode restriction)
  ├── --copy clipboard flag
  ├── JSON Schema + MCP response schema docs
  └── Pipe examples trong README
  ✓ Acceptance: wsctx pack . --stdout | head works

M4-NEW — Compression Layer                  [3–5 ngày]
  ├── --compress flag
  ├── output/compressor.py (Tree-sitter signature extraction)
  ├── Replace function bodies với "# ... implementation"
  ├── Token reduction display
  └── Support Python + TS/JS minimum
  ✓ Acceptance: --compress shows token savings; output valid

M5 — Config Cleanup (residual)              [0.5–1 ngày]
  └── Clean up remaining config fields/docstrings

M6 — Incremental Indexing                   [5–7 ngày]
  ├── Migrate FAISS → IndexIDMap2
  ├── Embedding cache (content hash → vector)
  ├── Hash diff detection per file
  ├── Partial reparse + selective re-embed
  └── LEANN compatibility verification
  ✓ Acceptance: modify 1 file → only 1 file re-embedded

FUTURE — Remote Repository Support          [long-term]
  └── wsctx pack github:user/repo --branch main
```

**Tổng estimate**: 15–22 ngày làm việc (~3–4 tuần với buffer.

---

## Phần 8 — Acceptance Criteria Tổng hợp (Per Milestone)

Mỗi milestone khi shipped phải pass tất cả test cases sau:

### M1 Acceptance Tests

```bash
wsctx --help                    # Không crash
wsctx --version                 # Hiển thị đúng version
wsctx pack .                    # Không crash với default config
wsctx pack . --quiet            # Không crash (đây là crash case gốc)
```

### M2 Acceptance Tests

```bash
# Tạo test repo với .gitignore có negation:
echo "*.log\n!important.log" > .gitignore
wsctx pack .                    # important.log phải được include
wsctx pack . --include "**/*.java"  # Warning: no AST parser available
# Kiểm tra subdirectory .gitignore được respect
```

### M3 Acceptance Tests

```bash
wsctx pack . --stdout --format xml | xmllint --noout -  # Valid XML
wsctx pack . --stdout --format json | python -m json.tool  # Valid JSON
wsctx pack . --stdout 2>/dev/null | wc -c  # Content đi stdout, log đi stderr
# Token count hiển thị trong terminal output (stderr)
```

### M4-NEW Acceptance Tests

```bash
wsctx pack . --compress          # Không crash
wsctx pack . --compress --format xml | grep "# ... implementation"  # Marker có mặt
# Token count với --compress thấp hơn không có --compress (40%+ reduction target)
```

### M6 Acceptance Tests

```bash
wsctx index .                   # Full index build
touch src/modified_file.py      # Modify một file
wsctx index . --incremental     # Chỉ file đó được re-embedded (verify qua log)
rm src/deleted_file.py
wsctx index . --incremental     # File đó biến mất khỏi search results
wsctx query "test query"        # Query vẫn hoạt động đúng
```

---

## Phần 9 — Directory Structure Updated (Sau tất cả milestones)

```
src/ws_ctx_engine/
├── cli/
│   └── cli.py                    # [M1] fix crash; [M3] --stdout, --copy, token count
├── chunker/
│   ├── base.py                   # [M2] GitIgnoreSpec; INDEXED_EXTENSIONS; WARNING emit
│   └── tree_sitter.py            # [M2] minor; [M4] reuse cho compression
├── config/
│   └── config.py                 # [M1/M5] remove/mark aspirational fields
├── output/
│   ├── json_formatter.py         # [M3] JSON Schema conformance
│   ├── xml_formatter.py          # [M3] --stdout support
│   └── compressor.py             # [M4-NEW] Tree-sitter signature extraction
├── workflow/
│   └── indexer.py                # [M6] incremental reindex + hash diff
├── models/
│   └── models.py                 # [M6] chunk serialization; embedding cache schema
└── __init__.py                   # [M1] importlib.metadata version

pyproject.toml                    # [M2] pathspec>=0.12
README.md                         # [M1/M3/M4] sync commands, examples, compression docs
.ws-ctx-engine.yaml.example       # [M1/M5] remove/mark aspirational fields

docs/
├── output-schema.md              # [M3-NEW] JSON Schema + MCP response spec
└── compression.md                # [M4-NEW] compression guide (signature extraction examples)
```

---

## Phần 10 — Strategic Positioning: Sau khi hoàn thành 6 milestones

Product story sẽ là:

> **ws-ctx-engine**: Intelligent context engine cho code agents.
>
> Retrieval-first với hybrid ranking (semantic + PageRank + heuristics), compression sau retrieval, gitignore-native semantics, và agent-native MCP interface an toàn.
>
> Không chỉ pack repo — **chọn đúng phần codebase quan trọng nhất, rồi compress để fit vào token budget.**

Differentiation rõ ràng so với Repomix:

- Repomix: pack mọi thứ hoặc filter thủ công → compress
- ws-ctx-engine: retrieve intelligently (semantic + graph) → compress smart (dựa trên relevance)

Đây là story không bị overlap trực tiếp — hai tools sẽ ở hai lớp khác nhau của cùng workflow:

```
[codebase] → [ws-ctx-engine: retrieval + smart compression] → [AI context]
[codebase] → [Repomix: full pack + dumb compression]       → [AI context]
```

---

## Checklist Implement (Theo thứ tự)

```
M1 (unblock ngay):
[ ] Define _set_console_log_level trong cli.py
[ ] Replace hardcoded __version__ với importlib.metadata pattern
[ ] Add PackageNotFoundError guard
[ ] Audit --changed-files: implement hoặc remove khỏi README
[ ] Comment out aspirational YAML fields với note rõ ràng
[ ] Add 6 missing commands vào README
[ ] Test: wsctx pack . --quiet không crash

M2 (gitignore):
[ ] Add pathspec>=0.12 vào pyproject.toml
[ ] Import GitIgnoreSpec (không phải PathSpec)
[ ] Implement build_ignore_spec() với GitIgnoreSpec.from_lines()
[ ] Implement recursive .gitignore collection
[ ] Add INDEXED_EXTENSIONS constant
[ ] Add WARNING log cho unindexable file extensions
[ ] Test negation patterns

M3 (UX):
[ ] Token count display sau pack/query
[ ] --stdout flag với correct behavior (log → stderr)
[ ] Loosen --stdout + --agent-mode restriction
[ ] --copy clipboard flag
[ ] JSON Schema doc: docs/output-schema.md
[ ] Pipe examples trong README

M4-NEW (compression):
[ ] Create output/compressor.py
[ ] --compress flag trong pack + query commands
[ ] Tree-sitter signature extraction (Python + TS/JS minimum)
[ ] "# ... implementation" marker format
[ ] Token reduction display
[ ] docs/compression.md

M5 (cleanup):
[ ] Verify remaining aspirational config fields
[ ] Update config.py docstrings

M6 (incremental):
[ ] Migrate FAISS index → IndexIDMap2
[ ] Add embedding cache (content hash → numpy vector)
[ ] Hash diff detection trong indexer.py
[ ] Chunk serialization trong models.py
[ ] LEANN compatibility check + doc
[ ] Incremental reindex logic
[ ] Test: modify 1 file → only 1 file re-embedded
```

---

## Tài liệu tham khảo

| Resource                          | URL                                                                  | Relevance                   |
| --------------------------------- | -------------------------------------------------------------------- | --------------------------- |
| pathspec PyPI                     | https://pypi.org/project/pathspec/                                   | GitIgnoreSpec API, backends |
| pathspec CHANGES.rst              | github.com/cpburnz/python-pathspec/blob/master/CHANGES.rst           | v1.0 breaking changes       |
| FAISS Special Operations          | github.com/facebookresearch/faiss/wiki/Special-operations-on-indexes | remove_ids support          |
| Repomix compression docs          | https://repomix.com/guide/code-compress                              | Token reduction benchmark   |
| importlib.metadata (Python 3.12+) | https://docs.python.org/3/library/importlib.metadata.html            | Single-source version       |
| Adam Johnson: importlib.metadata  | adamj.eu/tech/2025/07/30/                                            | Best practice 2025          |
