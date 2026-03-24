import os
from pathlib import Path
from typing import List

from .base import ASTChunker
from .markdown import MarkdownChunker
from .resolvers import ALL_RESOLVERS
from ..logger import get_logger
from ..config import Config
from ..models import CodeChunk

logger = get_logger()


class TreeSitterChunker(ASTChunker):
    """AST parser using py-tree-sitter with language-specific resolvers."""

    def __init__(self):
        try:
            from tree_sitter import Language, Parser
            import tree_sitter_python
            import tree_sitter_javascript
            import tree_sitter_typescript
            import tree_sitter_rust
        except ImportError as e:
            raise ImportError(
                f"tree-sitter dependencies not available: {e}\n"
                "Install with: pip install py-tree-sitter tree-sitter-python "
                "tree-sitter-javascript tree-sitter-typescript tree-sitter-rust"
            )

        self.Parser = Parser
        self.languages = {
            'python': Language(tree_sitter_python.language()),
            'javascript': Language(tree_sitter_javascript.language()),
            'typescript': Language(tree_sitter_typescript.language_typescript()),
            'rust': Language(tree_sitter_rust.language()),
        }
        self.ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.rs': 'rust',
        }
        self._resolvers = {lang: resolver() for lang, resolver in ALL_RESOLVERS.items()}
        self._md_chunker = MarkdownChunker()

    def parse(self, repo_path: str, config=None) -> List[CodeChunk]:
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        if not os.path.isdir(repo_path):
            raise ValueError(f"Repository path is not a directory: {repo_path}")

        chunks = []
        repo_path_obj = Path(repo_path)

        from ..config import Config
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
                if not _should_include_file(file_path, repo_path_obj, include_patterns, exclude_patterns):
                    continue
                try:
                    chunks.extend(self._parse_file(file_path, repo_path_obj))
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

        return chunks

    def _parse_file(self, file_path: Path, repo_root: Path) -> List[CodeChunk]:
        ext = file_path.suffix
        language = self.ext_to_lang.get(ext)
        if not language:
            return []
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        parser = self.Parser(self.languages[language])
        tree = parser.parse(bytes(content, 'utf8'))
        return self._extract_definitions(
            tree.root_node,
            content,
            str(file_path.relative_to(repo_root)),
            language
        )

    def _extract_definitions(self, node, content: str, file_path: str, language: str) -> List[CodeChunk]:
        chunks = []
        resolver = self._resolvers.get(language)

        if resolver and resolver.should_extract(node.type):
            chunk = resolver.node_to_chunk(node, content, file_path)
            if chunk:
                chunks.append(chunk)

        for child in node.children:
            chunks.extend(self._extract_definitions(child, content, file_path, language))

        return chunks
