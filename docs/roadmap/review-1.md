# Đánh giá Roadmap `ws-ctx-engine` — Comprehensive Review

> Ngày: 2026-03-25 | Dựa trên: GitHub repo, comparison report, web research (pathspec, FAISS, Repomix latest)

---

## 1. Tóm tắt điều hành

Roadmap v1 là một **"stabilization plan" tốt** — nó đúng ưu tiên, đúng milestone ordering, và có implementation notes đủ cụ thể để implement. Nếu hoàn thành đúng 5 milestone này, project sẽ chuyển từ Alpha có bug crash lên **Beta usable**.

Tuy nhiên, roadmap hiện tại có **3 loại vấn đề** cần được giải quyết trước khi implement:

| Loại                               | Mức độ | Ví dụ                                                                                                           |
| ---------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------- |
| **Kỹ thuật sai / thiếu**           | Cao    | Dùng `PathSpec` thay vì `GitIgnoreSpec`; FAISS IDMap pattern bị bỏ qua; chunk embedding cache chưa được address |
| **Tính năng chiến lược bị bỏ qua** | Cao    | Không có compression milestone — đây là lợi thế cạnh tranh #1 của Repomix (~70% token reduction)                |
| **Scope creep / sắp xếp sai**      | Thấp   | M4 có thể gộp vào M1; một số M3 items nên lên M1.5                                                              |

---

## 2. Đánh giá từng Milestone

### M1 — Hotfix & Unblock ✅ Đúng, nhưng scope thiếu

**Đánh giá**: Đúng hoàn toàn về priority. `_set_console_log_level` crash là blocker tuyệt đối — mọi thứ phải chờ cái này.

**Thiếu trong M1 scope:**

1. **`--changed-files` flag inconsistency**: Comparison report xác nhận README đang nhắc đến `--changed-files` nhưng CLI không expose nó đúng như documented. M1 cần explicitly audit điều này và quyết định: implement đúng hoặc remove khỏi README. Hiện tại roadmap chỉ nói "fix README thiếu 6 commands" nhưng không mention cái inconsistency này.

2. **`__version__` sync logic**: Implementation note nói sync về `0.1.10` — đúng. Nhưng cần thêm guard: version phải được lấy dynamically từ `importlib.metadata.version('ws-ctx-engine')` trong `__init__.py`, không hardcode. Hardcode sẽ gây drift lại.

3. **Kiểm tra M4 "quick wins" có thể làm ngay**: Fields như `logging.level`, `logging.file` trong example config không cần cả milestone riêng — có thể comment out ngay trong M1 với 10 phút effort.

**Estimate**: 1-2 ngày — đúng.

---

### M2 — Ignore Semantics & Language Honesty ⚠️ Đúng hướng, sai class

**Đánh giá**: Quyết định dùng `pathspec` là đúng và được validate bởi ecosystem — đây là library được dùng bởi black, isort, và nhiều tooling lớn. Tuy nhiên có một lỗi kỹ thuật quan trọng trong implementation note.

**Lỗi kỹ thuật — `PathSpec` vs `GitIgnoreSpec`:**

Roadmap nói dùng `pathspec.PathSpec` với `'gitignore'` pattern. Đây **không phải** cách chính xác nhất để replicate git behavior.

`pathspec` có hai class:

```python
# CÁCH ROADMAP ĐỀ XUẤT — Partial gitignore compliance
spec = PathSpec.from_lines('gitignore', patterns)

# CÁCH ĐÚNG — Full git edge-case replication
from pathspec import GitIgnoreSpec
spec = GitIgnoreSpec.from_lines(patterns)
```

`GitIgnoreSpec` xử lý các edge case mà `PathSpec` không handle:

- **Re-include inside excluded directory**: Git cho phép `!subdir/file.py` re-include một file trong directory đã bị exclude. `PathSpec.from_lines('gitignore')` không handle đúng edge case này. `GitIgnoreSpec` mới handle được.
- **Priority order**: `GitIgnoreSpec` xử lý last-pattern-wins theo đúng cách git thực hiện.

**Fix**: Thay `PathSpec.from_lines('gitignore', ...)` bằng `GitIgnoreSpec.from_lines(...)` trong implementation. Version target vẫn là `pathspec>=0.12` — không thay đổi.

**Fallback note**: Roadmap đề xuất fallback về fnmatch nếu pathspec unavailable. Điều này thực ra không cần thiết — pathspec là pure Python, không có C extension, install trên bất kỳ platform nào. Fallback chỉ làm tăng code complexity. Nếu pathspec không available thì pyproject.toml dependency install đã fail rồi. Nên xóa fallback logic.

**Language honesty approach** — `[WARNING]` emit — là đúng và pragmatic. Không cần breaking change.

