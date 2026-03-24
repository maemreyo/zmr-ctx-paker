"""Property-based tests for ZIP Packer.

These tests validate universal properties that should hold for all valid inputs.
"""

import io
import os
import tempfile
import zipfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from context_packer.zip_packer import ZIPPacker


# Custom strategies for generating test data
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
def directory_structure_strategy(draw):
    """Generate a list of file paths with directory structure."""
    # Generate some directories
    num_dirs = draw(st.integers(min_value=0, max_value=3))
    dirs = []
    for _ in range(num_dirs):
        dir_name = draw(st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='-_'
            ),
            min_size=1,
            max_size=20
        ))
        if dir_name and dir_name[0] not in '.-':
            dirs.append(dir_name)
    
    # Generate files in various directories
    num_files = draw(st.integers(min_value=1, max_value=10))
    file_paths = []
    
    for _ in range(num_files):
        # Randomly choose to put file in root or subdirectory
        if dirs and draw(st.booleans()):
            dir_path = draw(st.sampled_from(dirs))
            file_name = draw(file_name_strategy())
            file_paths.append(os.path.join(dir_path, file_name))
        else:
            file_paths.append(draw(file_name_strategy()))
    
    return file_paths


@st.composite
def metadata_strategy(draw):
    """Generate valid metadata dictionaries."""
    repo_name = draw(st.text(min_size=1, max_size=50))
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
        query = draw(st.text(max_size=100))
        if query:
            metadata["query"] = query
    
    # Optionally add changed_files
    if draw(st.booleans()):
        changed_files = draw(st.lists(
            file_name_strategy(),
            max_size=5
        ))
        if changed_files:
            metadata["changed_files"] = changed_files
    
    return metadata


@st.composite
def importance_scores_strategy(draw, file_paths):
    """Generate importance scores for given file paths."""
    scores = {}
    for file_path in file_paths:
        score = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
        scores[file_path] = score
    return scores


