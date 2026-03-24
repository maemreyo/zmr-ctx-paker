"""Pretty printer for formatting Code_Chunks back to source code.

This module provides functionality to format Code_Chunks back to valid source code
for round-trip testing. It supports Python, JavaScript, and TypeScript.
"""

from typing import List

from ..logger import get_logger
from ..models import CodeChunk

logger = get_logger()


class PrettyPrinter:
    """Format Code_Chunks back to source code.
    
    This class takes Code_Chunks and formats them back to syntactically valid
    source code in the original language. It's primarily used for round-trip
    testing to verify that parse → print → parse produces equivalent structures.
    
    Supports:
    - Python
    - JavaScript
    - TypeScript
    """
    
    def format(self, chunks: List[CodeChunk]) -> str:
        """Format Code_Chunks back to source code.
        
        Takes a list of Code_Chunks and formats them back to valid source code
        in the appropriate language. Chunks are concatenated with appropriate
        spacing to maintain readability.
        
        Args:
            chunks: List of CodeChunk objects to format
        
        Returns:
            Formatted source code as a string
        
        Raises:
            ValueError: If chunks list is empty or contains unsupported language
        
        Example:
            >>> printer = PrettyPrinter()
            >>> chunks = [
            ...     CodeChunk(
            ...         path="test.py",
            ...         start_line=1,
            ...         end_line=3,
            ...         content="def hello():\\n    pass",
            ...         symbols_defined=["hello"],
            ...         symbols_referenced=[],
            ...         language="python"
            ...     )
            ... ]
            >>> code = printer.format(chunks)
            >>> print(code)
            def hello():
                pass
        """
        if not chunks:
            raise ValueError("Cannot format empty chunks list")
        
        # Group chunks by language
        language = chunks[0].language
        
        # Verify all chunks are same language
        for chunk in chunks:
            if chunk.language != language:
                raise ValueError(
                    f"All chunks must be same language. "
                    f"Expected {language}, got {chunk.language}"
                )
        
        # Verify language is supported
        if language not in ('python', 'javascript', 'typescript'):
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported: python, javascript, typescript"
            )
        
        # Format based on language
        if language == 'python':
            return self._format_python(chunks)
        elif language in ('javascript', 'typescript'):
            return self._format_javascript(chunks)
        else:
            raise ValueError(f"Unsupported language: {language}")
    
    def _format_python(self, chunks: List[CodeChunk]) -> str:
        """Format Python Code_Chunks.
        
        Args:
            chunks: List of Python CodeChunk objects
        
        Returns:
            Formatted Python source code
        """
        # Sort chunks by start_line to maintain order
        sorted_chunks = sorted(chunks, key=lambda c: c.start_line)
        
        # Filter out nested chunks (methods inside classes)
        # A chunk is nested if its range is completely contained within another chunk
        # BUT only if the parent chunk has valid content (starts with 'class' or 'def')
        top_level_chunks = []
        for i, chunk in enumerate(sorted_chunks):
            is_nested = False
            for j, other in enumerate(sorted_chunks):
                if i != j:
                    # Check if chunk is nested inside other
                    if (other.start_line <= chunk.start_line and 
                        chunk.end_line <= other.end_line and
                        chunk.path == other.path):
                        # Only consider it nested if parent has valid content
                        parent_content = other.content.lstrip()
                        if parent_content.startswith(('class ', 'def ', 'async def ')):
                            is_nested = True
                            break
            
            if not is_nested:
                top_level_chunks.append(chunk)
        
        # Join chunks with double newline for readability
        formatted_parts = []
        for chunk in top_level_chunks:
            # Use the chunk content directly - it's already valid Python
            formatted_parts.append(chunk.content)
        
        # Join with double newline between top-level definitions
        return '\n\n'.join(formatted_parts)
    
    def _format_javascript(self, chunks: List[CodeChunk]) -> str:
        """Format JavaScript/TypeScript Code_Chunks.
        
        Args:
            chunks: List of JavaScript/TypeScript CodeChunk objects
        
        Returns:
            Formatted JavaScript/TypeScript source code
        """
        # Sort chunks by start_line to maintain order
        sorted_chunks = sorted(chunks, key=lambda c: c.start_line)
        
        # Filter out nested chunks (methods inside classes)
        # A chunk is nested if its range is completely contained within another chunk
        # BUT only if the parent chunk has valid content (starts with 'class' or 'function')
        top_level_chunks = []
        for i, chunk in enumerate(sorted_chunks):
            is_nested = False
            for j, other in enumerate(sorted_chunks):
                if i != j:
                    # Check if chunk is nested inside other
                    if (other.start_line <= chunk.start_line and 
                        chunk.end_line <= other.end_line and
                        chunk.path == other.path):
                        # Only consider it nested if parent has valid content
                        parent_content = other.content.lstrip()
                        if parent_content.startswith(('class ', 'function ', 'async function ', 'const ', 'let ', 'var ')):
                            is_nested = True
                            break
            
            if not is_nested:
                top_level_chunks.append(chunk)
        
        # Join chunks with double newline for readability
        formatted_parts = []
        for chunk in top_level_chunks:
            # Use the chunk content directly - it's already valid JS/TS
            formatted_parts.append(chunk.content)
        
        # Join with double newline between top-level definitions
        return '\n\n'.join(formatted_parts)
    
    def format_file(self, chunks: List[CodeChunk], file_path: str) -> str:
        """Format Code_Chunks for a specific file.
        
        Filters chunks by file path and formats them back to source code.
        
        Args:
            chunks: List of CodeChunk objects
            file_path: Path to filter chunks by
        
        Returns:
            Formatted source code for the specified file
        
        Raises:
            ValueError: If no chunks found for the specified file
        
        Example:
            >>> printer = PrettyPrinter()
            >>> all_chunks = [...]  # List of chunks from multiple files
            >>> code = printer.format_file(all_chunks, "src/main.py")
        """
        # Filter chunks for this file
        file_chunks = [c for c in chunks if c.path == file_path]
        
        if not file_chunks:
            raise ValueError(f"No chunks found for file: {file_path}")
        
        return self.format(file_chunks)