**Estimate**: 2-3 ngày — đúng.

---

### M3 — CLI UX & Output Polish ⚠️ Thiếu item quan trọng nhất

**Đánh giá**: Token count display và `--stdout` là đúng. JSON Schema là đúng. Nhưng M3 đang **thiếu feature có impact lớn nhất** đối với competitive positioning.

**Thiếu: `--stdout` pipe ergonomics**

Roadmap nói: `"--stdout` và `--agent-mode` không được dùng cùng nhau." Điều này **quá restrictive**. Repomix's killer UX là:

```bash
repomix --stdout | llm "explain this codebase"
repomix --stdout > output.txt
```

Pipe-to-LLM là use case quan trọng. NDJSON cho agent là khác với XML/JSON cho pipe. Hai thứ này không conflict nhau. Cần loosen restriction thành: `--stdout` với `--agent-mode` thì output là NDJSON to stdout; `--stdout` không có `--agent-mode` thì output là XML/JSON to stdout.

**`--stdout` thêm vào README examples là phải đi kèm với actual pipe example:**

```bash
# Example cần document
wsctx pack . --format xml --stdout | pbcopy
wsctx query "auth flow" --format xml --stdout | claude
```

**Thiếu: Split output**

Repomix có `--split-output 20mb`. Với repo lớn, single XML file có thể quá lớn cho context window. `ws-ctx-engine` có budget selection (điểm mạnh), nên split output ít cần thiết hơn — nhưng vẫn nên có flag `--max-output-size` để split thành multiple files.

**JSON Schema output**: Đây là M3 item đúng và quan trọng cho agent consumers. Cần đảm bảo schema bao gồm cả MCP response format, không chỉ file output format.

**Estimate**: 2-3 ngày — đúng, nhưng nếu thêm split output thì 3-4 ngày.

---

### M4 — Config Cleanup ✅ Đúng, nhưng overscoped thành milestone riêng

**Đánh giá**: Các thay đổi trong M4 đúng về content. Nhưng đây không cần cả milestone riêng 2-3 ngày.

**Thực tế effort M4:**

- Comment out aspirational fields trong YAML example: ~30 phút
- Remove/mark `logging.*` section: ~30 phút
- Verify `advanced.*` fields không được parse/used: ~1 giờ review
- Mark `max_workers`, `cache_embeddings`, `incremental_index` là `# NOT YET IMPLEMENTED`: ~20 phút

**Tổng**: ≤4 giờ. Đây là M1.5, không phải standalone milestone.

**Đề xuất**: Gộp M4 vào cuối M1 hoặc đầu M2. Dùng thời gian tiết kiệm được để làm **M6 — Compression** (xem phần 3).

---

### M5 — Incremental Indexing ⚠️ Correct approach, nhưng implementation notes thiếu chi tiết quan trọng

**Đánh giá**: Approach "partial reparse → rebuild vector/graph từ changed + unchanged chunks" là pragmatic và đúng hướng. Nhưng có 2 vấn đề kỹ thuật trong implementation notes chưa được address.

**Vấn đề 1: FAISS không native support `remove()` trên flat index**

Roadmap nói "vector index cần support `update(new_chunks)` và `remove(deleted_paths)`" nhưng không nói cách implement.

FAISS `IndexFlatIP`/`IndexFlatL2` (likely được dùng trong project) **không support `remove_ids()`** trực tiếp. Để support incremental update với deletion, cần wrap trong `IndexIDMap`:

```python
# Không làm được trực tiếp:
index.remove(deleted_ids)  # ❌ không có method này trên IndexFlat

# Phải wrap:
base_index = faiss.IndexFlatIP(dim)
index = faiss.IndexIDMap(base_index)
index.add_with_ids(vectors, int64_ids)
index.remove_ids(deleted_id_array)  # ✅ works
```

Implementation note cần explicitly mention pattern này. Nếu codebase hiện tại dùng `IndexFlatIP` không có IDMap, đây là một migration step không nhỏ.

**Vấn đề 2: Chunk embedding cache phải được address**

Roadmap nói "cần serialize chunks" nhưng không mention embedding cache.

Kịch bản incremental reindex:

1. File A không thay đổi → không cần reparse, không cần re-embed
2. File B thay đổi → reparse, **cần re-embed**
3. File C mới → parse, **cần embed**

Để bước 1 thực sự fast, phải cache embeddings theo content hash, không chỉ serialize chunk text. Nếu không có embedding cache, incremental indexing chỉ tiết kiệm được phần parsing, không tiết kiệm phần embedding (đây thường là bottleneck chính cho repo lớn với sentence-transformers).

**Implementation note cần thêm:**

