from .errors import (
    BudgetError,
    ConfigurationError,
    DependencyError,
    IndexError,
    ParsingError,
    WsCtxEngineError,
)

# Aliases for backwards compatibility and test imports
IndexNotFoundError = IndexError
RetrievalError = WsCtxEngineError

__all__ = [
    "WsCtxEngineError",
    "DependencyError",
    "ConfigurationError",
    "ParsingError",
    "IndexError",
    "IndexNotFoundError",
    "BudgetError",
    "RetrievalError",
]
