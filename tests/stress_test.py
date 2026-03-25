#!/usr/bin/env python3
"""
Stress test script for ws-ctx-engine.

This script runs multiple test scenarios with different configurations
and repositories, logging detailed results for each test run.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class StressTestRunner:
    """Run stress tests on ws-ctx-engine with detailed logging."""

    def __init__(self, output_dir: str = "tests/stress_results"):
        """Initialize stress test runner.

        Args:
            output_dir: Directory to store test results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_count = 0

    def create_test_run_dir(self, test_name: str) -> Path:
        """Create a directory for a specific test run.

        Args:
            test_name: Name of the test

        Returns:
            Path to the test run directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_count += 1
        run_dir = self.output_dir / f"run_{self.test_count:03d}_{test_name}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def run_test(
        self,
        test_name: str,
        repo_path: str,
        config_path: Optional[str] = None,
        prompt: str = "",
        expected_files: Optional[int] = None,
        expected_chunks: Optional[int] = None
    ) -> Dict:
        """Run a single test scenario.

        Args:
            test_name: Name of the test
            repo_path: Path to repository to test
            config_path: Path to config file (optional)
            prompt: Description of what this test is checking
            expected_files: Expected number of files (optional)
            expected_chunks: Expected number of chunks (optional)

        Returns:
            Dictionary with test results
        """
        print(f"\n{'='*80}")
        print(f"Test #{self.test_count + 1}: {test_name}")
        print(f"{'='*80}")
        print(f"Prompt: {prompt}")
        print(f"Repository: {repo_path}")
        if config_path:
            print(f"Config: {config_path}")
        print(f"{'='*80}\n")

        # Create test run directory
        run_dir = self.create_test_run_dir(test_name)

        # Prepare test metadata
        test_metadata = {
            "test_number": self.test_count + 1,
            "test_name": test_name,
            "prompt": prompt,
            "repo_path": repo_path,
            "config_path": config_path,
            "expected_files": expected_files,
            "expected_chunks": expected_chunks,
            "timestamp": datetime.now().isoformat(),
            "run_dir": str(run_dir)
        }

        # Save test metadata
        with open(run_dir / "test_metadata.json", "w") as f:
            json.dump(test_metadata, f, indent=2)

        # Build command
        cmd = [sys.executable, "-m", "ws_ctx_engine.cli", "index", repo_path]
        if config_path:
            cmd.extend(["--config", config_path])

        # Run the test
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            duration = time.time() - start_time
            success = result.returncode == 0
            error_message = None
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            success = False
            error_message = "Test timed out after 5 minutes"
            result = None
        except Exception as e:
            duration = time.time() - start_time
            success = False
            error_message = str(e)
            result = None

        # Save command output
        if result:
            with open(run_dir / "stdout.log", "w") as f:
                f.write(result.stdout)
            with open(run_dir / "stderr.log", "w") as f:
                f.write(result.stderr)

        # Copy artifacts from .ws-ctx-engine
        context_pack_dir = Path(repo_path) / ".ws-ctx-engine"
        if context_pack_dir.exists():
            artifacts_dir = run_dir / "artifacts"
            artifacts_dir.mkdir(exist_ok=True)

            # Copy metadata
            if (context_pack_dir / "metadata.json").exists():
                shutil.copy2(
                    context_pack_dir / "metadata.json",
                    artifacts_dir / "metadata.json"
                )

            # Copy vector index
            if (context_pack_dir / "vector.idx").exists():
                shutil.copy2(
                    context_pack_dir / "vector.idx",
                    artifacts_dir / "vector.idx"
                )

            # Copy graph
            if (context_pack_dir / "graph.pkl").exists():
                shutil.copy2(
                    context_pack_dir / "graph.pkl",
                    artifacts_dir / "graph.pkl"
                )

        # Parse results from metadata
        actual_files = None
        actual_chunks = None
        if (run_dir / "artifacts" / "metadata.json").exists():
            with open(run_dir / "artifacts" / "metadata.json") as f:
                metadata = json.load(f)
                actual_files = metadata.get("file_count")

        # Find the latest log file
        log_dir = Path(".ws-ctx-engine/logs")
        if log_dir.exists():
            log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
            if log_files:
                latest_log = log_files[-1]
                shutil.copy2(latest_log, run_dir / "ws-ctx-engine.log")

                # Parse chunks from log
                with open(latest_log) as f:
                    for line in f:
                        if "chunks_extracted=" in line:
                            parts = line.split("chunks_extracted=")
                            if len(parts) > 1:
                                actual_chunks = int(parts[1].split()[0])
                                break

        # Compile results
        test_result = {
            **test_metadata,
            "success": success,
            "duration": duration,
            "error_message": error_message,
            "actual_files": actual_files,
            "actual_chunks": actual_chunks,
            "files_match": actual_files == expected_files if expected_files else None,
            "chunks_match": actual_chunks == expected_chunks if expected_chunks else None
        }

        # Save test results
        with open(run_dir / "test_results.json", "w") as f:
            json.dump(test_result, f, indent=2)

        # Print summary
        print(f"\n{'='*80}")
        print(f"Test Results: {test_name}")
        print(f"{'='*80}")
        print(f"Status: {'✅ PASS' if success else '❌ FAIL'}")
        print(f"Duration: {duration:.2f}s")
        if error_message:
            print(f"Error: {error_message}")
        print(f"\nExpected vs Actual:")
        print(f"  Files: {expected_files} → {actual_files} {'✅' if test_result['files_match'] else '❌' if expected_files else '⚠️'}")
        print(f"  Chunks: {expected_chunks} → {actual_chunks} {'✅' if test_result['chunks_match'] else '❌' if expected_chunks else '⚠️'}")
        print(f"\nArtifacts saved to: {run_dir}")
        print(f"{'='*80}\n")

        return test_result

    def generate_summary_report(self, results: List[Dict]):
        """Generate a summary report of all test runs.

        Args:
            results: List of test result dictionaries
        """
        summary_path = self.output_dir / "summary_report.md"

        with open(summary_path, "w") as f:
            f.write("# ws-ctx-engine Stress Test Summary\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Tests**: {len(results)}\n")
            f.write(f"**Passed**: {sum(1 for r in results if r['success'])}\n")
            f.write(f"**Failed**: {sum(1 for r in results if not r['success'])}\n\n")

            f.write("## Test Results\n\n")
            f.write("| # | Test Name | Status | Duration | Files | Chunks | Artifacts |\n")
            f.write("|---|-----------|--------|----------|-------|--------|----------|\n")

            for r in results:
                status = "✅ PASS" if r['success'] else "❌ FAIL"
                files_status = "✅" if r.get('files_match') else "❌" if r.get('expected_files') else "⚠️"
                chunks_status = "✅" if r.get('chunks_match') else "❌" if r.get('expected_chunks') else "⚠️"

                f.write(f"| {r['test_number']} | {r['test_name']} | {status} | {r['duration']:.2f}s | ")
                f.write(f"{r['expected_files']} → {r['actual_files']} {files_status} | ")
                f.write(f"{r['expected_chunks']} → {r['actual_chunks']} {chunks_status} | ")
                f.write(f"[📁]({Path(r['run_dir']).name}) |\n")

            f.write("\n## Detailed Test Information\n\n")
            for r in results:
                f.write(f"### Test #{r['test_number']}: {r['test_name']}\n\n")
                f.write(f"**Prompt**: {r['prompt']}\n\n")
                f.write(f"**Repository**: `{r['repo_path']}`\n\n")
                if r['config_path']:
                    f.write(f"**Config**: `{r['config_path']}`\n\n")
                f.write(f"**Status**: {'✅ PASS' if r['success'] else '❌ FAIL'}\n\n")
                f.write(f"**Duration**: {r['duration']:.2f}s\n\n")
                if r['error_message']:
                    f.write(f"**Error**: {r['error_message']}\n\n")
                f.write(f"**Results**:\n")
                f.write(f"- Files: {r['expected_files']} (expected) → {r['actual_files']} (actual)\n")
                f.write(f"- Chunks: {r['expected_chunks']} (expected) → {r['actual_chunks']} (actual)\n\n")
                f.write(f"**Artifacts**: `{r['run_dir']}`\n\n")
                f.write("---\n\n")

        print(f"\n📊 Summary report generated: {summary_path}\n")


def main():
    """Main entry point for stress testing."""
    parser = argparse.ArgumentParser(description="Stress test ws-ctx-engine")
    parser.add_argument(
        "--output-dir",
        default="tests/stress_results",
        help="Directory to store test results"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test suite (fewer tests)"
    )
    args = parser.parse_args()

    runner = StressTestRunner(output_dir=args.output_dir)
    results = []

    print("\n" + "="*80)
    print("WS-CTX-ENGINE STRESS TEST SUITE")
    print("="*80)

    # Test 1: zmr-koe with default config
    results.append(runner.run_test(
        test_name="zmr-koe_default",
        repo_path="examples/zmr-koe/source",
        prompt="Test zmr-koe repository with default configuration. "
               "Should extract functions from TypeScript/JavaScript files.",
        expected_files=1,
        expected_chunks=6
    ))

    # Test 2: zmr-koe with custom config
    results.append(runner.run_test(
        test_name="zmr-koe_custom_config",
        repo_path="examples/zmr-koe/source",
        config_path="examples/zmr-koe/config.yaml",
        prompt="Test zmr-koe repository with custom config (50k token budget, TS/JS focus). "
               "Should respect include/exclude patterns.",
        expected_files=1,
        expected_chunks=6
    ))

    if not args.quick:
        # Test 3: Empty repository
        empty_repo = Path("tests/fixtures/empty_repo")
        empty_repo.mkdir(parents=True, exist_ok=True)
        results.append(runner.run_test(
            test_name="empty_repository",
            repo_path=str(empty_repo),
            prompt="Test with empty repository. Should handle gracefully with no files.",
            expected_files=0,
            expected_chunks=0
        ))

        # Test 4: Repository with only config files
        config_only_repo = Path("tests/fixtures/config_only_repo")
        config_only_repo.mkdir(parents=True, exist_ok=True)
        (config_only_repo / "package.json").write_text('{"name": "test"}')
        (config_only_repo / "tsconfig.json").write_text('{"compilerOptions": {}}')
        results.append(runner.run_test(
            test_name="config_files_only",
            repo_path=str(config_only_repo),
            prompt="Test with only config files (no functions/classes). "
                   "Should scan files but extract 0 chunks.",
            expected_files=0,
            expected_chunks=0
        ))

        # Test 5: Large file stress test
        large_file_repo = Path("tests/fixtures/large_file_repo")
        large_file_repo.mkdir(parents=True, exist_ok=True)
        large_file_content = "\n".join([
            f"export function func{i}() {{ return {i}; }}"
            for i in range(1000)
        ])
        (large_file_repo / "large.ts").write_text(large_file_content)
        results.append(runner.run_test(
            test_name="large_file_1000_functions",
            repo_path=str(large_file_repo),
            prompt="Test with large file containing 1000 functions. "
                   "Should handle large files efficiently.",
            expected_files=1,
            expected_chunks=1000
        ))

    # Generate summary report
    runner.generate_summary_report(results)

    # Exit with appropriate code
    failed_tests = sum(1 for r in results if not r['success'])
    if failed_tests > 0:
        print(f"\n❌ {failed_tests} test(s) failed\n")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} tests passed\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
