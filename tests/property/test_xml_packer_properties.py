"""Property-based tests for XML Packer.

These tests validate universal properties that should hold for all valid inputs.
"""

import os
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from lxml import etree

from ws_ctx_engine.packer import XMLPacker


# Custom strategies for generating test data
@st.composite
def xml_safe_text_strategy(draw):
    """Generate XML-safe text without control characters."""
    # XML 1.0 allows: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # Exclude control characters that are not allowed in XML
    text = draw(st.text(
        alphabet=st.characters(
            blacklist_categories=('Cs',),  # Exclude surrogates
            blacklist_characters='\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f'
                                '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
        ),
        max_size=200
    ))
    return text


@st.composite
def file_name_strategy(draw):
    """Generate valid file names without path separators or special characters."""
    name = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        ),
        min_size=1,
        max_size=50
    ))
    # Ensure it doesn't start with a dot or dash
    if name and name[0] in '.-':
        name = 'f' + name
    return name + '.py'


@st.composite
def metadata_strategy(draw):
    """Generate valid metadata dictionaries."""
    repo_name = draw(xml_safe_text_strategy())
    if not repo_name:
        repo_name = "test-repo"
    file_count = draw(st.integers(min_value=0, max_value=1000))
    total_tokens = draw(st.integers(min_value=0, max_value=1000000))
    
    metadata = {
        "repo_name": repo_name,
        "file_count": file_count,
        "total_tokens": total_tokens
    }
    
    # Optionally add query
    if draw(st.booleans()):
        query = draw(xml_safe_text_strategy())
        if query:  # Only add if not empty
            metadata["query"] = query
    
    # Optionally add changed_files
    if draw(st.booleans()):
        changed_files = draw(st.lists(
            file_name_strategy(),
            max_size=10
        ))
        if changed_files:  # Only add if not empty
            metadata["changed_files"] = changed_files
    
    return metadata


@st.composite
def file_content_strategy(draw):
    """Generate file content with various special characters."""
    # Include special XML characters that need escaping, but exclude control chars
    content = draw(st.text(
        alphabet=st.characters(
            blacklist_categories=('Cs',),  # Exclude surrogates
            blacklist_characters='\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f'
                                '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
        ),
        max_size=1000
    ))
    return content


