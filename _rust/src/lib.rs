/// ws_ctx_engine Rust extension — PyO3 module entrypoint.
///
/// Exposes fast hot-path functions to Python:
///   - walk_files(root, ignore_patterns) → list[str]
///   - hash_content(text)               → str
///   - count_tokens(text)               → int   (tiktoken-rs approximation)
///
/// All functions have Python fallbacks in chunker/base.py so this module is
/// purely optional — the engine works without it.
use pyo3::prelude::*;

mod hasher;
mod token_counter;
mod walker;

#[pymodule]
fn _rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(walker::walk_files, m)?)?;
    m.add_function(wrap_pyfunction!(hasher::hash_content, m)?)?;
    m.add_function(wrap_pyfunction!(token_counter::count_tokens, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