class TestZIPPackerProperties:
    """Property-based tests for ZIPPacker."""
    
    @given(directory_structure_strategy(), metadata_strategy())
    def test_property_zip_structure_preservation(self, file_paths, metadata):
        """Property 20: ZIP structure SHALL preserve directory structure under files/.
        
        **Validates: Requirements 7.1, 7.2, 7.3**
        
        For any set of files with directory structure, the ZIP SHALL:
        - Preserve the original directory structure
        - Place all files under a files/ directory
        - Include REVIEW_CONTEXT.md in the ZIP root
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with directory structure
            for file_path in file_paths:
                full_path = os.path.join(tmpdir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Content for {file_path}\n")
            
            # Generate importance scores
            importance_scores = {fp: 0.5 for fp in file_paths}
            
            # Pack files
            packer = ZIPPacker()
            zip_bytes = packer.pack(file_paths, tmpdir, metadata, importance_scores)
            
            # Verify ZIP is valid
            assert isinstance(zip_bytes, bytes), \
                "pack() must return bytes"
            assert len(zip_bytes) > 0, \
                "ZIP archive must not be empty"
            
            # Open and verify ZIP structure
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_contents = zip_file.namelist()
                
                # Verify REVIEW_CONTEXT.md exists in root
                assert "REVIEW_CONTEXT.md" in zip_contents, \
                    "ZIP must contain REVIEW_CONTEXT.md in root"
                
                # Verify all files are under files/ directory
                for file_path in file_paths:
                    expected_zip_path = os.path.join("files", file_path)
                    # Normalize path separators for comparison
                    expected_zip_path = expected_zip_path.replace(os.sep, '/')
                    
                    # Check if file exists in ZIP
                    matching_paths = [
                        zp for zp in zip_contents
                        if zp.replace('\\', '/') == expected_zip_path
                    ]
                    
                    assert len(matching_paths) > 0, \
                        f"File '{file_path}' must be in ZIP as 'files/{file_path}', " \
                        f"but not found. ZIP contents: {zip_contents}"
                
                # Verify directory structure is preserved
                for file_path in file_paths:
                    if os.sep in file_path or '/' in file_path:
                        # File is in a subdirectory
                        dir_parts = file_path.replace(os.sep, '/').split('/')[:-1]
                        
                        # Check that intermediate directories are preserved
                        for i in range(1, len(dir_parts) + 1):
                            partial_dir = '/'.join(['files'] + dir_parts[:i])
                            
                            # In ZIP, directories may or may not have explicit entries
                            # But files in those directories must exist
                            files_in_dir = [
                                zp for zp in zip_contents
                                if zp.replace('\\', '/').startswith(partial_dir + '/')
                            ]
                            
                            assert len(files_in_dir) > 0, \
                                f"Directory structure not preserved: {partial_dir} has no files"
    
    @given(directory_structure_strategy(), metadata_strategy())
    def test_property_zip_manifest_completeness(self, file_paths, metadata):
        """Property 21: ZIP manifest SHALL include all required information.
        
        **Validates: Requirements 7.4, 7.5, 7.6**
        
        For any set of files, the REVIEW_CONTEXT.md manifest SHALL include:
        - All file paths with importance scores
        - Explanation for why each file was included
        - Suggested reading order based on importance
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for file_path in file_paths:
                full_path = os.path.join(tmpdir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Content for {file_path}\n")
            
            # Generate importance scores with variety
            importance_scores = {}
            for i, fp in enumerate(file_paths):
                # Create varied scores to test different inclusion reasons
                if i % 3 == 0:
                    importance_scores[fp] = 0.9  # High score - semantic match
                elif i % 3 == 1:
                    importance_scores[fp] = 0.5  # Medium score - dependency
                else:
                    importance_scores[fp] = 0.2  # Low score - transitive dependency
            
            # Pack files
            packer = ZIPPacker()
            zip_bytes = packer.pack(file_paths, tmpdir, metadata, importance_scores)
            
            # Extract and verify manifest
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest_content = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                # Verify manifest contains repository metadata
                assert metadata["repo_name"] in manifest_content, \
                    "Manifest must include repository name"
                assert str(metadata.get("file_count", len(file_paths))) in manifest_content, \
                    "Manifest must include file count"
                assert str(metadata.get("total_tokens", 0)) in manifest_content or \
                       f"{metadata.get('total_tokens', 0):,}" in manifest_content, \
                    "Manifest must include total tokens"
                
                # Verify all files are listed with scores
                for file_path, score in importance_scores.items():
                    assert file_path in manifest_content, \
                        f"Manifest must list file '{file_path}'"
                    
                    # Score should appear in manifest (formatted to 4 decimal places)
                    score_str = f"{score:.4f}"
                    assert score_str in manifest_content, \
                        f"Manifest must include importance score {score_str} for '{file_path}'"
                
                # Verify inclusion reasons are present
                # At least one of these reason keywords should appear
                reason_keywords = ["Semantic match", "Dependency", "Transitive dependency", "Changed file"]
                has_reason = any(keyword in manifest_content for keyword in reason_keywords)
                assert has_reason, \
                    f"Manifest must include inclusion reasons. Expected one of {reason_keywords}"
                
                # Verify suggested reading order section exists
                assert "Suggested Reading Order" in manifest_content or \
                       "Reading Order" in manifest_content, \
                    "Manifest must include suggested reading order section"
                
                # Verify files are listed in reading order
                # The manifest should list files in order of importance
                sorted_files = sorted(
                    importance_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                # Check that at least the top files appear in order
                if len(sorted_files) >= 2:
                    top_file = sorted_files[0][0]
                    second_file = sorted_files[1][0]
                    
                    # Find positions in manifest
                    top_pos = manifest_content.find(top_file)
                    second_pos = manifest_content.find(second_file)
                    
                    # In the reading order section, top file should appear before second
                    # (though they may also appear in the table earlier)
                    reading_order_section = manifest_content.split("Suggested Reading Order")[-1] if "Suggested Reading Order" in manifest_content else manifest_content.split("Reading Order")[-1]
                    
                    top_pos_in_order = reading_order_section.find(top_file)
                    second_pos_in_order = reading_order_section.find(second_file)
                    
                    if top_pos_in_order >= 0 and second_pos_in_order >= 0:
                        assert top_pos_in_order < second_pos_in_order, \
                            "Files in reading order should be sorted by importance (highest first)"
    
    @given(directory_structure_strategy(), metadata_strategy())
    def test_property_zip_content_preservation(self, file_paths, metadata):
        """Property: ZIP SHALL preserve file content exactly.
        
        **Validates: Requirements 7.1, 7.2**
        
        For any file content, the ZIP SHALL preserve it exactly without
        modification or corruption.
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with specific content
            file_contents = {}
            for file_path in file_paths:
                full_path = os.path.join(tmpdir, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                content = f"# Test file: {file_path}\n" \
                         f"def test_{file_path.replace('/', '_').replace('.', '_')}():\n" \
                         f"    pass\n"
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                file_contents[file_path] = content
            
            # Generate importance scores
            importance_scores = {fp: 0.5 for fp in file_paths}
            
            # Pack files
            packer = ZIPPacker()
            zip_bytes = packer.pack(file_paths, tmpdir, metadata, importance_scores)
            
            # Verify content is preserved
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                for file_path, original_content in file_contents.items():
                    zip_path = os.path.join("files", file_path).replace(os.sep, '/')
                    
                    # Find the file in ZIP (handle path separator differences)
                    matching_paths = [
                        zp for zp in zip_file.namelist()
                        if zp.replace('\\', '/') == zip_path
                    ]
                    
                    assert len(matching_paths) > 0, \
                        f"File '{file_path}' not found in ZIP"
                    
                    extracted_content = zip_file.read(matching_paths[0]).decode('utf-8')
                    
                    assert extracted_content == original_content, \
                        f"Content mismatch for '{file_path}': " \
                        f"expected {len(original_content)} chars, " \
                        f"got {len(extracted_content)} chars"
    
    @given(st.lists(file_name_strategy(), min_size=1, max_size=10), metadata_strategy())
    def test_property_zip_importance_score_ordering(self, file_names, metadata):
        """Property: Files in manifest SHALL be ordered by importance score.
        
        **Validates: Requirements 7.6**
        
        For any set of files with different importance scores, the manifest
        SHALL list them in descending order of importance.
        """
        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            for file_name in file_names:
                file_path = os.path.join(tmpdir, file_name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {file_name}\n")
            
            # Generate importance scores with clear ordering
            importance_scores = {}
            for i, file_name in enumerate(file_names):
                # Assign scores in reverse order to test sorting
                importance_scores[file_name] = 1.0 - (i * 0.1)
            
            # Pack files
            packer = ZIPPacker()
            zip_bytes = packer.pack(file_names, tmpdir, metadata, importance_scores)
            
            # Extract and verify manifest ordering
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                manifest_content = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                
                # Extract the reading order section to check ordering
                # (files can appear multiple times in manifest - in metadata and in table)
                if "Suggested Reading Order" in manifest_content:
                    reading_section = manifest_content.split("Suggested Reading Order")[1]
                elif "Reading Order" in manifest_content:
                    reading_section = manifest_content.split("Reading Order")[1]
                else:
                    reading_section = manifest_content
                
                # Extract file positions in reading order section
                file_positions = {}
                for file_name in file_names:
                    pos = reading_section.find(file_name)
                    if pos >= 0:
                        file_positions[file_name] = pos
                
                # Verify files appear in order of importance
                sorted_by_score = sorted(
                    importance_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                # Check that files appear in descending score order in reading section
                prev_pos = -1
                for file_name, score in sorted_by_score:
                    if file_name in file_positions:
                        curr_pos = file_positions[file_name]
                        # Position should increase (files with higher scores appear first)
                        assert curr_pos > prev_pos, \
                            f"File '{file_name}' (score {score}) appears before " \
                            f"a file with higher score in reading order section"
                        prev_pos = curr_pos
    
    @given(metadata_strategy())
    def test_property_zip_handles_empty_file_list(self, metadata):
        """Property: ZIP generation SHALL handle empty file lists gracefully.
        
        **Validates: Requirements 7.1, 7.3**
        
        When no files are selected, the ZIP SHALL still be valid with:
        - Empty files/ directory
        - REVIEW_CONTEXT.md manifest
        """
        # Create temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Pack with empty file list
            packer = ZIPPacker()
            importance_scores = {}
            zip_bytes = packer.pack([], tmpdir, metadata, importance_scores)
            
            # Verify ZIP is valid
            assert isinstance(zip_bytes, bytes), \
                "pack() must return bytes even for empty file list"
            assert len(zip_bytes) > 0, \
                "ZIP archive must not be empty even with no files"
            
            # Verify ZIP structure
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
                zip_contents = zip_file.namelist()
                
                # Manifest must exist
                assert "REVIEW_CONTEXT.md" in zip_contents, \
                    "ZIP must contain REVIEW_CONTEXT.md even with no files"
                
                # Verify manifest is readable
                manifest_content = zip_file.read("REVIEW_CONTEXT.md").decode('utf-8')
                assert len(manifest_content) > 0, \
                    "Manifest must not be empty"
                assert metadata["repo_name"] in manifest_content, \
                    "Manifest must include repository metadata"