class TestXMLPackerProperties:
    """Property-based tests for XMLPacker."""
    
    @given(metadata_strategy(), st.lists(file_name_strategy(), min_size=1, max_size=10))
    def test_property_xml_generation_completeness(self, metadata, file_names):
        """Property 17: XML generation SHALL include all required elements.
        
        **Validates: Requirements 6.1, 6.2, 6.3, 6.5**
        
        For any valid metadata and file list, the generated XML SHALL contain:
        - Root <repository> element
        - <metadata> section with name, file_count, total_tokens
        - <files> section with all file entries
        - Each <file> element with path and tokens attributes
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file_paths = []
            for file_name in file_names:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Test content for {file_name}\n")
                file_paths.append(file_name)
            
            # Pack files
            packer = XMLPacker()
            xml_output = packer.pack(file_paths, tmpdir, metadata)
            
            # Parse XML
            root = etree.fromstring(xml_output.encode('utf-8'))
            
            # Verify root element
            assert root.tag == "repository", \
                f"Root element must be 'repository', got '{root.tag}'"
            
            # Verify metadata section exists
            metadata_elem = root.find("metadata")
            assert metadata_elem is not None, \
                "XML must contain <metadata> element"
            
            # Verify metadata fields
            name_elem = metadata_elem.find("name")
            assert name_elem is not None, \
                "Metadata must contain <name> element"
            assert name_elem.text == str(metadata["repo_name"]), \
                f"Name mismatch: expected '{metadata['repo_name']}', got '{name_elem.text}'"
            
            file_count_elem = metadata_elem.find("file_count")
            assert file_count_elem is not None, \
                "Metadata must contain <file_count> element"
            assert file_count_elem.text == str(metadata["file_count"]), \
                f"File count mismatch: expected '{metadata['file_count']}', got '{file_count_elem.text}'"
            
            total_tokens_elem = metadata_elem.find("total_tokens")
            assert total_tokens_elem is not None, \
                "Metadata must contain <total_tokens> element"
            assert total_tokens_elem.text == str(metadata["total_tokens"]), \
                f"Total tokens mismatch: expected '{metadata['total_tokens']}', got '{total_tokens_elem.text}'"
            
            # Verify files section exists
            files_elem = root.find("files")
            assert files_elem is not None, \
                "XML must contain <files> element"
            
            # Verify all files are present
            file_elems = files_elem.findall("file")
            assert len(file_elems) == len(file_paths), \
                f"Expected {len(file_paths)} file elements, got {len(file_elems)}"
            
            # Verify each file element has required attributes
            for file_elem in file_elems:
                assert "path" in file_elem.attrib, \
                    "File element must have 'path' attribute"
                assert "tokens" in file_elem.attrib, \
                    "File element must have 'tokens' attribute"
                
                # Verify tokens is a valid integer
                try:
                    tokens = int(file_elem.attrib["tokens"])
                    assert tokens >= 0, \
                        f"Token count must be non-negative, got {tokens}"
                except ValueError:
                    pytest.fail(f"Token count must be an integer, got '{file_elem.attrib['tokens']}'")
    
    @given(file_content_strategy())
    def test_property_xml_character_escaping(self, content):
        """Property 18: XML character escaping SHALL handle special characters correctly.
        
        **Validates: Requirements 6.4**
        
        For any file content containing special XML characters (<, >, &, ', "),
        the generated XML SHALL properly escape them so the XML remains valid.
        
        Note: XML parsers normalize line endings (\r and \r\n to \n) per XML spec.
        """
        # Create temporary directory with test file
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = "test.txt"
            full_path = os.path.join(tmpdir, file_path)
            
            # Write content with special characters
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Pack file
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 1,
                "total_tokens": 100
            }
            xml_output = packer.pack([file_path], tmpdir, metadata)
            
            # Parse XML - this will fail if escaping is incorrect
            try:
                root = etree.fromstring(xml_output.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                pytest.fail(f"XML parsing failed due to improper escaping: {e}")
            
            # Verify we can extract the original content
            files_elem = root.find("files")
            file_elem = files_elem.find("file")
            extracted_content = file_elem.text or ""
            
            # XML parsers normalize line endings: \r and \r\n become \n
            # This is per XML 1.0 spec section 2.11
            expected_content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Content should match after normalization (lxml handles escaping/unescaping)
            assert extracted_content == expected_content, \
                "Extracted content does not match original after XML round-trip and line ending normalization"
    
    @given(metadata_strategy(), st.lists(file_name_strategy(), min_size=1, max_size=5))
    def test_property_xml_round_trip_validity(self, metadata, file_names):
        """Property 19: XML round-trip SHALL produce valid parseable XML.
        
        **Validates: Requirements 6.7**
        
        For any valid input, the generated XML SHALL be parseable without errors
        and SHALL preserve all data through a parse-serialize round-trip.
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with various content
            file_paths = []
            for file_name in file_names:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"def test_{file_name}():\n    pass\n")
                file_paths.append(file_name)
            
            # Pack files
            packer = XMLPacker()
            xml_output = packer.pack(file_paths, tmpdir, metadata)
            
            # First parse - should succeed
            try:
                root1 = etree.fromstring(xml_output.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                pytest.fail(f"Initial XML parsing failed: {e}")
            
            # Serialize back to string
            xml_output2 = etree.tostring(root1, encoding="unicode")
            
            # Second parse - should also succeed
            try:
                root2 = etree.fromstring(xml_output2.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                pytest.fail(f"Round-trip XML parsing failed: {e}")
            
            # Verify structure is preserved
            assert root2.tag == "repository", \
                "Root element lost after round-trip"
            
            metadata_elem = root2.find("metadata")
            assert metadata_elem is not None, \
                "Metadata element lost after round-trip"
            
            files_elem = root2.find("files")
            assert files_elem is not None, \
                "Files element lost after round-trip"
            
            file_elems = files_elem.findall("file")
            assert len(file_elems) == len(file_paths), \
                f"File count changed after round-trip: {len(file_paths)} -> {len(file_elems)}"
    
    @given(metadata_strategy())
    def test_property_xml_metadata_types(self, metadata):
        """Property: Metadata values SHALL be properly converted to strings.
        
        **Validates: Requirements 6.2**
        
        For any metadata with integer or string values, all values SHALL be
        properly converted to string representation in the XML.
        """
        # Create temporary directory with one test file
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = "test.py"
            full_path = os.path.join(tmpdir, file_path)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write("# test\n")
            
            # Pack file
            packer = XMLPacker()
            xml_output = packer.pack([file_path], tmpdir, metadata)
            
            # Parse XML
            root = etree.fromstring(xml_output.encode('utf-8'))
            metadata_elem = root.find("metadata")
            
            # Verify all metadata values are strings in XML
            for child in metadata_elem:
                assert isinstance(child.text, str), \
                    f"Metadata element '{child.tag}' text must be string, got {type(child.text)}"
    
    @given(st.lists(file_name_strategy(), min_size=0, max_size=10))
    def test_property_xml_handles_empty_file_list(self, file_names):
        """Property: XML generation SHALL handle empty file lists gracefully.
        
        **Validates: Requirements 6.1, 6.3**
        
        When no files are selected, the XML SHALL still be valid with an empty
        <files> section.
        """
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files but don't select them
            for file_name in file_names:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# test\n")
            
            # Pack with empty file list
            packer = XMLPacker()
            metadata = {
                "repo_name": "test-repo",
                "file_count": 0,
                "total_tokens": 0
            }
            xml_output = packer.pack([], tmpdir, metadata)
            
            # Parse XML
            try:
                root = etree.fromstring(xml_output.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                pytest.fail(f"XML parsing failed for empty file list: {e}")
            
            # Verify structure
            files_elem = root.find("files")
            assert files_elem is not None, \
                "Files element must exist even when empty"
            
            file_elems = files_elem.findall("file")
            assert len(file_elems) == 0, \
                f"Expected 0 file elements, got {len(file_elems)}"
    
    @given(metadata_strategy(), st.lists(file_name_strategy(), min_size=1, max_size=5))
    def test_property_xml_token_counts_non_negative(self, metadata, file_names):
        """Property: Token counts in XML SHALL always be non-negative integers.
        
        **Validates: Requirements 6.5**
        
        For any file, the tokens attribute SHALL be a non-negative integer.
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            file_paths = []
            for file_name in file_names:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Content for {file_name}\n")
                file_paths.append(file_name)
            
            # Pack files
            packer = XMLPacker()
            xml_output = packer.pack(file_paths, tmpdir, metadata)
            
            # Parse XML
            root = etree.fromstring(xml_output.encode('utf-8'))
            files_elem = root.find("files")
            
            # Check all token counts
            for file_elem in files_elem.findall("file"):
                tokens_str = file_elem.attrib.get("tokens")
                assert tokens_str is not None, \
                    "File element must have tokens attribute"
                
                try:
                    tokens = int(tokens_str)
                except ValueError:
                    pytest.fail(f"Token count must be an integer, got '{tokens_str}'")
                
                assert tokens >= 0, \
                    f"Token count must be non-negative, got {tokens}"