```python
# Embedding cache structure cần thêm vào IndexMetadata
{
  "file_hashes": {...},
  "chunk_embedding_cache": {
    "chunk_content_hash_hex": embedding_vector_as_list  # hoặc reference tới numpy file
  }
}
```

**Vấn đề 3: LEANN backend**

README mentions LEANN là primary backend ("97% storage savings"). LEANN là một graph-based ANN library ít mainstream hơn FAISS. Incremental update behavior của LEANN cần được verify riêng — roadmap giả định behavior tương tự FAISS nhưng không nói rõ. Nếu LEANN không support incremental update theo cách tương tự, M5 chỉ work cho FAISS fallback.

**Estimate revised**: 5-7 ngày (không phải 3-5), đặc biệt nếu FAISS migration sang IndexIDMap là needed.

---

## 3. Gap Lớn Nhất: Compression Milestone Bị Bỏ Qua

Đây là điểm quan trọng nhất trong toàn bộ evaluation.

### Bối cảnh

Repomix hiện tại (v0.2.28+) có `--compress` flag dùng Tree-sitter để extract code signatures, giảm ~70% token count. Đây là lợi thế cạnh tranh rất rõ — một codebase 200k tokens có thể pack thành 60k tokens.

`ws-ctx-engine` đã có Tree-sitter parsing trong codebase (dùng để tạo `CodeChunk`). Đây là **foundation đã sẵn sàng** cho compression.

### Tại sao đây là gap chiến lược?

Comparison report đã identify rõ: compression là một trong những nơi `Repomix` mạnh hơn nhất. Roadmap hiện tại không có bất kỳ milestone nào address điều này.

Nếu người dùng có repo 500k tokens:

- `Repomix --compress` → 150k tokens, paste vào Claude
- `ws-ctx-engine` với token budget 150k → cũng 150k tokens, nhưng **được chọn lọc thông minh hơn**

