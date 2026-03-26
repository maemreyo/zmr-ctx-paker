# Performance Guide

ws-ctx-engine includes an optional Rust extension (`_rust/`) that accelerates
hot-path operations by 8–20x.

---

## Performance Targets

| Operation          | Python (current) | With Rust    | Speedup |
|--------------------|------------------|--------------|---------|
| File walk (10k)    | ~2–4 s           | < 200 ms     | 10–20x  |
| Gitignore matching | ~500 ms          | < 50 ms      | 8–12x   |
| Chunk hashing      | ~300 ms          | < 30 ms      | 8–10x   |
| Token counting     | ~1 s             | < 100 ms     | 8–12x   |

The Rust extension is **optional** — the engine falls back to Python
implementations automatically when the extension is not installed.

---

## Building the Rust Extension

Prerequisites: Rust toolchain (`rustup`) + `maturin`.

```bash
# Install maturin
pip install maturin

# Build in development mode (no wheel)
cd _rust && maturin develop --release

# Verify
python -c "from ws_ctx_engine._rust import walk_files; print('Rust OK')"
```

### Pre-built wheels

CI produces manylinux2014, macOS universal2, and Windows amd64 wheels on
every push to `main` that touches `_rust/`.  Download from GitHub Actions
artifacts or install from the future PyPI release.

---

## Benchmark Suite

```bash
# Run the benchmark script against a large repo
python scripts/benchmark.py --repo /path/to/large-repo

# Expected output for a 10k-file repo with Rust extension:
# File walk:  142 ms  (Python baseline: 2,400 ms)
# Full pack:  1.8 s   (Python baseline: 12 s)
```

---

## Rust Extension Architecture

The extension lives in `_rust/` and is built with [maturin](https://github.com/PyO3/maturin):

```
_rust/
├── Cargo.toml          — dependencies: pyo3, ignore, blake3, xxhash-rust, rayon
└── src/
    ├── lib.rs           — PyO3 module: registers walk_files, hash_content, count_tokens
    ├── walker.rs        — parallel file walker (ignore crate, respects .gitignore natively)
    ├── hasher.rs        — Blake3 / xxHash3 content hashing
    └── token_counter.rs — BPE-free token count approximation (±5% vs tiktoken)
```

The Python fallback chain in `chunker/base.py`:
```python
try:
    from ws_ctx_engine._rust import walk_files, hash_content, count_tokens
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Python fallbacks used instead
```
