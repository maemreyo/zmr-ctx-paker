"""Unit tests for ZIP Packer.

These tests validate specific examples and edge cases for ZIP generation.
"""

import io
import os
import tempfile
import zipfile

import pytest

from context_packer.packer import ZIPPacker


class TestZIPPacker:
    """Unit tests for ZIPPacker class."""
    
    def test_zip_preserves_directory_structure(self):
        """Test that ZIP preserves directory structure under files/.
        
        **Validates: Requirements 7.1, 7.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with directory structure
            files = [
                "src/main.py",
                "src/utils/helper.py",
                "tests/test_main.py",
                "README.md"
            ]
            
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Content for {file_path}\n")
            
            # Pack files
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": len(files),
                "total_tokens": 100
            }
            importance_scores = {fp: 0.5 for fp in files}
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Verify ZIP structure
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_contents = zip_file.namelist()
                
                # Check all files are under files/ directory
                for file_path in files:
                    expected_path = f"files/{file_path}"
                    # Normalize path separators
                    normalized_contents = [zp.replace('\\', '/') for zp in zip_contents]
                    assert expected_path in normalized_contents, \
                        f"Expected '{expected_path}' in ZIP, got {normalized_contents}"
                
                # Verify content is preserved
                for file_path in files:
                    zip_path = f"files/{file_path}"
                    # Find matching path (handle separator differences)
                    matching = [zp for zp in zip_file.namelist() if zp.replace('\\', '/') == zip_path]
                    assert len(matching) > 0, f"File {zip_path} not found"
                    
                    content = zip_file.read(matching[0]).decode('utf-8')
                    assert f"# Content for {file_path}" in content
    
    def test_manifest_includes_all_required_information(self):
        """Test that manifest includes all required information.
        
        **Validates: Requirements 7.4, 7.5, 7.6**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = ["file1.py", "file2.py", "file3.py"]
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(f"def test():\n    pass\n")
            
            # Pack files with varied importance scores
            packer = ZIPPacker()
            metadata = {
                "repo_name": "my-project",
                "file_count": 3,
                "total_tokens": 150,
                "query": "find test functions",
                "changed_files": ["file1.py"]
            }
            importance_scores = {
                "file1.py": 0.9,  # High score
                "file2.py": 0.5,  # Medium score
                "file3.py": 0.2   # Low score
            }
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Extract and verify manifest
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                # Check repository metadata
                assert "my-project" in manifest
                assert "3" in manifest  # file count
                assert "150" in manifest  # total tokens
                assert "find test functions" in manifest  # query
                assert "file1.py" in manifest  # changed file
                
                # Check all files are listed with scores
                assert "file1.py" in manifest
                assert "0.9000" in manifest
                assert "file2.py" in manifest
                assert "0.5000" in manifest
                assert "file3.py" in manifest
                assert "0.2000" in manifest
                
                # Check inclusion reasons
                assert "Changed file" in manifest or "Semantic match" in manifest
                assert "Dependency" in manifest or "Semantic match" in manifest
                
                # Check reading order section exists
                assert "Reading Order" in manifest or "Suggested Reading Order" in manifest
                
                # Verify files are ordered by importance in reading order
                # file1.py (0.9) should appear before file2.py (0.5) in reading order
                reading_section = manifest.split("Reading Order")[-1]
                file1_pos = reading_section.find("file1.py")
                file2_pos = reading_section.find("file2.py")
                file3_pos = reading_section.find("file3.py")
                
                assert file1_pos < file2_pos < file3_pos, \
                    "Files should be ordered by importance in reading order"
    
    def test_files_are_under_files_directory(self):
        """Test that all files are placed under files/ directory.
        
        **Validates: Requirements 7.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = ["test1.py", "test2.py"]
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write("# test\n")
            
            # Pack files
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 2,
                "total_tokens": 50
            }
            importance_scores = {fp: 0.5 for fp in files}
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Verify all files are under files/
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                for zip_path in zip_file.namelist():
                    if zip_path != "REVIEW_CONTEXT.md":
                        # Normalize path separator
                        normalized_path = zip_path.replace('\\', '/')
                        assert normalized_path.startswith("files/"), \
                            f"File '{zip_path}' must be under files/ directory"
    
    def test_review_context_exists_in_zip_root(self):
        """Test that REVIEW_CONTEXT.md exists in ZIP root.
        
        **Validates: Requirements 7.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            file_path = "test.py"
            full_path = os.path.join(tmpdir, file_path)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write("# test\n")
            
            # Pack file
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 10
            }
            importance_scores = {file_path: 0.5}
            
            zip_bytes = packer.pack([file_path], tmpdir, metadata, importance_scores)
            
            # Verify REVIEW_CONTEXT.md exists in root
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_contents = zip_file.namelist()
                
                assert "REVIEW_CONTEXT.md" in zip_contents, \
                    "REVIEW_CONTEXT.md must exist in ZIP root"
                
                # Verify it's in root (not in subdirectory)
                assert not "REVIEW_CONTEXT.md".startswith("files/"), \
                    "REVIEW_CONTEXT.md must be in root, not under files/"
                
                # Verify it's readable
                manifest = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                assert len(manifest) > 0, \
                    "REVIEW_CONTEXT.md must not be empty"
    
    def test_empty_file_handling(self):
        """Test that empty files are handled correctly.
        
        **Validates: Requirements 7.1, 7.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty file
            file_path = "empty.py"
            full_path = os.path.join(tmpdir, file_path)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write("")
            
            # Pack file
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 0
            }
            importance_scores = {file_path: 0.5}
            
            zip_bytes = packer.pack([file_path], tmpdir, metadata, importance_scores)
            
            # Verify empty file is in ZIP
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_path = "files/empty.py"
                content = zip_file.read(zip_path).decode('utf-8')
                assert content == "", \
                    "Empty file content should be preserved"
    
    def test_unicode_content_handling(self):
        """Test that Unicode content is handled correctly.
        
        **Validates: Requirements 7.1, 7.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with Unicode content
            file_path = "unicode.py"
            unicode_content = '''# -*- coding: utf-8 -*-
def greet():
    print("Hello 世界")  # Chinese
    print("Привет мир")  # Russian
    print("🎉🎊")  # Emojis
'''
            full_path = os.path.join(tmpdir, file_path)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(unicode_content)
            
            # Pack file
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 50
            }
            importance_scores = {file_path: 0.5}
            
            zip_bytes = packer.pack([file_path], tmpdir, metadata, importance_scores)
            
            # Verify Unicode content is preserved
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_path = "files/unicode.py"
                content = zip_file.read(zip_path).decode('utf-8')
                
                assert content == unicode_content, \
                    "Unicode content should be preserved exactly"
                assert "世界" in content
                assert "Привет" in content
                assert "🎉" in content
    
    def test_special_characters_in_filenames(self):
        """Test that files with special characters in names are handled.
        
        **Validates: Requirements 7.1, 7.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with special characters
            files = [
                "test-file.py",
                "test_file.py",
                "test.file.py"
            ]
            
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {file_path}\n")
            
            # Pack files
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": len(files),
                "total_tokens": 50
            }
            importance_scores = {fp: 0.5 for fp in files}
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Verify all files are in ZIP
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_contents = [zp.replace('\\', '/') for zp in zip_file.namelist()]
                
                for file_path in files:
                    expected_path = f"files/{file_path}"
                    assert expected_path in zip_contents, \
                        f"File '{file_path}' with special characters should be in ZIP"
    
    def test_nested_directory_structure(self):
        """Test that deeply nested directories are preserved.
        
        **Validates: Requirements 7.1, 7.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deeply nested file
            file_path = "a/b/c/d/deep.py"
            full_path = os.path.join(tmpdir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write("# deep file\n")
            
            # Pack file
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 10
            }
            importance_scores = {file_path: 0.5}
            
            zip_bytes = packer.pack([file_path], tmpdir, metadata, importance_scores)
            
            # Verify nested structure is preserved
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                expected_path = "files/a/b/c/d/deep.py"
                zip_contents = [zp.replace('\\', '/') for zp in zip_file.namelist()]
                
                assert expected_path in zip_contents, \
                    "Deeply nested directory structure should be preserved"
    
    def test_inclusion_reason_for_changed_files(self):
        """Test that changed files are marked correctly in manifest.
        
        **Validates: Requirements 7.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = ["changed.py", "unchanged.py"]
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write("# test\n")
            
            # Pack files with one marked as changed
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 2,
                "total_tokens": 50,
                "changed_files": ["changed.py"]
            }
            importance_scores = {
                "changed.py": 0.8,
                "unchanged.py": 0.5
            }
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Verify manifest marks changed file correctly
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                # Changed file should be marked as "Changed file"
                assert "changed.py" in manifest
                assert "Changed file" in manifest
    
    def test_inclusion_reason_based_on_score(self):
        """Test that inclusion reasons are inferred from scores.
        
        **Validates: Requirements 7.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with different score ranges
            files = ["high.py", "medium.py", "low.py"]
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write("# test\n")
            
            # Pack files with varied scores
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 3,
                "total_tokens": 100
            }
            importance_scores = {
                "high.py": 0.9,    # Should be "Semantic match"
                "medium.py": 0.5,  # Should be "Dependency"
                "low.py": 0.2      # Should be "Transitive dependency"
            }
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Verify manifest has appropriate reasons
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                # Should have different reason types
                assert "Semantic match" in manifest or "Dependency" in manifest or "Transitive dependency" in manifest
    
    def test_file_read_error_handling(self):
        """Test that file read errors are handled appropriately.
        
        **Validates: Requirements 7.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Try to pack non-existent file
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 0
            }
            importance_scores = {"nonexistent.py": 0.5}
            
            # Should raise IOError for non-existent file
            with pytest.raises((IOError, FileNotFoundError)):
                packer.pack(["nonexistent.py"], tmpdir, metadata, importance_scores)
    
    def test_manifest_formatting(self):
        """Test that manifest is properly formatted as Markdown.
        
        **Validates: Requirements 7.3, 7.4, 7.5, 7.6**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            file_path = "test.py"
            full_path = os.path.join(tmpdir, file_path)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write("# test\n")
            
            # Pack file
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 10
            }
            importance_scores = {file_path: 0.5}
            
            zip_bytes = packer.pack([file_path], tmpdir, metadata, importance_scores)
            
            # Verify manifest is valid Markdown
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                # Check Markdown headers
                assert "# Review Context" in manifest or "# " in manifest
                assert "## " in manifest  # Section headers
                
                # Check Markdown table
                assert "|" in manifest  # Table separator
                assert "---" in manifest  # Table header separator
                
                # Check Markdown list
                assert "1." in manifest or "-" in manifest  # Numbered or bullet list
    
    def test_multiple_files_with_same_score(self):
        """Test handling of multiple files with identical scores.
        
        **Validates: Requirements 7.6**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = ["file1.py", "file2.py", "file3.py"]
            for file_path in files:
                full_path = os.path.join(tmpdir, file_path)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write("# test\n")
            
            # Pack files with same score
            packer = ZIPPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 3,
                "total_tokens": 50
            }
            importance_scores = {fp: 0.5 for fp in files}
            
            zip_bytes = packer.pack(files, tmpdir, metadata, importance_scores)
            
            # Verify all files are in manifest
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                for file_path in files:
                    assert file_path in manifest, \
                        f"File '{file_path}' should be in manifest"
                    assert "0.5000" in manifest, \
                        "Score should be in manifest"
