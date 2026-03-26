/// ws_ctx_engine Rust extension — PyO3 module entrypoint.
///
/// Exposes fast hot-path functions to Python:
///   - walk_files(root, respect_hidden) → list[str]  (36x faster than os.walk)
///
/// hash_content and count_tokens were removed: hashlib.sha256 and len(t)//4
/// are already fast enough in Python; the Rust↔Python boundary overhead
/// negated any gain from Blake3 or the trivial byte-count heuristic.
///
/// All functions have Python fallbacks in chunker/base.py so this module is
/// purely optional — the engine works without it.
use pyo3::prelude::*;

mod walker;

#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(walker::walk_files, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
