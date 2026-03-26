"""
Property-based tests for CLI interface.

Tests Properties 29-33 from the design document.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from ws_ctx_engine.config import Config


def run_cli(*args, **kwargs):
    """Run a CLI subprocess with env vars that prevent PyTorch SIGSEGV on macOS."""
    env = os.environ.copy()
    env.update({
        'OMP_NUM_THREADS': '1',
        'MKL_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
        'VECLIB_MAXIMUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'TOKENIZERS_PARALLELISM': 'false',
    })
    if 'env' in kwargs:
        env.update(kwargs['env'])
    kwargs['env'] = env
    if kwargs.get('text') or kwargs.get('encoding'):
        kwargs.setdefault('encoding', 'utf-8')
        kwargs.setdefault('errors', 'replace')
    return subprocess.run(*args, **kwargs)


# Helper function to create a minimal test repository
def create_test_repo(repo_path: Path) -> None:
    """Create a minimal test repository with Python files."""
    # Create source directory
    src_dir = repo_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a simple Python file
    main_file = src_dir / "main.py"
    main_file.write_text("""
def hello():
    return "Hello, World!"

def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")
    
    # Create another Python file
    utils_file = src_dir / "utils.py"
    utils_file.write_text("""
from .main import add

def subtract(a, b):
    return a - b

def process_data(data):
    return [add(x, 1) for x in data]
""")
    
    # Create config file that uses fallback backends (no API required)
    config_file = repo_path / ".ws-ctx-engine.yaml"
    config_file.write_text("""
backends:
  vector_index: faiss
  graph: networkx
  embeddings: local
""")


