# ws-ctx-engine Stress Tests

## Overview

Stress test suite for ws-ctx-engine that runs multiple test scenarios with detailed logging and artifact collection.

## Features

- **Clear test prompts**: Each test has a description of what it's testing
- **Detailed logging**: Each test run saves stdout, stderr, and ws-ctx-engine logs
- **Organized artifacts**: Each test run gets its own folder with all artifacts
- **Summary reports**: Automatic generation of markdown summary with all results

## Directory Structure

```
tests/
├── stress_test.py           # Main stress test script
├── fixtures/                # Test fixtures (generated)
└── stress_results/          # Test results (generated)
    ├── run_001_test_name_20260324_090000/
    │   ├── test_metadata.json      # Test configuration
    │   ├── test_results.json       # Test results
    │   ├── stdout.log              # Command stdout
    │   ├── stderr.log              # Command stderr
    │   ├── ws-ctx-engine.log      # ws-ctx-engine log
    │   └── artifacts/              # Copied artifacts
    │       ├── metadata.json       # Index metadata
    │       ├── vector.idx          # Vector index
    │       └── graph.pkl           # Graph index
    ├── run_002_test_name_20260324_090030/
    │   └── ...
    └── summary_report.md           # Summary of all tests
```

## Usage

### Run all tests
```bash
python tests/stress_test.py
```

### Run quick test suite (fewer tests)
```bash
python tests/stress_test.py --quick
```

### Specify custom output directory
```bash
python tests/stress_test.py --output-dir my_test_results
```

### Make script executable
```bash
chmod +x tests/stress_test.py
./tests/stress_test.py
```

## Test Scenarios

### 1. zmr-koe with default config
**Prompt**: Test zmr-koe repository with default configuration. Should extract functions from TypeScript/JavaScript files.

**Expected**:
- Files: 1
- Chunks: 6

### 2. zmr-koe with custom config
**Prompt**: Test zmr-koe repository with custom config (50k token budget, TS/JS focus). Should respect include/exclude patterns.

**Expected**:
- Files: 1
- Chunks: 6

### 3. Empty repository
**Prompt**: Test with empty repository. Should handle gracefully with no files.

**Expected**:
- Files: 0
- Chunks: 0

### 4. Config files only
**Prompt**: Test with only config files (no functions/classes). Should scan files but extract 0 chunks.

**Expected**:
- Files: 0
- Chunks: 0

### 5. Large file stress test
**Prompt**: Test with large file containing 1000 functions. Should handle large files efficiently.

**Expected**:
- Files: 1
- Chunks: 1000

## Output Files

### test_metadata.json
Contains test configuration and parameters:
```json
{
  "test_number": 1,
  "test_name": "zmr-koe_default",
  "prompt": "Test description...",
  "repo_path": "examples/zmr-koe/source",
  "config_path": null,
  "expected_files": 1,
  "expected_chunks": 6,
  "timestamp": "2026-03-24T09:00:00",
  "run_dir": "tests/stress_results/run_001_..."
}
```

### test_results.json
Contains test execution results:
```json
{
  "success": true,
  "duration": 8.43,
  "error_message": null,
  "actual_files": 1,
  "actual_chunks": 6,
  "files_match": true,
  "chunks_match": true
}
```

### Logs
- `stdout.log`: Standard output from ws-ctx-engine command
- `stderr.log`: Standard error from ws-ctx-engine command
- `ws-ctx-engine.log`: Detailed ws-ctx-engine internal logs

### Artifacts
- `metadata.json`: Index metadata (file count, backend, hashes)
- `vector.idx`: Vector index file
- `graph.pkl`: Graph index file

## Summary Report

After all tests complete, a `summary_report.md` is generated with:
- Overall pass/fail statistics
- Table of all test results
- Detailed information for each test
- Links to artifact directories

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

## Adding New Tests

To add a new test scenario, add a call to `runner.run_test()` in `main()`:

```python
results.append(runner.run_test(
    test_name="my_new_test",
    repo_path="path/to/repo",
    config_path="path/to/config.yaml",  # optional
    prompt="Description of what this test checks",
    expected_files=5,
    expected_chunks=20
))
```

## Tips

1. **Review artifacts**: Each test run folder contains all artifacts for debugging
2. **Check logs**: Look at `ws-ctx-engine.log` for detailed execution info
3. **Compare runs**: Use different output directories to compare test runs
4. **CI/CD integration**: Script exits with code 1 on failure for CI/CD pipelines

## Requirements

- Python 3.8+
- ws-ctx-engine installed and in PATH
- Write access to tests/ directory
