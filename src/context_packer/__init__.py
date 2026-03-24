"""
Context Packer - Intelligently package codebases into optimized context for LLMs.

This package provides tools to analyze codebases using semantic search and structural
analysis (PageRank) to select the most relevant files within a token budget.
"""

from context_packer.budget import BudgetManager
from context_packer.chunker import ASTChunker, parse_with_fallback
from context_packer.config import Config
from context_packer.logger import ContextPackerLogger, get_logger
from context_packer.models import CodeChunk
from context_packer.retrieval import RetrievalEngine

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Config",
    "ContextPackerLogger",
    "get_logger",
    "CodeChunk",
    "ASTChunker",
    "RetrievalEngine",
    "BudgetManager",
    "parse_with_fallback",
]
