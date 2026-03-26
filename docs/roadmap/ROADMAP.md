# ROADMAP — ws-ctx-engine

> Version: current `v0.2.0a0`
> Cập nhật: 2026-03-26

---

## Trạng thái hiện tại

**v0.2.0a0 — Alpha.** Core pipeline hoàn chỉnh và có thể sử dụng. Các tính năng agent-native đã implement nhưng chưa được verify end-to-end trên real repos.

### Đã implement (✓)

| Module                                                                       | Tình trạng     | Ghi chú                                                            |
| ---------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------ |
| 6-stage pipeline (chunker → vector → graph → retrieval → budget → packer)    | ✓ Stable       | Fallback ở mọi tầng                                                |
| Hybrid ranking (semantic + PageRank + symbol + path + domain + test penalty) | ✓ Stable       |                                                                    |
| Query classification (symbol / path-dominant / semantic-dominant)            | ✓ Stable       |                                                                    |
| Output formats: XML, ZIP, JSON, YAML, Markdown                               | ✓ Stable       |                                                                    |
| Output format: TOON                                                          | ✓ Experimental | Chưa benchmark                                                     |
| Smart compression (relevance-aware, Tree-sitter + regex fallback)            | ✓ Stable       | Python/JS/TS/Rust                                                  |
| Context shuffling (shuffle_for_model_recall)                                 | ✓ Stable       | combat Lost-in-the-Middle                                          |
| AI rule persistence (`.cursorrules`, `CLAUDE.md`, etc.)                      | ✓ Stable       | boost = 10.0                                                       |
| Session deduplication (hash cache, `--session-id`)                           | ✓ Stable       |                                                                    |
| Phase-aware ranking (`--mode discovery/edit/test`)                           | ✓ Implemented  | Chưa có E2E test                                                   |
| Secret scanner (regex + secretlint, mtime cache)                             | ✓ Stable       |                                                                    |
| MCP server (stdio, path guard, rate limiter, RADE)                           | ✓ Stable       |                                                                    |
| Embedding cache                                                              | ✓ Implemented  | Chưa expose qua config                                             |
| GitIgnoreSpec (full git semantics, recursive .gitignore)                     | ✓ Stable       | pathspec>=0.12                                                     |
| Incremental indexing flag (`--incremental`)                                  | ⚠️ Partial     | IndexIDMap2 migration helper có nhưng chưa integrated vào workflow |
| FAISS IndexIDMap2                                                            | ⚠️ Partial     | migrate_to_id_map2() có nhưng không phải default                   |
| Rust extension                                                               | ✗ Not started  | pyproject.toml comment only                                        |

### Gap còn lại

1. **Incremental indexing** chưa hoạt động end-to-end — flag tồn tại nhưng workflow chưa dùng `IndexIDMap2` as default
2. **Embedding cache** chưa được expose qua `.ws-ctx-engine.yaml`
3. **Phase ranker** chưa có integration test — behavior của mỗi mode chưa được verify với real queries
4. **TOON format** chưa có benchmark — không biết thực sự tiết kiệm bao nhiêu tokens
5. **MCP tool coverage** hạn chế — chỉ có `search_codebase`, thiếu `pack_context`, `index_status`, `session_clear`
6. **Streaming output** chưa có — toàn bộ pack built in-memory trước khi write
7. **Compression coverage** thiếu Go và Java

---

## Milestones

---

### v0.3.0 — Beta Stabilization

**Mục tiêu**: Từ Alpha → Beta. Không thêm tính năng mới, chỉ làm cho các tính năng đã có hoạt động đúng và có thể tin cậy được.

**Scope:**

#### 1. Incremental indexing — complete the implementation

Flag `--incremental` hiện tại là no-op với FAISS backend. Cần:

- Dùng `IndexIDMap2` làm default khi create FAISS index (không phải `IndexHNSWFlat`)
- Wire `migrate_to_id_map2()` vào `index_repository()` workflow
- Verify embedding cache được sử dụng trong incremental path (load `.npy` → skip embed nếu hash hit)
- Test: re-index chỉ modified files, delete files biến mất khỏi results

```bash
# Acceptance
wsctx index .
touch src/foo.py && wsctx index . --incremental  # log: only foo.py re-embedded
rm src/bar.py && wsctx index . --incremental     # bar.py absent từ search
```

#### 2. Embedding cache — expose via config

```yaml
# .ws-ctx-engine.yaml
performance:
  cache_embeddings: true # currently ignored — activate this
```

Cần: `index_repository()` đọc flag này, load/save `.ws-ctx-engine/embeddings.npy` + `embedding_index.json` theo đúng C4 pattern.

#### 3. Phase ranker — integration tests

`phase_ranker.py` tồn tại nhưng chưa có test verify behavior khác nhau giữa modes. Cần:

- Test: `--mode discovery` → output nhỏ hơn `--mode edit` với cùng query
- Test: `--mode test` → test files rank cao hơn source files
- Test: `--mode edit` → verbatim code, ít compression markers hơn discovery

#### 4. TOON format — benchmark và quyết định

Đo token count thực tế (tiktoken) so sánh TOON vs XML vs YAML trên 3 repos thực:

```bash
wsctx pack . --format xml  | python -c "import tiktoken; ..."   # baseline
wsctx pack . --format toon | python -c "import tiktoken; ..."   # TOON
```

Nếu savings < 10% → deprecate TOON, giữ XML/YAML/JSON/MD.
Nếu savings ≥ 15% → promote TOON lên stable, thêm vào docs.

#### 5. MCP tool expansion

Thêm 3 tools còn thiếu vào MCP server:

