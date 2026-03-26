from abc import ABC, abstractmethod
from typing import Any

from ...models import CodeChunk


class LanguageResolver(ABC):
    """Abstract base for language-specific code resolution.

    Each resolver封装了特定编程语言的:
    - Target AST node types
    - Symbol name extraction
    - References extraction
    - Block boundary detection
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language identifier (e.g., 'python', 'javascript')."""
        pass

    @property
    @abstractmethod
    def target_types(self) -> set[str]:
        """Return set of AST node types to extract."""
        pass

    @property
    def file_extensions(self) -> list[str]:
        """Return list of file extensions for this language."""
        return []

    @abstractmethod
    def extract_symbol_name(self, node: Any) -> str | None:
        """Extract symbol name from AST node."""
        pass

    @abstractmethod
    def extract_references(self, node: Any) -> list[str]:
        """Extract referenced symbols from AST node."""
        pass

    def should_extract(self, node_type: str) -> bool:
        """Check if this node type should be extracted."""
        return node_type in self.target_types

    def node_to_chunk(
        self,
        node: Any,
        content: str,
        file_path: str,
    ) -> CodeChunk | None:
        """Convert AST node to CodeChunk."""
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        content_bytes = content.encode("utf8")
        node_content = content_bytes[node.start_byte : node.end_byte].decode("utf8")
        symbol_name = self.extract_symbol_name(node)

        return CodeChunk(
            path=file_path,
            start_line=start_line,
            end_line=end_line,
            content=node_content,
            symbols_defined=[symbol_name] if symbol_name else [],
            symbols_referenced=self.extract_references(node),
            language=self.language,
        )