# Property 29: CLI Index Command
# **Validates: Requirements 11.2**
def test_cli_index_command_creates_indexes():
    """
    Property 29: CLI Index Command
    
    For any valid repository path provided to `ws-ctx-engine index`,
    the command SHALL build and save indexes to `.ws-ctx-engine/` directory.
    
    **Validates: Requirements 11.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create test repository
        create_test_repo(repo_path)
        
        # Run index command
        result = run_cli(
            [sys.executable, "-m", "ws_ctx_engine.cli", "index", str(repo_path)],
            capture_output=True,
            text=True,
        )
        
        # Verify exit code is 0 (success)
        assert result.returncode == 0, f"Index command failed: {result.stderr}"
        
        # Verify indexes were created
        index_dir = repo_path / ".ws-ctx-engine"
        assert index_dir.exists(), "Index directory was not created"
        assert (index_dir / "vector.idx").exists(), "Vector index was not created"
        assert (index_dir / "graph.pkl").exists(), "Graph was not created"
        assert (index_dir / "metadata.json").exists(), "Metadata was not created"


@given(
    format_choice=st.sampled_from(["xml", "zip"]),
    budget=st.integers(min_value=1000, max_value=200000),
)
@settings(max_examples=10, deadline=60000)  # Reduced examples for CLI tests
def test_cli_query_command_generates_output(format_choice: str, budget: int):
    """
    Property 30: CLI Query Command
    
    For any query text provided to `ws-ctx-engine query`,
    the command SHALL search indexes and generate output in the configured format.
    
    **Validates: Requirements 11.3**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create test repository
        create_test_repo(repo_path)
        
        # First, build indexes
        result = run_cli(
            [sys.executable, "-m", "ws_ctx_engine.cli", "index", str(repo_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Index command failed: {result.stderr}"
        
        # Create output directory
        output_dir = repo_path / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Create config file with output settings
        config_path = repo_path / ".ws-ctx-engine.yaml"
        config_path.write_text(f"""
format: {format_choice}
token_budget: {budget}
output_path: {output_dir}
""")
        
        # Run query command
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "query",
                "calculator function",
                "--repo", str(repo_path),
                "--format", format_choice,
                "--budget", str(budget),
            ],
            capture_output=True,
            text=True,
        )
        
        # Verify exit code is 0 (success)
        assert result.returncode == 0, f"Query command failed: {result.stderr}"
        
        # Verify output was generated
        if format_choice == "xml":
            output_file = output_dir / "repomix-output.xml"
            assert output_file.exists(), "XML output was not created"
            assert output_file.stat().st_size > 0, "XML output is empty"
        else:  # zip
            output_file = output_dir / "ws-ctx-engine.zip"
            assert output_file.exists(), "ZIP output was not created"
            assert output_file.stat().st_size > 0, "ZIP output is empty"


def test_cli_pack_command_executes_full_workflow():
    """
    Property 31: CLI Pack Command
    
    For any valid repository path provided to `ws-ctx-engine pack`,
    the command SHALL execute the full workflow (index, query, pack) and produce output.
    
    **Validates: Requirements 11.4**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create test repository
        create_test_repo(repo_path)
        
        # Create output directory
        output_dir = repo_path / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Create config file
        config_path = repo_path / ".ws-ctx-engine.yaml"
        config_path.write_text(f"""
format: xml
token_budget: 50000
output_path: {output_dir}
""")
        
        # Run pack command (full workflow)
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "pack",
                str(repo_path),
                "--query", "calculator",
            ],
            capture_output=True,
            text=True,
        )
        
        # Verify exit code is 0 (success)
        assert result.returncode == 0, f"Pack command failed: {result.stderr}"
        
        # Verify indexes were created
        index_dir = repo_path / ".ws-ctx-engine"
        assert index_dir.exists(), "Index directory was not created"
        assert (index_dir / "vector.idx").exists(), "Vector index was not created"
        
        # Verify output was generated
        output_file = output_dir / "repomix-output.xml"
        assert output_file.exists(), "Output was not created"
        assert output_file.stat().st_size > 0, "Output is empty"


@given(
    format_choice=st.sampled_from(["xml", "zip"]),
    budget=st.integers(min_value=5000, max_value=150000),
)
@settings(max_examples=10, deadline=60000)
def test_cli_flag_handling_overrides_config(format_choice: str, budget: int):
    """
    Property 32: CLI Flag Handling
    
    For any valid CLI flags (--format, --budget, --config),
    the ws_ctx_engine SHALL apply the flag values,
    overriding configuration file or default values.
    
    **Validates: Requirements 11.5, 11.6, 11.7**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Create test repository
        create_test_repo(repo_path)
        
        # Create output directory
        output_dir = repo_path / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Create config file with DIFFERENT values than CLI flags
        config_path = repo_path / ".ws-ctx-engine.yaml"
        opposite_format = "zip" if format_choice == "xml" else "xml"
        config_path.write_text(f"""
format: {opposite_format}
token_budget: 100000
output_path: {output_dir}
""")
        
        # Build indexes first
        result = run_cli(
            [sys.executable, "-m", "ws_ctx_engine.cli", "index", str(repo_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        
        # Run query with CLI flags that override config
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "query",
                "test query",
                "--repo", str(repo_path),
                "--format", format_choice,  # Override config
                "--budget", str(budget),     # Override config
            ],
            capture_output=True,
            text=True,
        )
        
        # Verify exit code is 0 (success)
        assert result.returncode == 0, f"Query command failed: {result.stderr}"
        
        # Verify output was generated with CLI flag format (not config format)
        if format_choice == "xml":
            output_file = output_dir / "repomix-output.xml"
            assert output_file.exists(), "XML output was not created (flag not applied)"
            # Verify ZIP was NOT created
            zip_file = output_dir / "ws-ctx-engine.zip"
            assert not zip_file.exists() or zip_file.stat().st_size == 0, \
                "ZIP was created despite --format xml flag"
        else:  # zip
            output_file = output_dir / "ws-ctx-engine.zip"
            assert output_file.exists(), "ZIP output was not created (flag not applied)"


def test_cli_exit_codes_success_and_failure():
    """
    Property 33: CLI Exit Codes
    
    For any CLI command execution,
    the exit code SHALL be 0 on success and non-zero on failure.
    
    **Validates: Requirements 11.8**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Test 1: Success case - valid index command
        create_test_repo(repo_path)
        result = run_cli(
            [sys.executable, "-m", "ws_ctx_engine.cli", "index", str(repo_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Success case should return exit code 0"
        
        # Test 2: Failure case - invalid repo path
        invalid_path = repo_path / "nonexistent"
        result = run_cli(
            [sys.executable, "-m", "ws_ctx_engine.cli", "index", str(invalid_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Failure case should return non-zero exit code"
        
        # Test 3: Failure case - invalid format flag
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "query",
                "test",
                "--repo", str(repo_path),
                "--format", "invalid_format",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Invalid format should return non-zero exit code"
        
        # Test 4: Failure case - invalid budget (negative)
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "query",
                "test",
                "--repo", str(repo_path),
                "--budget", "-1000",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Invalid budget should return non-zero exit code"
        
        # Test 5: Failure case - query without indexes
        new_repo = Path(tmpdir) / "new_repo"
        new_repo.mkdir()
        create_test_repo(new_repo)
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "query",
                "test",
                "--repo", str(new_repo),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, "Query without indexes should return non-zero exit code"


# Additional edge case tests
def test_cli_handles_missing_config_file():
    """Test that CLI handles missing config file gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        create_test_repo(repo_path)
        
        # Try to use non-existent config file
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "index",
                str(repo_path),
                "--config", str(repo_path / "nonexistent.yaml"),
            ],
            capture_output=True,
            text=True,
        )
        
        # Should fail with non-zero exit code
        assert result.returncode != 0
        assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()


