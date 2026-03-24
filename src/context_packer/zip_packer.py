"""
ZIP output packer for Context Packer.

Generates ZIP archive with preserved directory structure and REVIEW_CONTEXT.md manifest.
"""

import io
import os
import zipfile
from typing import Any, Dict, List

import tiktoken

from .logger import get_logger


class ZIPPacker:
    """
    Packer that generates ZIP output with preserved file structure.
    
    The ZIP structure includes:
    - files/ directory containing all selected files with original structure
    - REVIEW_CONTEXT.md manifest in ZIP root with:
      - Repository metadata
      - List of files with importance scores
      - Inclusion explanations
      - Suggested reading order
    
    Example structure:
        context-pack.zip
        ├── files/
        │   ├── src/
        │   │   └── main.py
        │   └── tests/
        │       └── test_main.py
        └── REVIEW_CONTEXT.md
    """
    
    def __init__(self, encoding: str = "cl100k_base"):
        """
        Initialize ZIPPacker.
        
        Args:
            encoding: Tiktoken encoding name for token counting
        """
        self.logger = get_logger()
        self.encoding = tiktoken.get_encoding(encoding)
    
    def pack(
        self,
        selected_files: List[str],
        repo_path: str,
        metadata: Dict[str, Any],
        importance_scores: Dict[str, float]
    ) -> bytes:
        """
        Generate ZIP archive from selected files.
        
        Args:
            selected_files: List of file paths relative to repo_path
            repo_path: Absolute path to repository root
            metadata: Dictionary with repo_name, file_count, total_tokens, etc.
            importance_scores: Dictionary mapping file paths to importance scores
        
        Returns:
            ZIP archive as bytes
        
        Raises:
            IOError: If files cannot be read
            ValueError: If metadata is invalid
        """
        self.logger.info(f"Packing {len(selected_files)} files into ZIP format")
        
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all selected files under files/ directory
            for file_path in selected_files:
                self._add_file_to_zip(zip_file, file_path, repo_path)
            
            # Generate and add REVIEW_CONTEXT.md manifest
            manifest_content = self._generate_manifest(
                selected_files,
                repo_path,
                metadata,
                importance_scores
            )
            zip_file.writestr("REVIEW_CONTEXT.md", manifest_content)
        
        self.logger.info("ZIP packing complete")
        return zip_buffer.getvalue()
    
    def _add_file_to_zip(
        self,
        zip_file: zipfile.ZipFile,
        file_path: str,
        repo_path: str
    ) -> None:
        """
        Add a file to the ZIP archive under files/ directory.
        
        Args:
            zip_file: ZipFile object to add file to
            file_path: Relative path to file
            repo_path: Absolute path to repository root
        
        Raises:
            IOError: If file cannot be read
        """
        full_path = os.path.join(repo_path, file_path)
        zip_path = os.path.join("files", file_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            zip_file.writestr(zip_path, content)
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            self.logger.warning(f"UTF-8 decode failed for {file_path}, trying latin-1")
            with open(full_path, 'r', encoding='latin-1') as f:
                content = f.read()
            zip_file.writestr(zip_path, content)
        except Exception as e:
            self.logger.error(f"Failed to add {file_path} to ZIP: {e}")
            raise
    
    def _generate_manifest(
        self,
        selected_files: List[str],
        repo_path: str,
        metadata: Dict[str, Any],
        importance_scores: Dict[str, float]
    ) -> str:
        """
        Generate REVIEW_CONTEXT.md manifest content.
        
        Args:
            selected_files: List of file paths
            repo_path: Absolute path to repository root
            metadata: Repository metadata
            importance_scores: File importance scores
        
        Returns:
            Markdown content for manifest
        """
        lines = []
        
        # Header
        lines.append("# Review Context")
        lines.append("")
        
        # Repository metadata
        lines.append("## Repository Information")
        lines.append("")
        lines.append(f"- **Repository**: {metadata.get('repo_name', 'unknown')}")
        lines.append(f"- **Files Included**: {metadata.get('file_count', len(selected_files))}")
        lines.append(f"- **Total Tokens**: {metadata.get('total_tokens', 0):,}")
        
        # Optional query
        if metadata.get('query'):
            lines.append(f"- **Query**: {metadata['query']}")
        
        # Optional changed files
        if metadata.get('changed_files'):
            lines.append(f"- **Changed Files**: {', '.join(metadata['changed_files'])}")
        
        lines.append("")
        
        # Files with importance scores
        lines.append("## Included Files")
        lines.append("")
        lines.append("The following files were selected based on their importance scores:")
        lines.append("")
        
        # Sort files by importance score (descending)
        files_with_scores = [
            (file_path, importance_scores.get(file_path, 0.0))
            for file_path in selected_files
        ]
        files_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Create table
        lines.append("| File | Importance Score | Reason |")
        lines.append("|------|------------------|--------|")
        
        for file_path, score in files_with_scores:
            reason = self._get_inclusion_reason(file_path, score, metadata)
            lines.append(f"| `{file_path}` | {score:.4f} | {reason} |")
        
        lines.append("")
        
        # Suggested reading order
        lines.append("## Suggested Reading Order")
        lines.append("")
        lines.append("Files are listed in order of importance (highest first):")
        lines.append("")
        
        for i, (file_path, score) in enumerate(files_with_scores, 1):
            lines.append(f"{i}. `{file_path}` (score: {score:.4f})")
        
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*This context was generated by Context Packer*")
        lines.append("")
        
        return "\n".join(lines)
    
    def _get_inclusion_reason(
        self,
        file_path: str,
        score: float,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Determine why a file was included based on its score and metadata.
        
        Args:
            file_path: Path to the file
            score: Importance score
            metadata: Repository metadata
        
        Returns:
            Human-readable reason for inclusion
        """
        # Check if file was changed
        changed_files = metadata.get('changed_files', [])
        if changed_files is not None and file_path in changed_files:
            return "Changed file"
        
        # Infer reason from score
        # High scores (>0.7) typically indicate semantic match
        # Medium scores (0.3-0.7) typically indicate dependencies
        # Low scores (<0.3) typically indicate transitive dependencies
        if score > 0.7:
            return "Semantic match"
        elif score > 0.3:
            return "Dependency"
        else:
            return "Transitive dependency"
