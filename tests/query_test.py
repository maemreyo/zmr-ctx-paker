#!/usr/bin/env python3
"""
Query test script for ws-ctx-engine.

Tests real-world user queries to verify ws-ctx-engine can answer practical questions.
"""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class QueryTestRunner:
    """Run query tests with real user questions."""

    def __init__(self, output_dir: str = "tests/query_results"):
        """Initialize query test runner.

        Args:
            output_dir: Directory to store test results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_count = 0

    def run_query_test(
        self,
        test_name: str,
        repo_path: str,
        query: str,
        config_path: str = None,
        expected_files: List[str] = None
    ) -> Dict:
        """Run a query test.

        Args:
            test_name: Name of the test
            repo_path: Path to repository
            query: User query to test
            config_path: Path to config file (optional)
            expected_files: List of expected file paths in result (optional)

        Returns:
            Dictionary with test results
        """
        self.test_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"run_{self.test_count:03d}_{test_name}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*80}")
        print(f"Query Test #{self.test_count}: {test_name}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print(f"Repository: {repo_path}")
        if config_path:
            print(f"Config: {config_path}")
        print(f"{'='*80}\n")

        # Save test metadata
        test_metadata = {
            "test_number": self.test_count,
            "test_name": test_name,
            "query": query,
            "repo_path": repo_path,
            "config_path": config_path,
            "expected_files": expected_files,
            "timestamp": datetime.now().isoformat(),
            "run_dir": str(run_dir)
        }

        with open(run_dir / "test_metadata.json", "w") as f:
            json.dump(test_metadata, f, indent=2)

        # Build command
        cmd = [sys.executable, "-m", "ws_ctx_engine.cli", "query", query, "--repo", repo_path]
        if config_path:
            cmd.extend(["--config", config_path])

        # Run query
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            success = result.returncode == 0
            error_message = None
        except subprocess.TimeoutExpired:
            success = False
            error_message = "Query timed out after 2 minutes"
            result = None
        except Exception as e:
            success = False
            error_message = str(e)
            result = None

        # Save command output
        if result:
            with open(run_dir / "stdout.log", "w") as f:
                f.write(result.stdout)
            with open(run_dir / "stderr.log", "w") as f:
                f.write(result.stderr)

        # Extract and analyze output
        output_zip = Path("output/ws-ctx-engine.zip")
        actual_files = []
        review_context = None

        if output_zip.exists():
            # Copy output zip
            shutil.copy2(output_zip, run_dir / "ws-ctx-engine.zip")

            # Extract and analyze
            extract_dir = run_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(output_zip, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Get list of files
            files_dir = extract_dir / "files"
            if files_dir.exists():
                for file_path in files_dir.rglob("*"):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(files_dir)
                        actual_files.append(str(rel_path))

            # Read review context
            review_path = extract_dir / "REVIEW_CONTEXT.md"
            if review_path.exists():
                review_context = review_path.read_text()
                with open(run_dir / "REVIEW_CONTEXT.md", "w") as f:
                    f.write(review_context)

        # Copy latest log
        log_dir = Path(".ws-ctx-engine/logs")
        if log_dir.exists():
            log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
            if log_files:
                shutil.copy2(log_files[-1], run_dir / "ws-ctx-engine.log")

        # Analyze results
        files_match = None
        if expected_files:
            files_match = set(actual_files) == set(expected_files)

        test_result = {
            **test_metadata,
            "success": success,
            "error_message": error_message,
            "actual_files": actual_files,
            "files_count": len(actual_files),
            "files_match": files_match,
            "has_review_context": review_context is not None
        }

        # Save test results
        with open(run_dir / "test_results.json", "w") as f:
            json.dump(test_result, f, indent=2)

        # Print results
        print(f"\n{'='*80}")
        print(f"Query Test Results: {test_name}")
        print(f"{'='*80}")
        print(f"Status: {'✅ PASS' if success else '❌ FAIL'}")
        if error_message:
            print(f"Error: {error_message}")
        print(f"\nFiles returned: {len(actual_files)}")
        for f in actual_files:
            print(f"  - {f}")
        if expected_files:
            print(f"\nExpected files: {len(expected_files)}")
            for f in expected_files:
                status = "✅" if f in actual_files else "❌"
                print(f"  {status} {f}")
        print(f"\nArtifacts saved to: {run_dir}")
        print(f"{'='*80}\n")

        return test_result

    def generate_summary(self, results: List[Dict]):
        """Generate summary report."""
        summary_path = self.output_dir / "query_test_summary.md"

        with open(summary_path, "w") as f:
            f.write("# ws-ctx-engine Query Test Summary\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Tests**: {len(results)}\n")
            f.write(f"**Passed**: {sum(1 for r in results if r['success'])}\n")
            f.write(f"**Failed**: {sum(1 for r in results if not r['success'])}\n\n")

            f.write("## Test Results\n\n")
            f.write("| # | Test Name | Status | Files | Query |\n")
            f.write("|---|-----------|--------|-------|-------|\n")

            for r in results:
                status = "✅ PASS" if r['success'] else "❌ FAIL"
                query_short = r['query'][:50] + "..." if len(r['query']) > 50 else r['query']
                f.write(f"| {r['test_number']} | {r['test_name']} | {status} | {r['files_count']} | {query_short} |\n")

            f.write("\n## Detailed Results\n\n")
            for r in results:
                f.write(f"### Test #{r['test_number']}: {r['test_name']}\n\n")
                f.write(f"**Query**: {r['query']}\n\n")
                f.write(f"**Repository**: `{r['repo_path']}`\n\n")
                if r['config_path']:
                    f.write(f"**Config**: `{r['config_path']}`\n\n")
                f.write(f"**Status**: {'✅ PASS' if r['success'] else '❌ FAIL'}\n\n")
                if r['error_message']:
                    f.write(f"**Error**: {r['error_message']}\n\n")
                f.write(f"**Files Returned** ({r['files_count']}):\n")
                for file in r['actual_files']:
                    f.write(f"- `{file}`\n")
                f.write(f"\n**Artifacts**: `{r['run_dir']}`\n\n")
                f.write("---\n\n")

        print(f"\n📊 Summary report generated: {summary_path}\n")


def main():
    """Main entry point."""
    runner = QueryTestRunner()
    results = []

    print("\n" + "="*80)
    print("WS-CTX-ENGINE QUERY TEST SUITE")
    print("="*80)

    # Test 1: Voice management query (TS/JS only)
    results.append(runner.run_query_test(
        test_name="voice_management_ts_only",
        repo_path="examples/zmr-koe/source",
        config_path="examples/zmr-koe/config.yaml",
        query="How does voice management work? Show me the logic for managing voices",
        expected_files=["koe/src/lib/store.ts"]
    ))

    # Test 2: Voice management query (all languages)
    # First, create a config that includes Rust files
    all_langs_config = Path("tests/fixtures/all_langs_config.yaml")
    all_langs_config.parent.mkdir(parents=True, exist_ok=True)
    all_langs_config.write_text("""