Kết hợp cả hai: retrieval selection (ws-ctx-engine's moat) + compression (chưa có) = sản phẩm mạnh nhất trong category.

### Đề xuất M6 — Compression Layer (sau M3, trước M5)

**Scope**: Thêm `--compress` flag. Khi enabled, sau khi file được selected bởi retrieval engine, apply AST-based signature extraction:

- Giữ: class signatures, function signatures, docstrings (optional), import statements
- Remove: function bodies (replace bằng `# ... implementation`)
- Target: 50-70% token reduction cho code files

**Implementation approach** (dùng Tree-sitter đã có):

```python
# Trong output formatter, sau khi file được selected:
if config.compress:
    content = extract_signatures(content, file_extension)
    # extract_signatures dùng tree_sitter_chunker đã có
    # chỉ emit: class_definition, function_definition signatures
    # replace body với "    ..." marker
```

**Estimate**: 3-5 ngày. ROI rất cao so với M5 (incremental indexing có ít user-visible impact hơn).

---

## 4. Vấn đề Thiếu: Remote Repository Support

Comparison report liệt kê remote repo support là gap so với Repomix. Roadmap không address điều này.

Đây không cần implement ngay — là long-term item. Nhưng nên được thêm vào roadmap dưới dạng "Future Milestone" để có strategic awareness.

**Minimum viable remote support**:

```bash
wsctx pack https://github.com/user/repo
wsctx pack github:user/repo --branch main
```

---

## 5. Vấn đề Nhỏ: Test Coverage Không Được Mention

Mỗi milestone làm thay đổi behavior (M2 thay matcher, M5 thay indexing flow) nhưng roadmap không nói gì về test coverage requirement.

**Minimum**: Mỗi milestone nên có acceptance criteria bao gồm:

- M1: `wsctx --help` không crash; `wsctx pack .` không crash với default config
- M2: Test file với `!negation` pattern được handled đúng; `**/*.py` pattern đúng behavior
- M3: `wsctx pack . --stdout --format xml` output valid XML to stdout
- M5: Modify một file, reindex, verify chỉ file đó được re-embedded (check log)

---

## 6. Revised Implementation Notes

### M2 — Pathspec (correction)

```python
# SỬA: Dùng GitIgnoreSpec thay vì PathSpec.from_lines
from pathspec import GitIgnoreSpec

# Trong _extract_gitignore_patterns():
def build_ignore_spec(patterns: list[str]) -> GitIgnoreSpec:
    return GitIgnoreSpec.from_lines(patterns)

# Trong _should_include_file():
def _should_include_file(path: str, spec: GitIgnoreSpec) -> bool:
    return not spec.match_file(path)
```

### M5 — FAISS IDMap pattern (addition)

```python
# Khi tạo/load FAISS index cho incremental support:
import faiss
import numpy as np

def create_incremental_index(dim: int) -> faiss.IndexIDMap:
    base = faiss.IndexFlatIP(dim)
    return faiss.IndexIDMap(base)

def add_chunks(index: faiss.IndexIDMap, embeddings: np.ndarray, chunk_ids: np.ndarray):
    index.add_with_ids(embeddings.astype(np.float32), chunk_ids.astype(np.int64))

def remove_chunks(index: faiss.IndexIDMap, chunk_ids: list[int]):
    id_selector = faiss.IDSelectorArray(np.array(chunk_ids, dtype=np.int64))
    index.remove_ids(id_selector)
```

---

## 7. Revised Milestone Plan

```
REVISED ORDER:

M1 — Hotfix + Config Quick Cleanup (1-2 ngày)
  ├── Fix _set_console_log_level crash
  ├── Sync __version__ via importlib.metadata
  ├── Fix README --changed-files inconsistency
  ├── Comment out aspirational config fields (M4 quick wins)
  └── Acceptance: wsctx pack . không crash

M2 — Ignore Semantics + Language Honesty (2-3 ngày)
  ├── Add pathspec>=0.12 dependency
  ├── Use GitIgnoreSpec (not PathSpec.from_lines)
  ├── Recursive .gitignore discovery
  ├── INDEXED_EXTENSIONS constant + WARNING emit
  └── Acceptance: negation patterns work; Java files warn

M3 — CLI UX + Output Polish (3-4 ngày)
  ├── Token count display post-pack/query
  ├── --stdout flag (loosen agent-mode restriction)
  ├── --copy clipboard flag
  ├── JSON Schema + MCP response schema docs
  └── Acceptance: wsctx pack . --stdout | head works

[NEW] M4 — Compression Layer (3-5 ngày)
  ├── --compress flag
  ├── Tree-sitter signature extraction
  ├── Replace function bodies with "..." marker
  ├── 40-70% token reduction target
  └── Acceptance: wsctx pack . --compress shows token savings

M5 — Config Cleanup (residual) (0.5-1 ngày)
  └── Remove/mark remaining aspirational fields in YAML

M6 — Incremental Indexing (5-7 ngày)
  ├── Migrate to IndexIDMap for FAISS
  ├── Add chunk embedding cache (content hash → vector)
  ├── Hash diff detection per file
  ├── Partial reparse + selective re-embed
  └── Acceptance: modify 1 file, reindex, only 1 file re-embedded
```

---

## 8. Đánh giá Chiến Lược Tổng Thể

### Điểm mạnh của roadmap hiện tại

1. **Priority ordering hoàn toàn đúng** — M1 unblocks mọi thứ
2. **Implementation notes đủ concrete** — có thể bắt tay implement ngay
3. **Scope từng milestone hợp lý** — không overcrowd
4. **Directory structure rõ ràng** — biết chính xác file nào cần touch

### Điểm yếu của roadmap hiện tại

1. **Không có compression milestone** — đây là lợi thế cạnh tranh quan trọng nhất bị bỏ qua
2. **Kỹ thuật pathspec sai class** (`PathSpec` vs `GitIgnoreSpec`)
3. **M5 FAISS IDMap pattern chưa được address** — sẽ gặp blocker khi implement
4. **`--stdout` restriction quá chặt** — sẽ limit pipe UX
5. **Không mention test acceptance criteria** cho từng milestone
6. **M4 không cần standalone** — gộp được, tiết kiệm 1 milestone

### Về Strategic Positioning

Roadmap v1 sẽ đưa project từ "broken Alpha" lên "functional Beta." Đây là cần thiết. Nhưng nó không di chuyển kim trên "differentiation" so với Repomix.

Sau khi xong 6 milestone revised, product story sẽ là:

> `ws-ctx-engine`: Intelligent context selector — retrieval-first với hybrid ranking, compression sau retrieval, agent-native MCP, và gitignore semantics chuẩn.

Đây là story mạnh hơn "Repomix clone tốt hơn" — và đúng với kiến trúc hiện tại của project.

---

## 9. Checklist Review trước khi implement

- [ ] Sửa pathspec implementation note: `GitIgnoreSpec` thay vì `PathSpec.from_lines('gitignore')`
- [ ] Thêm M4 (Compression) vào roadmap — đây là feature có ROI cao nhất
- [ ] Address FAISS IDMap pattern trong M5/M6 implementation notes
- [ ] Thêm embedding cache design vào M5/M6
- [ ] Loosen `--stdout` restriction trong M3
- [ ] Thêm acceptance criteria cho từng milestone
- [ ] Gộp config cleanup quick wins vào M1
- [ ] Clarify `--changed-files` flag status trong M1 scope
- [ ] Add LEANN incremental behavior note trong M5/M6
