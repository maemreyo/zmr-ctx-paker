/// Content hashing utilities — Blake3 for large inputs, xxHash3 for small ones.
///
/// Blake3 is ~10x faster than SHA-256 on modern hardware and produces a
/// 256-bit hex digest, which is suitable for change detection in the
/// incremental indexing pipeline.
use pyo3::prelude::*;

/// Compute a Blake3 hex digest of *content*.
///
/// ~10x faster than hashlib.sha256 for file-sized inputs.
/// Drop-in replacement for the SHA-256 hashes stored in IndexMetadata.
#[pyfunction]
pub fn hash_content(content: &str) -> String {
    let hash = blake3::hash(content.as_bytes());
    hash.to_hex().to_string()
}

/// Compute an xxHash3 (128-bit) hex digest of *content*.
///
/// Even faster than Blake3 for small strings (< 4 KB).
#[pyfunction]
pub fn hash_content_fast(content: &str) -> String {
    use xxhash_rust::xxh3::xxh3_128;
    let hash = xxh3_128(content.as_bytes());
    format!("{:032x}", hash)
}
