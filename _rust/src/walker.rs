/// Fast parallel file walker using the `ignore` crate.
///
/// The `ignore` crate respects `.gitignore`, `.ignore`, and `.git/info/exclude`
/// natively — giving correct Git semantics without needing pathspec.
use pyo3::prelude::*;
use ignore::WalkBuilder;
use rayon::prelude::*;

/// Walk *root* respecting gitignore rules and return relative file paths.
///
/// Args:
///     root:            Repository root directory.
///     respect_hidden:  If True, skip hidden files and directories.
///
/// Returns:
///     List of relative POSIX paths (sorted for determinism).
#[pyfunction]
#[pyo3(signature = (root, respect_hidden = true))]
pub fn walk_files(root: &str, respect_hidden: bool) -> PyResult<Vec<String>> {
    let walker = WalkBuilder::new(root)
        .hidden(respect_hidden)
        .git_ignore(true)
        .git_global(true)
        .git_exclude(true)
        .build_parallel();

    use std::sync::{Arc, Mutex};
    let results: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));
    let root_path = std::path::Path::new(root);
    let results_clone = Arc::clone(&results);

    walker.run(move || {
        let results = Arc::clone(&results_clone);
        Box::new(move |result| {
            if let Ok(entry) = result {
                if entry.file_type().map(|ft| ft.is_file()).unwrap_or(false) {
                    if let Ok(rel) = entry.path().strip_prefix(root_path) {
                        let s = rel.to_string_lossy().replace('\\', "/");
                        results.lock().unwrap().push(s);
                    }
                }
            }
            ignore::WalkState::Continue
        })
    });

    let mut paths = Arc::try_unwrap(results)
        .unwrap()
        .into_inner()
        .unwrap();
    paths.sort_unstable();
    Ok(paths)
}
