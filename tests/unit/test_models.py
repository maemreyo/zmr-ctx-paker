"""Unit tests for data models."""

import hashlib
import os
import tempfile
from datetime import datetime

import pytest
import tiktoken

from ws_ctx_engine.models import CodeChunk, IndexMetadata


class TestCodeChunk:
    """Unit tests for CodeChunk dataclass."""
    
    def test_codechunk_creation(self):
        """Test basic CodeChunk instantiation."""
        chunk = CodeChunk(
            path="src/main.py",
            start_line=1,
            end_line=10,
            content="def hello():\n    print('Hello')",
            symbols_defined=["hello"],
            symbols_referenced=["print"],
            language="python"
        )
        
        assert chunk.path == "src/main.py"
        assert chunk.start_line == 1
        assert chunk.end_line == 10
        assert chunk.content == "def hello():\n    print('Hello')"
        assert chunk.symbols_defined == ["hello"]
        assert chunk.symbols_referenced == ["print"]
        assert chunk.language == "python"
    
    def test_token_count_simple(self):
        """Test token counting with simple content."""
        encoding = tiktoken.get_encoding("cl100k_base")
        chunk = CodeChunk(
            path="src/test.py",
            start_line=1,
            end_line=1,
            content="print('hello')",
            symbols_defined=[],
            symbols_referenced=["print"],
            language="python"
        )
        
        token_count = chunk.token_count(encoding)
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_token_count_empty_content(self):
        """Test token counting with empty content."""
        encoding = tiktoken.get_encoding("cl100k_base")
        chunk = CodeChunk(
            path="src/empty.py",
            start_line=1,
            end_line=1,
            content="",
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        
        token_count = chunk.token_count(encoding)
        assert token_count == 0
    
    def test_token_count_multiline(self):
        """Test token counting with multiline content."""
        encoding = tiktoken.get_encoding("cl100k_base")
        content = """def calculate_sum(a, b):
    '''Calculate the sum of two numbers.'''
    return a + b

def calculate_product(a, b):
    '''Calculate the product of two numbers.'''
    return a * b
"""
        chunk = CodeChunk(
            path="src/math_utils.py",
            start_line=1,
            end_line=8,
            content=content,
            symbols_defined=["calculate_sum", "calculate_product"],
            symbols_referenced=[],
            language="python"
        )
        
        token_count = chunk.token_count(encoding)
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_token_count_with_special_characters(self):
        """Test token counting with special characters and unicode."""
        encoding = tiktoken.get_encoding("cl100k_base")
        chunk = CodeChunk(
            path="src/unicode.py",
            start_line=1,
            end_line=3,
            content="# Comment with émojis 🚀\ndef greet():\n    print('Hello 世界')",
            symbols_defined=["greet"],
            symbols_referenced=["print"],
            language="python"
        )
        
        token_count = chunk.token_count(encoding)
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_token_count_javascript(self):
        """Test token counting with JavaScript content."""
        encoding = tiktoken.get_encoding("cl100k_base")
        chunk = CodeChunk(
            path="src/app.js",
            start_line=1,
            end_line=5,
            content="function greet(name) {\n  console.log(`Hello, ${name}!`);\n}\n\ngreet('World');",
            symbols_defined=["greet"],
            symbols_referenced=["console.log"],
            language="javascript"
        )
        
        token_count = chunk.token_count(encoding)
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_empty_symbols_lists(self):
        """Test CodeChunk with empty symbol lists."""
        chunk = CodeChunk(
            path="src/empty.py",
            start_line=1,
            end_line=1,
            content="# Just a comment",
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        
        assert chunk.symbols_defined == []
        assert chunk.symbols_referenced == []
    
    def test_multiple_symbols(self):
        """Test CodeChunk with multiple symbols defined and referenced."""
        chunk = CodeChunk(
            path="src/module.py",
            start_line=1,
            end_line=20,
            content="import os\nimport sys\n\nclass MyClass:\n    pass\n\ndef func1():\n    pass\n\ndef func2():\n    pass",
            symbols_defined=["MyClass", "func1", "func2"],
            symbols_referenced=["os", "sys"],
            language="python"
        )
        
        assert len(chunk.symbols_defined) == 3
        assert len(chunk.symbols_referenced) == 2
        assert "MyClass" in chunk.symbols_defined
        assert "os" in chunk.symbols_referenced
    
    def test_line_numbers_boundary(self):
        """Test CodeChunk with various line number boundaries."""
        # Single line
        chunk1 = CodeChunk(
            path="src/single.py",
            start_line=5,
            end_line=5,
            content="x = 1",
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        assert chunk1.start_line == chunk1.end_line
        
        # Large range
        chunk2 = CodeChunk(
            path="src/large.py",
            start_line=1,
            end_line=1000,
            content="# Large file content",
            symbols_defined=[],
            symbols_referenced=[],
            language="python"
        )
        assert chunk2.end_line - chunk2.start_line == 999
    
    def test_different_languages(self):
        """Test CodeChunk with different programming languages."""
        languages = ["python", "javascript", "typescript", "java", "go", "rust"]
        
        for lang in languages:
            chunk = CodeChunk(
                path=f"src/file.{lang}",
                start_line=1,
                end_line=10,
                content="// code content",
                symbols_defined=["function"],
                symbols_referenced=[],
                language=lang
            )
            assert chunk.language == lang



class TestIndexMetadata:
    """Unit tests for IndexMetadata dataclass."""
    
    def test_indexmetadata_creation(self):
        """Test basic IndexMetadata instantiation."""
        now = datetime.now()
        metadata = IndexMetadata(
            created_at=now,
            repo_path="/path/to/repo",
            file_count=10,
            backend="LEANNIndex+IGraphRepoMap",
            file_hashes={"src/main.py": "abc123", "src/utils.py": "def456"}
        )
        
        assert metadata.created_at == now
        assert metadata.repo_path == "/path/to/repo"
        assert metadata.file_count == 10
        assert metadata.backend == "LEANNIndex+IGraphRepoMap"
        assert len(metadata.file_hashes) == 2
        assert metadata.file_hashes["src/main.py"] == "abc123"
    
    def test_is_stale_no_changes(self):
        """Test is_stale returns False when files haven't changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, 'w') as f:
                f.write("print('hello')")
            
            # Calculate hash
            with open(test_file, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Create metadata
            metadata = IndexMetadata(
                created_at=datetime.now(),
                repo_path=tmpdir,
                file_count=1,
                backend="LEANNIndex",
                file_hashes={"test.py": file_hash}
            )
            
            # Should not be stale
            assert not metadata.is_stale(tmpdir)
    
    def test_is_stale_file_modified(self):
        """Test is_stale returns True when a file is modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, 'w') as f:
                f.write("print('hello')")
            
            # Calculate original hash
            with open(test_file, 'rb') as f:
                original_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Create metadata with original hash
            metadata = IndexMetadata(
                created_at=datetime.now(),
                repo_path=tmpdir,
                file_count=1,
                backend="LEANNIndex",
                file_hashes={"test.py": original_hash}
            )
            
            # Modify the file
            with open(test_file, 'w') as f:
                f.write("print('goodbye')")
            
            # Should be stale
            assert metadata.is_stale(tmpdir)
    
    def test_is_stale_file_deleted(self):
        """Test is_stale returns True when a file is deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata for a non-existent file
            metadata = IndexMetadata(
                created_at=datetime.now(),
                repo_path=tmpdir,
                file_count=1,
                backend="LEANNIndex",
                file_hashes={"nonexistent.py": "abc123"}
            )
            
            # Should be stale because file doesn't exist
            assert metadata.is_stale(tmpdir)
    
    def test_is_stale_multiple_files_one_changed(self):
        """Test is_stale returns True when one of multiple files changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple test files
            file1 = os.path.join(tmpdir, "file1.py")
            file2 = os.path.join(tmpdir, "file2.py")
            
            with open(file1, 'w') as f:
                f.write("print('file1')")
            with open(file2, 'w') as f:
                f.write("print('file2')")
            
            # Calculate hashes
            with open(file1, 'rb') as f:
                hash1 = hashlib.sha256(f.read()).hexdigest()
            with open(file2, 'rb') as f:
                hash2 = hashlib.sha256(f.read()).hexdigest()
            
            # Create metadata
            metadata = IndexMetadata(
                created_at=datetime.now(),
                repo_path=tmpdir,
                file_count=2,
                backend="LEANNIndex",
                file_hashes={"file1.py": hash1, "file2.py": hash2}
            )
            
            # Modify one file
            with open(file2, 'w') as f:
                f.write("print('modified')")
            
            # Should be stale
            assert metadata.is_stale(tmpdir)
    
    def test_is_stale_empty_file_hashes(self):
        """Test is_stale with empty file_hashes dictionary."""
        metadata = IndexMetadata(
            created_at=datetime.now(),
            repo_path="/path/to/repo",
            file_count=0,
            backend="LEANNIndex",
            file_hashes={}
        )
        
        # Should not be stale (no files to check)
        assert not metadata.is_stale("/path/to/repo")
    
    def test_is_stale_with_subdirectories(self):
        """Test is_stale with files in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create subdirectory and file
            subdir = os.path.join(tmpdir, "src")
            os.makedirs(subdir)
            test_file = os.path.join(subdir, "main.py")
            
            with open(test_file, 'w') as f:
                f.write("print('hello')")
            
            # Calculate hash
            with open(test_file, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Create metadata with relative path
            metadata = IndexMetadata(
                created_at=datetime.now(),
                repo_path=tmpdir,
                file_count=1,
                backend="LEANNIndex",
                file_hashes={"src/main.py": file_hash}
            )
            
            # Should not be stale
            assert not metadata.is_stale(tmpdir)
            
            # Modify the file
            with open(test_file, 'w') as f:
                f.write("print('modified')")
            
            # Should be stale
            assert metadata.is_stale(tmpdir)
    
    def test_different_backends(self):
        """Test IndexMetadata with different backend strings."""
        backends = [
            "LEANNIndex+IGraphRepoMap",
            "FAISSIndex+NetworkXRepoMap",
            "LEANNIndex+NetworkXRepoMap",
            "FAISSIndex+IGraphRepoMap"
        ]
        
        for backend in backends:
            metadata = IndexMetadata(
                created_at=datetime.now(),
                repo_path="/path/to/repo",
                file_count=5,
                backend=backend,
                file_hashes={}
            )
            assert metadata.backend == backend