token_budget: 50000
include_patterns:
  - "**/*.ts"
  - "**/*.js"
  - "**/*.rs"
exclude_patterns:
  - "**/node_modules/**"
  - "**/target/**"
  - "**/.git/**"
""")

    results.append(runner.run_query_test(
        test_name="voice_management_all_langs",
        repo_path="examples/zmr-koe/source",
        config_path=str(all_langs_config),
        query="How does voice management work? Show me the logic for managing voices",
        expected_files=["koe/src/lib/store.ts", "koe/src-tauri/src/voices.rs"]
    ))

    # Test 3: Specific technical query
    results.append(runner.run_query_test(
        test_name="tauri_invoke_pattern",
        repo_path="examples/zmr-koe/source",
        config_path="examples/zmr-koe/config.yaml",
        query="Show me how Tauri invoke is used to communicate between frontend and backend"
    ))

    # Test 4: Architecture query
    results.append(runner.run_query_test(
        test_name="state_management",
        repo_path="examples/zmr-koe/source",
        config_path="examples/zmr-koe/config.yaml",
        query="How is application state managed? Show me the state management pattern"
    ))

    # Generate summary
    runner.generate_summary(results)

    # Exit with appropriate code
    failed = sum(1 for r in results if not r['success'])
    if failed > 0:
        print(f"\n❌ {failed} test(s) failed\n")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} tests passed\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
