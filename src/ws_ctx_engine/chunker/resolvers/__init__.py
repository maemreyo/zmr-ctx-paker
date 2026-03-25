from .base import LanguageResolver
from .python import PythonResolver
from .javascript import JavaScriptResolver
from .typescript import TypeScriptResolver
from .rust import RustResolver

ALL_RESOLVERS = {
    'python': PythonResolver,
    'javascript': JavaScriptResolver,
    'typescript': TypeScriptResolver,
    'rust': RustResolver,
}

__all__ = [
    "LanguageResolver",
    "PythonResolver",
    "JavaScriptResolver",
    "TypeScriptResolver",
    "RustResolver",
    "ALL_RESOLVERS",
]
