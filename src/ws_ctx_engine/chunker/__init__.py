from .base import ASTChunker, _should_include_file, _match_pattern
from .markdown import MarkdownChunker
from .tree_sitter import TreeSitterChunker
from .regex import RegexChunker
from .resolvers import (
    LanguageResolver,
    PythonResolver,
    JavaScriptResolver,
    TypeScriptResolver,
    RustResolver,
    ALL_RESOLVERS,
)

def parse_with_fallback(repo_path: str, config=None):
    """Parse repository with automatic fallback from TreeSitter to Regex."""
    try:
        chunker = TreeSitterChunker()
        from ..logger import get_logger
        logger = get_logger()
        logger.info("Using TreeSitterChunker for AST parsing")
        return chunker.parse(repo_path, config=config)
    except ImportError as e:
        from ..logger import get_logger
        logger = get_logger()
        logger.warning(f"TreeSitter not available ({e}), falling back to RegexChunker")
        return RegexChunker().parse(repo_path, config=config)
    except Exception as e:
        from ..logger import get_logger
        logger = get_logger()
        logger.warning(f"TreeSitterChunker failed ({e}), falling back to RegexChunker")
        return RegexChunker().parse(repo_path, config=config)


__all__ = [
    "ASTChunker",
    "MarkdownChunker",
    "TreeSitterChunker",
    "RegexChunker",
    "parse_with_fallback",
    "LanguageResolver",
    "PythonResolver",
    "JavaScriptResolver",
    "TypeScriptResolver",
    "RustResolver",
    "ALL_RESOLVERS",
    "_should_include_file",
    "_match_pattern",
]
