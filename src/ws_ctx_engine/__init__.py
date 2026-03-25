"""
ws-ctx-engine - Intelligently package codebases into optimized context for LLMs.

This package provides tools to analyze codebases using semantic search and structural
analysis (PageRank) to select the most relevant files within a token budget.
"""

from ws_ctx_engine.budget import BudgetManager
from ws_ctx_engine.chunker import ASTChunker, parse_with_fallback
from ws_ctx_engine.config import Config
from ws_ctx_engine.logger import WsCtxEngineLogger, get_logger
from ws_ctx_engine.models import CodeChunk
from ws_ctx_engine.retrieval import RetrievalEngine

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Config",
    "WsCtxEngineLogger",
    "get_logger",
    "CodeChunk",
    "ASTChunker",
    "RetrievalEngine",
    "BudgetManager",
    "parse_with_fallback",
]
