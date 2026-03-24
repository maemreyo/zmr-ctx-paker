import fnmatch
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from ..models import CodeChunk


class ASTChunker(ABC):
    @abstractmethod
    def parse(self, repo_path: str, config=None) -> List[CodeChunk]:
        pass


def _should_include_file(
    file_path: Path,
    repo_root: Path,
    include_patterns: List[str],
    exclude_patterns: List[str]
) -> bool:
    relative_path = str(file_path.relative_to(repo_root))
    path_parts = relative_path.split('/')

    for pattern in exclude_patterns:
        if _match_pattern(relative_path, path_parts, pattern):
            return False

    for pattern in include_patterns:
        if _match_pattern(relative_path, path_parts, pattern):
            return True

    return False


def _match_pattern(relative_path: str, path_parts: List[str], pattern: str) -> bool:
    if fnmatch.fnmatch(relative_path, pattern):
        return True
    if fnmatch.fnmatch(relative_path, pattern.replace('**/', '*/')):
        return True
    if fnmatch.fnmatch(relative_path, pattern.replace('**', '*')):
        return True
    if pattern.startswith('**/'):
        simple_pattern = pattern[3:]
        for part in path_parts:
            if fnmatch.fnmatch(part, simple_pattern):
                return True
        if fnmatch.fnmatch(relative_path.split('/')[-1], simple_pattern):
            return True
    return False
