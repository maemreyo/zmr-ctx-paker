from .errors import (
    WsCtxEngineError,
    DependencyError,
    ConfigurationError,
    ParsingError,
    IndexError,
    BudgetError,
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
