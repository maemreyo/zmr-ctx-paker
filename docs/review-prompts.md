# Code Review Prompts for zmr-ctx-paker

## Example Query Prompts (for testing ws-ctx-engine on itself)

| # | ID | Prompt |
|---|-----|--------|
| 1 | `chunking_flow` | "Show me the chunking logic flow from entry point to output in the chunker module" |
| 2 | `python_resolver` | "Show me how PythonResolver extracts function and class definitions" |
| 3 | `js_resolver` | "Show me how JavaScriptResolver handles JSX elements and exports" |
| 4 | `ts_resolver` | "Show me how TypeScriptResolver handles interfaces and type aliases" |
| 5 | `rust_resolver` | "Show me how RustResolver handles impl blocks and macro definitions" |
| 6 | `symbol_extraction` | "Show me how symbols_defined and symbols_referenced are collected" |
| 7 | `file_filtering` | "Show me how _should_include_file works with include/exclude patterns" |
| 8 | `fallback_regex` | "Show me when RegexChunker is used as fallback and how it parses" |
| 9 | `markdown_chunker` | "Show me how MarkdownChunker splits content by headings" |
| 10 | `tree_sitter_parse` | "Show me how TreeSitterChunker parses files and extracts definitions" |

### Running the test script

```bash
cd /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker
chmod +x examples/ws-ctx-engine-self/run_self_tests.sh
./examples/ws-ctx-engine-self/run_self_tests.sh
```

---

## Chunking System

### 1. Chunking Logic Flow
```
Show me the chunking logic flow from entry point to output
```

```
Show me how TreeSitterChunker parses a file and extracts definitions
```

```
Show me how LanguageResolver.extract_symbol_name works for each language
```

```
Show me how symbols_referenced is collected in each resolver
```

---

## Language-Specific Parsing

### 2. PythonResolver
```
Show me the PythonResolver - how it extracts function/class definitions
```

### 3. JavaScriptResolver
```
Show me the JavaScriptResolver - how it handles JSX and exports
```

### 4. TypeScriptResolver
```
Show me the TypeScriptResolver - how it handles interfaces and types
```

### 5. RustResolver
```
Show me the RustResolver - how it handles impl blocks and macros
```

---

## Fallback & Edge Cases

### 6. RegexChunker
```
Show me when RegexChunker is used as fallback
```

```
Show me how _brace_matching_end works in RegexChunker
```

### 7. MarkdownChunker
```
Show me how MarkdownChunker splits content by headings
```

### 8. File Filtering
```
Show me how _should_include_file works with patterns
```

---

## Data Models

### 9. CodeChunk Model
```
Show me the CodeChunk model and its fields
```

### 10. Symbol Extraction
```
Show me how extract_references vs extract_symbols_defined differs
```

---

## Testing & Coverage

### 11. Test Structure
```
Show me the test structure for chunkers
```

```
Show me the uncovered edge cases in regex.py
```

### 12. Integration Tests
```
Show me how tree_sitter_chunker tests verify file-level imports
```

---

## Architecture

### 13. Module Structure
```
Show me all modules in the chunker package and their responsibilities
```

### 14. Entry Points
```
Show me how Chunker.parse() decides which chunker to use
```

---

## Quick Verification Commands

```bash
# Run all chunker tests
cd /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker && python3 -m pytest tests/unit/test_resolvers.py tests/unit/test_tree_sitter_chunker.py -v

# Run coverage for chunker
cd /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker && python3 -m pytest tests/unit/ --ignore=tests/unit/test_cli.py --cov=src/ws_ctx_engine/chunker --cov-report=term

# Run full test suite
cd /Users/trung.ngo/Documents/zaob-dev/zmr-ctx-paker && python3 -m pytest tests/unit/ --ignore=tests/unit/test_cli.py -v
```
