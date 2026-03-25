# ws-ctx-engine: Chunker Issues & Improvement Report

**Date:** 2026-03-24
**Component:** `src/ws_ctx_engine/chunker.py`

This report summarizes critical issues found during the evaluation of the context extraction logic, specifically regarding missing file types and limitations in the custom chunker implementations.

---

## 1. Missing Support for Markdown (`.md`) Files
Currently, `.md` files are completely ignored by the system, even if explicitly defined in the `include_patterns` of `config.yaml`.

**Root Cause:**
- In `chunker.py`, the `ext_to_lang` dictionary hardcodes supported file extensions (`.py`, `.js`, `.ts`, etc.).
- The `parse()` method loops *only* over `self.ext_to_lang.keys()`. Since `.md` is not in this dictionary, the recursive glob search (`rglob`) never looks for them.
- Tree-sitter is designed for programming languages (AST nodes like functions/classes), making it incompatible with standard markdown structures out-of-the-box.

**Recommended Action:**
- Introduce a new `MarkdownChunker` (or `TextChunker`) that splits files based on Markdown headings (`#`, `##`) instead of AST nodes.
- Update the file traversal logic to support plain text / markdown extensions outside of the Tree-sitter dictionary.

---

## 2. Evaluation of Custom Chunkers

The dual-chunker architecture (TreeSitter as Primary, Regex as Fallback) is well-designed but requires refinement to be production-ready.

### A. TreeSitterChunker (Primary)
**Status:** Good, but misses global context.
- **Pros:** Highly accurate. Extracts references (imports, calls) perfectly, which is crucial for building the `RepoMapGraph` and calculating PageRank.
- **Cons:** The node targeting is too narrow. It currently only captures `function_definition` and `class_declaration`.
- **Recommended Action:** Expand AST target types to capture module-level constants, TypeScript Interfaces/Types, and Rust Structs/Enums globally.

### B. RegexChunker (Fallback)
**Status:** Fragile, high risk of data loss.
- **Pros:** Lightweight, no external C-bindings required.
- **Cons:** 
  1. **Truncation Risk:** The `_estimate_end_line` heuristic is dangerously simple. It looks ahead for the next definition, and if not found, forcefully caps the chunk at **20 lines** (`return min(start_line + 20, len(lines))`). Functions longer than 20 lines are silently truncated.
  2. **No Graph Support:** It hardcodes `symbols_referenced=[]`. When fallback occurs, the PageRank algorithm becomes "blind" because no dependencies are tracked.
- **Recommended Action:** 
  - Replace the 20-line heuristic with a bracket-matching algorithm (counting `{` and `}`) to accurately find the end of blocks.
  - Add basic Regex to detect `import` statements so the RepoMapGraph doesn't break entirely during fallback.
