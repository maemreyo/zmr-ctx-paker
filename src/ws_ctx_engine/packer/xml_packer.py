"""
XML output packer for ws-ctx-engine.

Generates Repomix-style XML output with metadata and file contents.
"""

import os
from typing import Any, Dict, List, Optional

import tiktoken
from lxml import etree

from ..logger import get_logger


class XMLPacker:
    """
    Packer that generates Repomix-style XML output.
    
    The XML structure includes:
    - Metadata header (repo name, file count, total tokens)
    - Individual file entries with paths and token counts
    - Properly escaped file contents
    
    Example output:
        <repository>
          <metadata>
            <name>my-repo</name>
            <file_count>42</file_count>
            <total_tokens>95000</total_tokens>
          </metadata>
          <files>
            <file path="src/main.py" tokens="1234">
              <![CDATA[...file content...]]>
            </file>
          </files>
        </repository>
    """
    
    def __init__(self, encoding: str = "cl100k_base"):
        """
        Initialize XMLPacker.
        
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
        secret_scanner: Optional[Any] = None,
    ) -> str:
        """
        Generate XML output from selected files.
        
        Args:
            selected_files: List of file paths relative to repo_path
            repo_path: Absolute path to repository root
            metadata: Dictionary with repo_name, file_count, total_tokens, etc.
        
        Returns:
            XML string with Repomix-style structure
        
        Raises:
            IOError: If files cannot be read
            ValueError: If metadata is invalid
        """
        self.logger.info(f"Packing {len(selected_files)} files into XML format")
        
        # Create root element
        root = etree.Element("repository")
        
        # Add metadata section
        metadata_elem = self._create_metadata_element(metadata)
        root.append(metadata_elem)
        
        # Add files section
        files_elem = etree.Element("files")
        
        for file_path in selected_files:
            file_elem = self._create_file_element(file_path, repo_path, secret_scanner=secret_scanner)
            files_elem.append(file_elem)
        
        root.append(files_elem)
        
        # Generate XML string with pretty printing
        # Note: xml_declaration=True requires encoding to be bytes, not unicode
        xml_bytes = etree.tostring(
            root,
            encoding="utf-8",
            pretty_print=True,
            xml_declaration=True
        )
        
        # Convert bytes to string
        xml_string = xml_bytes.decode('utf-8')
        
        self.logger.info("XML packing complete")
        return xml_string
    
    def _create_metadata_element(self, metadata: Dict[str, Any]) -> etree.Element:
        """
        Create metadata XML element.
        
        Args:
            metadata: Dictionary with repo_name, file_count, total_tokens
        
        Returns:
            XML element with metadata
        """
        metadata_elem = etree.Element("metadata")
        
        # Add repo name
        name_elem = etree.SubElement(metadata_elem, "name")
        name_elem.text = str(metadata.get("repo_name", "unknown"))
        
        # Add file count
        file_count_elem = etree.SubElement(metadata_elem, "file_count")
        file_count_elem.text = str(metadata.get("file_count", 0))
        
        # Add total tokens
        total_tokens_elem = etree.SubElement(metadata_elem, "total_tokens")
        total_tokens_elem.text = str(metadata.get("total_tokens", 0))
        
        # Add optional query if present
        if "query" in metadata and metadata["query"]:
            query_elem = etree.SubElement(metadata_elem, "query")
            query_elem.text = str(metadata["query"])
        
        # Add optional changed files if present
        if "changed_files" in metadata and metadata["changed_files"]:
            changed_elem = etree.SubElement(metadata_elem, "changed_files")
            changed_elem.text = ", ".join(metadata["changed_files"])

        index_health = metadata.get("index_health")
        if isinstance(index_health, dict):
            index_health_elem = etree.SubElement(metadata_elem, "index_health")
            for field in ("status", "stale_reason", "files_indexed", "index_built_at", "vcs"):
                value = index_health.get(field)
                if value is None:
                    continue
                field_elem = etree.SubElement(index_health_elem, field)
                field_elem.text = str(value)
        
        return metadata_elem
    
    def _create_file_element(
        self,
        file_path: str,
        repo_path: str,
        secret_scanner: Optional[Any] = None,
    ) -> etree.Element:
        """
        Create file XML element with content.
        
        Args:
            file_path: Relative path to file
            repo_path: Absolute path to repository root
        
        Returns:
            XML element with file content
        
        Raises:
            IOError: If file cannot be read
        """
        full_path = os.path.join(repo_path, file_path)
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding as fallback
            self.logger.warning(f"UTF-8 decode failed for {file_path}, trying latin-1")
            with open(full_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            raise
        
        if secret_scanner is not None:
            scan_result = secret_scanner.scan(file_path)
            if scan_result.secrets_detected:
                detected = ", ".join(scan_result.secrets_detected)
                content = f"[REDACTED: detected secrets ({detected})]"

        # Count tokens
        token_count = len(self.encoding.encode(content))
        
        # Create file element with attributes
        file_elem = etree.Element("file", path=file_path, tokens=str(token_count))
        
        # Add content as CDATA to preserve special characters
        # lxml automatically escapes content, but CDATA is cleaner for code
        file_elem.text = content
        
        return file_elem
