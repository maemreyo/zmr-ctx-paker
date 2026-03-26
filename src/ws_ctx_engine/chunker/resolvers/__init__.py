from typing import Union

from .base import LanguageResolver
from .javascript import JavaScriptResolver
from .python import PythonResolver
from .rust import RustResolver
from .typescript import TypeScriptResolver

ALL_RESOLVERS: dict[
    str, type[PythonResolver | JavaScriptResolver | TypeScriptResolver | RustResolver]
] = {
    "python": PythonResolver,
    "javascript": JavaScriptResolver,
    "typescript": TypeScriptResolver,
    "rust": RustResolver,
}

__all__ = [
    "LanguageResolver",
    "PythonResolver",
    "JavaScriptResolver",
    "TypeScriptResolver",
    "RustResolver",
    "ALL_RESOLVERS",
]
