# Chunking Strategy — Research Verdict

**Date**: March 27, 2026  
**Scope**: External validation of hybrid astchunk + tree-sitter approach  
**Status**: ✅ Confirmed — Strategy aligned with current research consensus

---

## TL;DR

Hybrid strategy (astchunk primary + tree-sitter fallback) là **best-practice được peer-review xác nhận**. Không cần thay đổi kiến trúc core.

---

## Evidence Summary

### 1. cAST Paper — Peer-Reviewed Validation (EMNLP 2025)

Paper gốc của astchunk ([arXiv:2506.15655](https://arxiv.org/abs/2506.15655), Carnegie Mellon University) được chấp nhận tại **EMNLP 2025 Findings** — hội nghị NLP hàng đầu. Kết quả thực nghiệm:

| Benchmark     | Metric   | Improvement      |
| ------------- | -------- | ---------------- |
| RepoEval      | Recall@5 | **+4.3 points**  |
| CrossCodeEval | Recall@5 | **+5.5 points**  |
| SWE-bench     | Pass@1   | **+2.67 points** |

Thuật toán cAST theo 4 mục tiêu thiết kế: syntactic integrity, high information density, language invariance, plug-and-play compatibility — khớp hoàn toàn với yêu cầu của ws-ctx-engine.

> **Implication**: Baseline metric trong report (+4.3/+5.5 Recall@5) có nguồn gốc xác thực từ peer-reviewed research, không phải vendor claim.

---

### 2. Tree-Sitter Fallback — Battle-Tested Foundation

Tree-sitter là parser được sử dụng bởi Neovim, Helix, Zed editors. Đây là lựa chọn standard trong industry cho AST parsing đa ngôn ngữ. Việc dùng làm fallback cho Rust/Go là đúng hướng — chính paper cAST cũng build trên tree-sitter làm parsing backend.

> **Implication**: Fallback path không phải workaround mà là kiến trúc chính thống.

---

### 3. Non-Whitespace Character Count — Đúng Metric

Research xác nhận đây là chunk size metric đúng cho code: hai đoạn code cùng số dòng có thể chứa lượng nội dung khác nhau hoàn toàn (import statement vs class body). Line-count hoặc raw character-count đều cho kết quả không nhất quán.

---

### 4. Chonkie cho Markdown — Hợp Lý Nhưng Optional

Chonkie benchmarks: **33x faster** token chunking, **2x faster** sentence chunking so với các thư viện RAG khác. Tuy nhiên Chonkie là **text-only** — không có khả năng parse code structure. Việc report đề xuất dùng Chonkie chỉ cho `.md`/`.txt` (P3) là phân tách đúng concern.

---

## Risks Identified (External Research)

**1. RAG-for-code critique (emerging)**  
Một số practitioner trong industry (Cline, 2025) lập luận rằng RAG chia code thành isolated chunks có thể miss architectural context (import chains, dependency graphs) — đây là điểm mà graph-based approaches như Aider's repo-map xử lý tốt hơn. Với ws-ctx-engine, astchunk's metadata (scope, symbols, filepath) giảm thiểu một phần rủi ro này, nhưng cần lưu ý nếu use case mở rộng sang cross-file reasoning.

**2. astchunk language coverage gap**  
Rust, Go không được astchunk support trực tiếp — tree-sitter fallback hiện tại là giải pháp đúng, nhưng chất lượng chunk phụ thuộc vào custom resolver implementation. Cần benchmark riêng cho Rust/Go so với Python/TypeScript baseline.

---

## Verdict

| Aspect                      | Assessment                                       |
| --------------------------- | ------------------------------------------------ |
| Core algorithm (cAST)       | ✅ Research-validated, EMNLP 2025                |
| Primary tool (astchunk)     | ✅ Official implementation của paper             |
| Fallback (tree-sitter)      | ✅ Industry standard                             |
| Chunk size metric           | ✅ Non-whitespace char count — confirmed correct |
| Markdown handling (Chonkie) | ✅ Justified — best-in-class for text            |
| Language coverage gap       | ⚠️ Rust/Go resolver quality cần benchmark riêng  |
| Cross-file context          | ⚠️ Monitor nếu scale lên graph-level reasoning   |

**Recommendation**: Proceed with current hybrid strategy. No architectural changes needed. Add Rust/Go resolver benchmarks vào Phase 2 success criteria.

---

## References

- Zhang et al., _cAST: Enhancing Code RAG with Structural Chunking via AST_, EMNLP 2025 Findings — [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.430/) | [arXiv](https://arxiv.org/abs/2506.15655)
- Chonkie benchmarks — [github.com/chonkie-inc/chonkie](https://github.com/chonkie-inc/chonkie/blob/main/BENCHMARKS.md)
- Supermemory, _Building code-chunk: AST Aware Code Chunking_ (Dec 2025) — [supermemory.ai](https://supermemory.ai/blog/building-code-chunk-ast-aware-code-chunking/)
- _An Exploratory Study of Code Retrieval Techniques in Coding Agents_, Preprints.org (Oct 2025)
