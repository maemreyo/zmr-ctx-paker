#!/usr/bin/env python3
"""Test pattern matching."""

import fnmatch
from pathlib import Path

# When run from the root of the repo
repo_root = Path("examples/zmr-koe/source")

include_patterns = ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.json", "**/*.md"]

exclude_patterns = [
    "*.min.js",
    "*.min.css",
    "node_modules/**",
    "dist/**",
    "build/**",
    ".next/**",
    "coverage/**",
    "*.test.ts",
    "*.test.js",
    "*.spec.ts",
    "*.spec.js",
]

# Find all TS/JS files
for ext in [".ts", ".tsx", ".js", ".jsx"]:
    for file_path in repo_root.rglob(f"*{ext}"):
        if not file_path.is_file():
            continue

        relative_path = str(file_path.relative_to(repo_root))
        print(f"\nFile: {relative_path}")

        # Check exclude
        excluded = False
        for pattern in exclude_patterns:
            if (
                fnmatch.fnmatch(relative_path, pattern)
                or fnmatch.fnmatch(relative_path, pattern.replace("**/", "*/"))
                or fnmatch.fnmatch(relative_path, pattern.replace("**", "*"))
            ):
                print(f"  ✗ EXCLUDED by: {pattern}")
                excluded = True
                break

        if excluded:
            continue

        # Check include
        included = False
        for pattern in include_patterns:
            if (
                fnmatch.fnmatch(relative_path, pattern)
                or fnmatch.fnmatch(relative_path, pattern.replace("**/", "*/"))
                or fnmatch.fnmatch(relative_path, pattern.replace("**", "*"))
            ):
                print(f"  ✓ INCLUDED by: {pattern}")
                included = True
                break

        if not included:
            print("  ✗ NOT MATCHED by any include pattern")