@given(limit=st.integers(min_value=1, max_value=5))
@settings(max_examples=5, deadline=60000)
def test_search_agent_mode_ndjson_lines_are_parseable(limit: int):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        create_test_repo(repo_path)

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["VECLIB_MAXIMUM_THREADS"] = "1"
        env["NUMEXPR_NUM_THREADS"] = "1"
        env["TOKENIZERS_PARALLELISM"] = "false"

        index_result = run_cli(
            [sys.executable, "-m", "ws_ctx_engine.cli", "index", str(repo_path)],
            capture_output=True,
            text=True,
            env=env,
        )
        assert index_result.returncode == 0

        search_result = run_cli(
            [
                sys.executable,
                "-m",
                "ws_ctx_engine.cli",
                "--agent-mode",
                "search",
                "calculator",
                "--repo",
                str(repo_path),
                "--limit",
                str(limit),
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert search_result.returncode == 0

        lines = [line for line in search_result.stdout.splitlines() if line.strip()]
        assert len(lines) >= 1

        payloads = [json.loads(line) for line in lines]
        assert payloads[0]["type"] == "meta"
        assert all(isinstance(item, dict) for item in payloads)


@given(query_text=st.sampled_from(["calculator", "authentication", "utils function"]))
@settings(max_examples=3, deadline=60000)
def test_pack_json_output_is_parseable_and_has_required_shape(query_text: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        create_test_repo(repo_path)

        output_dir = repo_path / "output"
        output_dir.mkdir(exist_ok=True)

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["VECLIB_MAXIMUM_THREADS"] = "1"
        env["NUMEXPR_NUM_THREADS"] = "1"
        env["TOKENIZERS_PARALLELISM"] = "false"

        config_path = repo_path / "phase2-pack.yaml"
        config_path.write_text(
            f"""
backends:
  vector_index: faiss
  graph: networkx
  embeddings: local
output_path: {output_dir}
""",
            encoding="utf-8",
        )

        result = run_cli(
            [
                sys.executable,
                "-m",
                "ws_ctx_engine.cli",
                "pack",
                str(repo_path),
                "--query",
                query_text,
                "--format",
                "json",
                "--config",
                str(config_path),
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0

        output_file = output_dir / "ws-ctx-engine.json"
        assert output_file.exists()

        payload = json.loads(output_file.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "files" in payload
        assert "index_health" in payload["metadata"]
        assert isinstance(payload["files"], list)


def test_cli_verbose_flag_enables_detailed_logging():
    """Test that --verbose flag enables detailed logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        create_test_repo(repo_path)
        
        # Run with verbose flag
        result = run_cli(
            [
                sys.executable, "-m", "ws_ctx_engine.cli", "index",
                str(repo_path),
                "--verbose",
            ],
            capture_output=True,
            text=True,
        )
        
        # Should succeed
        assert result.returncode == 0
        
        # Output should contain more detailed information
        # (This is a basic check - actual verbose output depends on logger implementation)
        assert len(result.stdout) > 0 or len(result.stderr) > 0
