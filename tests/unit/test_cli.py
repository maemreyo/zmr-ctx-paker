"""
Unit tests for CLI interface.

Tests specific examples and edge cases for CLI commands.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def create_test_repo(repo_path: Path) -> None:
    """Create a minimal test repository with Python files."""
    src_dir = repo_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    utils_file = src_dir / "utils.py"
    utils_file.write_text("""
from .main import add

def subtract(a, b):
    return a - b
""")
    
    # Create config file that uses fallback backends (no API required)
    config_file = repo_path / ".context-pack.yaml"
    config_file.write_text("""
backends:
  vector_index: faiss
  graph: networkx
  embeddings: local
""")


def run_cli_command(args, **kwargs):
    """
    Run CLI command with environment variables to prevent PyTorch multiprocessing issues.
    
    This helper sets environment variables that prevent PyTorch from using multiprocessing,
    which can cause SIGSEGV crashes in subprocess tests.
    """
    env = os.environ.copy()
    # Prevent PyTorch from using multiprocessing
    env['OMP_NUM_THREADS'] = '1'
    env['MKL_NUM_THREADS'] = '1'
    env['OPENBLAS_NUM_THREADS'] = '1'
    env['VECLIB_MAXIMUM_THREADS'] = '1'
    env['NUMEXPR_NUM_THREADS'] = '1'
    # Force PyTorch to use single thread
    env['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Merge with any env passed in kwargs
    if 'env' in kwargs:
        env.update(kwargs['env'])
    kwargs['env'] = env
    
    return subprocess.run(args, **kwargs)


class TestCLIIndexCommand:
    """Test cases for 'context-pack index' command."""
    
    def test_index_creates_all_required_files(self):
        """Test that index command creates all required index files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            result = run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            
            index_dir = repo_path / ".context-pack"
            assert index_dir.exists()
            assert (index_dir / "vector.idx").exists()
            assert (index_dir / "graph.pkl").exists()
            assert (index_dir / "metadata.json").exists()
    
    def test_index_fails_with_invalid_path(self):
        """Test that index command fails gracefully with invalid path."""
        result = run_cli_command(
            [sys.executable, "-m", "context_packer.cli", "index", "/nonexistent/path"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode != 0
        assert "does not exist" in result.stdout.lower()
    
    def test_index_fails_with_file_instead_of_directory(self):
        """Test that index command fails when given a file instead of directory."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("print('test')")
            file_path = f.name
        
        try:
            result = run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", file_path],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode != 0
            assert "not a directory" in result.stdout.lower()
        finally:
            Path(file_path).unlink()
    
    def test_index_with_verbose_flag(self):
        """Test that index command works with --verbose flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            result = run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path), "--verbose"],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0


class TestCLIQueryCommand:
    """Test cases for 'context-pack query' command."""
    
    def test_query_generates_xml_output(self):
        """Test that query command generates XML output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Build indexes first
            run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: xml
output_path: {output_dir}
""")
            
            # Run query
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "calculator",
                    "--repo", str(repo_path),
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            assert (output_dir / "repomix-output.xml").exists()
    
    def test_query_generates_zip_output(self):
        """Test that query command generates ZIP output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Build indexes first
            run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: zip
output_path: {output_dir}
""")
            
            # Run query
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "calculator",
                    "--repo", str(repo_path),
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            assert (output_dir / "context-pack.zip").exists()
    
    def test_query_fails_without_indexes(self):
        """Test that query command fails gracefully when indexes don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "test",
                    "--repo", str(repo_path),
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode != 0
            assert "index" in result.stdout.lower()
    
    def test_query_format_flag_overrides_config(self):
        """Test that --format flag overrides config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Build indexes
            run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config with XML format
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: xml
output_path: {output_dir}
""")
            
            # Run query with ZIP format flag (override)
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "test",
                    "--repo", str(repo_path),
                    "--format", "zip",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            # Should create ZIP, not XML
            assert (output_dir / "context-pack.zip").exists()
    
    def test_query_budget_flag_overrides_config(self):
        """Test that --budget flag overrides config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Build indexes
            run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: xml
token_budget: 100000
output_path: {output_dir}
""")
            
            # Run query with different budget
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "test",
                    "--repo", str(repo_path),
                    "--budget", "50000",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
    
    def test_query_fails_with_invalid_format(self):
        """Test that query command fails with invalid format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Build indexes
            run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "test",
                    "--repo", str(repo_path),
                    "--format", "invalid",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode != 0
            assert "invalid" in result.stdout.lower()
    
    def test_query_fails_with_invalid_budget(self):
        """Test that query command fails with invalid budget."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Build indexes
            run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "test",
                    "--repo", str(repo_path),
                    "--budget", "-1000",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode != 0


class TestCLIPackCommand:
    """Test cases for 'context-pack pack' command."""
    
    def test_pack_runs_full_workflow(self):
        """Test that pack command runs full workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: xml
output_path: {output_dir}
""")
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "pack",
                    str(repo_path),
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
            
            # Verify indexes were created
            assert (repo_path / ".context-pack" / "vector.idx").exists()
            
            # Verify output was created
            assert (output_dir / "repomix-output.xml").exists()
    
    def test_pack_with_query_option(self):
        """Test that pack command works with --query option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: xml
output_path: {output_dir}
""")
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "pack",
                    str(repo_path),
                    "--query", "calculator function",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0
    
    def test_pack_rebuilds_stale_indexes(self):
        """Test that pack command rebuilds stale indexes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            # Create output directory
            output_dir = repo_path / "output"
            output_dir.mkdir()
            
            # Create config
            config_path = repo_path / ".context-pack.yaml"
            config_path.write_text(f"""
format: xml
output_path: {output_dir}
""")
            
            # First pack
            result = run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "pack", str(repo_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            
            # Modify a file to make indexes stale
            src_file = repo_path / "src" / "main.py"
            src_file.write_text(src_file.read_text() + "\n# Modified\n")
            
            # Second pack should rebuild
            result = run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "pack", str(repo_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0


class TestCLIErrorHandling:
    """Test cases for CLI error handling."""
    
    def test_helpful_error_for_missing_indexes(self):
        """Test that CLI shows helpful error when indexes are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "query",
                    "test",
                    "--repo", str(repo_path),
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode != 0
            # Should suggest running index command
            assert "index" in result.stdout.lower()
    
    def test_helpful_error_for_invalid_config_path(self):
        """Test that CLI shows helpful error for invalid config path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            result = run_cli_command(
                [
                    sys.executable, "-m", "context_packer.cli", "index",
                    str(repo_path),
                    "--config", "/nonexistent/config.yaml",
                ],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode != 0
            assert "not found" in result.stdout.lower()
    
    def test_exit_code_0_on_success(self):
        """Test that CLI returns exit code 0 on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            create_test_repo(repo_path)
            
            result = run_cli_command(
                [sys.executable, "-m", "context_packer.cli", "index", str(repo_path)],
                capture_output=True,
            )
            
            assert result.returncode == 0
    
    def test_exit_code_nonzero_on_failure(self):
        """Test that CLI returns non-zero exit code on failure."""
        result = run_cli_command(
            [sys.executable, "-m", "context_packer.cli", "index", "/nonexistent"],
            capture_output=True,
        )
        
        assert result.returncode != 0