| Tool            | Mô tả                                              |
| --------------- | -------------------------------------------------- |
| `pack_context`  | Chạy query_and_pack(), trả nội dung hoặc path      |
| `index_status`  | Trả trạng thái index (stale, file count, built_at) |
| `session_clear` | Xóa session cache cho session_id                   |

#### 6. Config cleanup

Các fields trong `.ws-ctx-engine.yaml.example` đang annotated `# PLANNED` hoặc `# NOT YET IMPLEMENTED`:

- Audit xem field nào đã được implement thực sự
- Những gì vẫn là aspirational: move sang section riêng `experimental:` hoặc xóa
- `cache_embeddings` và `incremental_index` sau khi implement ở #1 và #2 → remove annotation

**Files thay đổi (v0.3.0):**

- `src/ws_ctx_engine/vector_index/vector_index.py` — `IndexIDMap2` as default
- `src/ws_ctx_engine/workflow/indexer.py` — wire incremental + embedding cache
- `src/ws_ctx_engine/mcp/tools.py` — add `pack_context`, `index_status`, `session_clear`
- `src/ws_ctx_engine/config/config.py` — activate `cache_embeddings`
- `tests/unit/test_phase_ranker.py` — integration behavior tests
- `tests/integration/` — incremental indexing end-to-end
- `.ws-ctx-engine.yaml.example` — config cleanup

**Estimate**: 5–7 ngày

---

### v0.4.0 — Scale

**Mục tiêu**: Hoạt động tốt với repos > 10k files. Hiện tại Python engine quá chậm ở file walk và token counting trên repos lớn.

**Scope:**

#### 1. Streaming output

Hiện tại toàn bộ pack được build in-memory rồi mới write. Với budget 200k tokens (~800KB text), peak memory có thể là vấn đề. Cần:

- `XMLPacker.pack_stream()` → write từng `<file>` block ra file object ngay thay vì buffer
- `--stdout` + streaming tương thích nhau

#### 2. Rust extension — hot paths (optional, `pip install ws-ctx-engine[fast-rust]`)

Các hot paths đáng Rust nhất:

| Path                                 | Python hiện tại | Target |
| ------------------------------------ | --------------- | ------ |
| File walk (10k files)                | ~2–4s           | <200ms |
| Content hashing (blake3 thay sha256) | ~300ms          | <30ms  |
| Token counting (tiktoken-rs)         | ~1s             | <100ms |

Dùng PyO3. Rust extension là **optional** — Python fallback khi không có:

```python
try:
    from ws_ctx_engine._rust import walk_files, hash_content, count_tokens
except ImportError:
    pass  # Python fallback
```

CI: manylinux wheels + macOS universal2 + Windows via maturin.

#### 3. Multi-language compression

Extend `output/compressor.py` thêm:

| Language | Node types cần strip                         |
| -------- | -------------------------------------------- |
| Go       | `function_declaration`, `method_declaration` |
| Java     | `method_declaration`, `class_declaration`    |
| C/C++    | `function_definition`                        |

**Estimate**: 8–12 ngày (7–10 ngày nếu bỏ Rust)

---

### v0.5.0 — Agent Platform

**Mục tiêu**: Trở thành engine tiêu chuẩn cho AI agents, không chỉ là CLI tool.

**Scope:**

#### 1. Chunk-level selection (Advanced RAG)

Chuyển từ file-level sang chunk-level selection:

```
Current:  [query] → [file ranking] → [file content]
Target:   [query] → [chunk ranking] → [cross-file symbol graph] → [minimal context]
```

Yêu cầu: chunk-level FAISS index riêng, cross-file symbol tracking, cross-chunk dependency graph. Đây là leap lớn nhất về kiến trúc.

#### 2. Remote repository support

```bash
wsctx pack https://github.com/user/repo -q "auth logic"
wsctx pack github:user/repo --branch main
```

Cần: shallow clone, trust/sandbox config, cache remote index.

#### 3. Watch mode

```bash
wsctx watch . -q "auth" --on-change pack   # Re-pack khi files thay đổi
```

Dùng `watchfiles` hoặc `fsevents`. Kết hợp với incremental indexing (v0.3.0) để re-index nhanh.

**Estimate**: TBD — architecture-heavy

---

### v1.0.0 — Production Ready

- Stable public API (không breaking changes without major version bump)
- Performance SLAs documented và enforced bằng benchmark CI
- Full language coverage cho compression (Python, JS, TS, Rust, Go, Java, C/C++)
- MCP 2.0 protocol support (nếu có)
- Comprehensive integration test suite với real-world repos

---

## Timeline

| Version    | Nội dung                                          | Estimate  | Status       |
| ---------- | ------------------------------------------------- | --------- | ------------ |
| **v0.2.0** | Core pipeline + agent features                    | Done      | ✓ Alpha      |
| **v0.3.0** | Beta stabilization                                | 5–7 ngày  | 🔵 Next      |
| **v0.4.0** | Scale (streaming + Rust + multi-lang compression) | 8–12 ngày | ⬜ Planned   |
| **v0.5.0** | Agent platform (chunk-level + remote + watch)     | TBD       | ⬜ Planned   |
| **v1.0.0** | Production ready                                  | TBD       | ⬜ Long-term |

---

## Nguyên tắc prioritization

1. **Fix trước, feature sau** — Không thêm tính năng mới khi tính năng đang có chưa hoạt động đúng (v0.3.0 trước v0.4.0)
2. **Benchmark trước khi quảng cáo** — TOON, compression savings, Rust speedup đều phải có số thực trước khi đưa vào README/docs
3. **Fallback ở mọi tầng** — Rust extension, LEANN, igraph đều optional. Engine không được crash khi thiếu bất kỳ dependency nào
4. **Agent-first** — Mọi tính năng mới đều cần MCP tool tương ứng (không chỉ CLI flag)
