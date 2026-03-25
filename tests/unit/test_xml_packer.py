"""Unit tests for XML Packer.

These tests validate specific examples and edge cases for XML generation.
"""

import os
import tempfile

import pytest
from lxml import etree

from ws_ctx_engine.packer import XMLPacker


class TestXMLPacker:
    """Unit tests for XMLPacker class."""
    
    def test_xml_output_is_valid_and_well_formed(self):
        """Test that XML output is valid and well-formed.
        
        **Validates: Requirements 6.1, 6.7**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = os.path.join(tmpdir, "test1.py")
            with open(file1, 'w', encoding='utf-8') as f:
                f.write("def hello():\n    print('Hello')\n")
            
            file2 = os.path.join(tmpdir, "test2.py")
            with open(file2, 'w', encoding='utf-8') as f:
                f.write("def world():\n    print('World')\n")
            
            # Pack files
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 2,
                "total_tokens": 50
            }
            xml_output = packer.pack(["test1.py", "test2.py"], tmpdir, metadata)
            
            # Verify XML is valid
            try:
                root = etree.fromstring(xml_output.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                pytest.fail(f"Generated XML is not valid: {e}")
            
            # Verify well-formed structure
            assert root.tag == "repository"
            assert root.find("metadata") is not None
            assert root.find("files") is not None
    
    def test_metadata_header_is_correct(self):
        """Test that metadata header contains correct information.
        
        **Validates: Requirements 6.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Test file\n")
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "my-awesome-repo",
                "file_count": 42,
                "total_tokens": 95000,
                "query": "find authentication code",
                "changed_files": ["auth.py", "login.py"],
                "index_health": {
                    "status": "current",
                    "files_indexed": 42,
                    "index_built_at": "2026-03-25T10:30:00Z",
                    "vcs": "git",
                },
            }
            xml_output = packer.pack(["test.py"], tmpdir, metadata)
            
            # Parse and verify metadata
            root = etree.fromstring(xml_output.encode('utf-8'))
            metadata_elem = root.find("metadata")
            
            # Check required fields
            assert metadata_elem.find("name").text == "my-awesome-repo"
            assert metadata_elem.find("file_count").text == "42"
            assert metadata_elem.find("total_tokens").text == "95000"
            
            # Check optional fields
            assert metadata_elem.find("query").text == "find authentication code"
            assert metadata_elem.find("changed_files").text == "auth.py, login.py"

            index_health = metadata_elem.find("index_health")
            assert index_health is not None
            assert index_health.find("status").text == "current"
            assert index_health.find("files_indexed").text == "42"
            assert index_health.find("index_built_at").text == "2026-03-25T10:30:00Z"
            assert index_health.find("vcs").text == "git"
    
    def test_file_tags_include_paths_and_token_counts(self):
        """Test that file tags include paths and token counts.
        
        **Validates: Requirements 6.3, 6.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = os.path.join(tmpdir, "src", "main.py")
            os.makedirs(os.path.dirname(file1), exist_ok=True)
            with open(file1, 'w', encoding='utf-8') as f:
                f.write("def main():\n    pass\n")
            
            file2 = os.path.join(tmpdir, "tests", "test_main.py")
            os.makedirs(os.path.dirname(file2), exist_ok=True)
            with open(file2, 'w', encoding='utf-8') as f:
                f.write("def test_main():\n    assert True\n")
            
            # Pack files
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 2,
                "total_tokens": 100
            }
            xml_output = packer.pack(
                ["src/main.py", "tests/test_main.py"],
                tmpdir,
                metadata
            )
            
            # Parse and verify file elements
            root = etree.fromstring(xml_output.encode('utf-8'))
            files_elem = root.find("files")
            file_elems = files_elem.findall("file")
            
            assert len(file_elems) == 2
            
            # Check first file
            file1_elem = file_elems[0]
            assert file1_elem.attrib["path"] == "src/main.py"
            assert "tokens" in file1_elem.attrib
            assert int(file1_elem.attrib["tokens"]) > 0
            
            # Check second file
            file2_elem = file_elems[1]
            assert file2_elem.attrib["path"] == "tests/test_main.py"
            assert "tokens" in file2_elem.attrib
            assert int(file2_elem.attrib["tokens"]) > 0
    
    def test_special_characters_are_escaped(self):
        """Test that special XML characters are properly escaped.
        
        **Validates: Requirements 6.4**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with special XML characters
            file_path = os.path.join(tmpdir, "special.py")
            special_content = '''def test():
    x = 5 < 10  # Less than
    y = 10 > 5  # Greater than
    z = "Hello & goodbye"  # Ampersand
    a = 'Single \\'quotes\\''  # Single quotes
    b = "Double \\"quotes\\""  # Double quotes
'''
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(special_content)
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 50
            }
            xml_output = packer.pack(["special.py"], tmpdir, metadata)
            
            # Parse XML - should succeed if escaping is correct
            try:
                root = etree.fromstring(xml_output.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                pytest.fail(f"XML parsing failed due to improper escaping: {e}")
            
            # Verify content is preserved
            files_elem = root.find("files")
            file_elem = files_elem.find("file")
            extracted_content = file_elem.text
            
            assert extracted_content == special_content
            assert "<" in extracted_content
            assert ">" in extracted_content
            assert "&" in extracted_content
            assert "'" in extracted_content
            assert '"' in extracted_content
    
    def test_empty_file_handling(self):
        """Test that empty files are handled correctly.
        
        **Validates: Requirements 6.1, 6.3, 6.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty file
            file_path = os.path.join(tmpdir, "empty.py")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("")
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 0
            }
            xml_output = packer.pack(["empty.py"], tmpdir, metadata)
            
            # Parse and verify
            root = etree.fromstring(xml_output.encode('utf-8'))
            files_elem = root.find("files")
            file_elem = files_elem.find("file")
            
            assert file_elem.attrib["path"] == "empty.py"
            assert file_elem.attrib["tokens"] == "0"
            assert (file_elem.text or "") == ""
    
    def test_unicode_content_handling(self):
        """Test that Unicode content is handled correctly.
        
        **Validates: Requirements 6.1, 6.4**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with Unicode content
            file_path = os.path.join(tmpdir, "unicode.py")
            unicode_content = '''# -*- coding: utf-8 -*-
def greet():
    print("Hello 世界")  # Chinese
    print("Привет мир")  # Russian
    print("مرحبا بالعالم")  # Arabic
    print("🎉🎊🎈")  # Emojis
'''
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(unicode_content)
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 100
            }
            xml_output = packer.pack(["unicode.py"], tmpdir, metadata)
            
            # Parse and verify
            root = etree.fromstring(xml_output.encode('utf-8'))
            files_elem = root.find("files")
            file_elem = files_elem.find("file")
            extracted_content = file_elem.text
            
            assert extracted_content == unicode_content
            assert "世界" in extracted_content
            assert "Привет" in extracted_content
            assert "مرحبا" in extracted_content
            assert "🎉" in extracted_content
    
    def test_large_file_handling(self):
        """Test that large files are handled correctly.
        
        **Validates: Requirements 6.1, 6.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create large file
            file_path = os.path.join(tmpdir, "large.py")
            large_content = "# Line {}\n" * 10000
            large_content = "".join([f"# Line {i}\n" for i in range(10000)])
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(large_content)
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 50000
            }
            xml_output = packer.pack(["large.py"], tmpdir, metadata)
            
            # Parse and verify
            root = etree.fromstring(xml_output.encode('utf-8'))
            files_elem = root.find("files")
            file_elem = files_elem.find("file")
            
            assert file_elem.attrib["path"] == "large.py"
            tokens = int(file_elem.attrib["tokens"])
            assert tokens > 0
            
            # Verify content is preserved
            extracted_content = file_elem.text
            assert extracted_content == large_content
    
    def test_multiple_files_ordering(self):
        """Test that multiple files maintain their order.
        
        **Validates: Requirements 6.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files
            file_names = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
            for file_name in file_names:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {file_name}\n")
            
            # Pack files
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": len(file_names),
                "total_tokens": 100
            }
            xml_output = packer.pack(file_names, tmpdir, metadata)
            
            # Parse and verify order
            root = etree.fromstring(xml_output.encode('utf-8'))
            files_elem = root.find("files")
            file_elems = files_elem.findall("file")
            
            assert len(file_elems) == len(file_names)
            
            for i, file_elem in enumerate(file_elems):
                assert file_elem.attrib["path"] == file_names[i], \
                    f"File order not preserved: expected {file_names[i]}, got {file_elem.attrib['path']}"
    
    def test_missing_optional_metadata_fields(self):
        """Test that optional metadata fields can be omitted.
        
        **Validates: Requirements 6.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Test\n")
            
            # Pack file with minimal metadata
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 10
                # No query or changed_files
            }
            xml_output = packer.pack(["test.py"], tmpdir, metadata)
            
            # Parse and verify
            root = etree.fromstring(xml_output.encode('utf-8'))
            metadata_elem = root.find("metadata")
            
            # Required fields should exist
            assert metadata_elem.find("name") is not None
            assert metadata_elem.find("file_count") is not None
            assert metadata_elem.find("total_tokens") is not None
            
            # Optional fields should not exist
            assert metadata_elem.find("query") is None
            assert metadata_elem.find("changed_files") is None
    
    def test_xml_declaration_present(self):
        """Test that XML declaration is present in output.
        
        **Validates: Requirements 6.7**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# Test\n")
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 10
            }
            xml_output = packer.pack(["test.py"], tmpdir, metadata)
            
            # Verify XML declaration
            assert xml_output.startswith("<?xml"), \
                "XML output should start with XML declaration"
    
    def test_file_read_error_handling(self):
        """Test that file read errors are handled appropriately.
        
        **Validates: Requirements 6.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pack non-existent file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 0
            }
            
            # Should raise IOError for non-existent file
            with pytest.raises((IOError, FileNotFoundError)):
                packer.pack(["nonexistent.py"], tmpdir, metadata)
