import os
from pathlib import Path
from typing import Any

from ..config import Config
from ..logger import get_logger
from ..models import CodeChunk
from .base import ASTChunker
from .markdown import MarkdownChunker
from .resolvers import ALL_RESOLVERS

logger = get_logger()


class TreeSitterChunker(ASTChunker):
    """AST parser using py-tree-sitter with language-specific resolvers."""

    IMPORT_TYPES = {
        "python": {"import_statement", "import_from_statement"},
        "javascript": {"import_statement"},
        "typescript": {"import_statement"},
        "rust": {"use_declaration"},
    }

    def __init__(self) -> None:
        try:
            import tree_sitter_javascript
            import tree_sitter_python
            import tree_sitter_rust
            import tree_sitter_typescript
            from tree_sitter import Language, Parser
        except ImportError as e:
            raise ImportError(
                f"tree-sitter dependencies not available: {e}\n"
                "Install with: pip install py-tree-sitter tree-sitter-python "
                "tree-sitter-javascript tree-sitter-typescript tree-sitter-rust"
            ) from e

        self.Parser = Parser
        self.languages = {
            "python": Language(tree_sitter_python.language()),
            "javascript": Language(tree_sitter_javascript.language()),
            "typescript": Language(tree_sitter_typescript.language_typescript()),
            "rust": Language(tree_sitter_rust.language()),
        }
        self.ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
        }
        self._resolvers = {lang: resolver() for lang, resolver in ALL_RESOLVERS.items()}
        self._md_chunker = MarkdownChunker()

    def parse(self, repo_path: str, config: Any = None) -> list[CodeChunk]:
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        if not os.path.isdir(repo_path):
            raise ValueError(f"Repository path is not a directory: {repo_path}")

        chunks = []
        repo_path_obj = Path(repo_path)

        if config is None:
            config = Config()

        include_patterns = config.include_patterns
        exclude_patterns = config.exclude_patterns

        chunks.extend(self._md_chunker.parse(repo_path, config=config))

        from .base import _should_include_file

        for ext in self.ext_to_lang.keys():
            for file_path in repo_path_obj.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                if not _should_include_file(
                    file_path, repo_path_obj, include_patterns, exclude_patterns
                ):
                    continue
                try:
                    chunks.extend(self._parse_file(file_path, repo_path_obj))
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

        return chunks

    def _parse_file(self, file_path: Path, repo_root: Path) -> list[CodeChunk]:
        ext = file_path.suffix
        language = self.ext_to_lang.get(ext)
        if not language:
            return []
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        parser = self.Parser(self.languages[language])
        tree = parser.parse(bytes(content, "utf8"))
        relative_path = str(file_path.relative_to(repo_root))

        chunks = self._extract_definitions(tree.root_node, content, relative_path, language)

        file_imports = self._extract_file_imports(tree.root_node, language)
        for chunk in chunks:
            for imp in file_imports:
                if imp not in chunk.symbols_referenced:
                    chunk.symbols_referenced.append(imp)

        return chunks

    def _extract_file_imports(self, root_node: Any, language: str) -> list[str]:
        imports: set[str] = set()
        import_types = self.IMPORT_TYPES.get(language, set())
        self._collect_imports(root_node, import_types, imports)
        return list(imports)

    def _collect_imports(self, node: Any, import_types: set[str], imports: set[str]) -> None:
        if node.type in import_types:
            self._extract_import_names_from_node(node, imports)
        for child in node.children:
            self._collect_imports(child, import_types, imports)

    def _extract_import_names_from_node(self, node: Any, imports: set[str]) -> None:
        for child in node.children:
            text = child.text.decode("utf8") if hasattr(child, "text") else ""
            if child.type == "identifier":
                imports.add(text)
            elif child.type == "string":
                cleaned = text.strip("'\"")
                imports.add(cleaned)
            elif child.type in ("dotted_name", "qualified_imports", "scoped_identifier"):
                self._extract_import_names_from_node(child, imports)
            elif child.type == "scoped_use_list":
                for use_child in child.children:
                    if use_child.type == "identifier":
                        imports.add(use_child.text.decode("utf8"))
                    elif use_child.type == "scoped_identifier":
                        self._extract_import_names_from_node(use_child, imports)

    def _extract_definitions(
        self, node: Any, content: str, file_path: str, language: str
    ) -> list[CodeChunk]:
        chunks = []
        resolver = self._resolvers.get(language)

        if resolver and resolver.should_extract(node.type):
            chunk = resolver.node_to_chunk(node, content, file_path)
            if chunk:
                chunks.append(chunk)

        for child in node.children:
            chunks.extend(self._extract_definitions(child, content, file_path, language))

        return chunks
