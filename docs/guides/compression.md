# Compression Guide

ws-ctx-engine provides two complementary features to reduce token usage and
improve model recall quality: **smart compression** and **context shuffling**.

---

## Smart Compression (`--compress`)

Enabled with `wsctx pack . --compress` or `wsctx query "..." --compress`.

Unlike Repomix's `--compress` which applies uniform compression to every file,
ws-ctx-engine applies **relevance-aware compression**:

| Relevance score | Content kept | Token savings |
|-----------------|--------------|---------------|
| ≥ 0.6 (high)    | Full content | 0% |
| 0.3–0.6 (medium) | Signatures only | ~70% |
| < 0.3 (low)     | Signatures + docstrings | ~85% |

### Marker format

Compressed function bodies are replaced with:

```python
# ... implementation
```

This marker is consistent with Python convention and is also used for
TypeScript, JavaScript, and Rust.

### Language support

| Language | Parser | Fallback |
|----------|--------|---------|
| Python | Tree-sitter (preferred) | Regex |
| TypeScript / JavaScript | Tree-sitter (preferred) | Regex |
| Rust | Tree-sitter | — |

### Example

```bash
wsctx pack . --compress
# ✓ Context packed with compression: 127,450 → 41,200 tokens (67% reduction)

wsctx pack . --compress --stdout | xmllint --noout -  # valid XML
wsctx pack . --compress --format json --stdout | python -m json.tool
```

---

## Context Shuffling (`--shuffle` / `--no-shuffle`)

Addresses the **"Lost in the Middle"** problem (Liu et al., 2023):

> LLMs recall information near the **start** and **end** of their context
> window significantly better than information in the **middle**.

ws-ctx-engine reorders files so that the highest-ranked files appear at
**both** ends of the output:

```
[TOP]    → Files rank 1, 2, 3       (highest relevance — best recall)
[MIDDLE] → Files rank 4..N-3        (supporting context)
[BOTTOM] → Files rank N-2, N-1, N   (2nd highest relevance — still good recall)
```

### Defaults

- **Agent mode** (`--agent-mode`): shuffle is ON by default.
- **Stdout-only mode**: shuffle is OFF by default.
- Override with `--shuffle` or `--no-shuffle`.

### Example

```bash
wsctx pack . --agent-mode --query "auth"   # shuffle ON (default in agent mode)
wsctx pack . --no-shuffle --stdout         # shuffle OFF
```

---

## Combined Usage

```bash
wsctx pack . --compress --query "fix auth bug"
# → High-relevance auth files: full content
# → Supporting files: signatures only
# → Highest-ranked files at top + bottom of XML output
```
