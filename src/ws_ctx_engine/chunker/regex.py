import os
import re
from pathlib import Path
from typing import List, Optional, Set

from .base import ASTChunker, _should_include_file
from .markdown import MarkdownChunker
from ..logger import get_logger
from ..config import Config
from ..models import CodeChunk

logger = get_logger()


class RegexChunker(ASTChunker):
    """Fallback parser using regex patterns with block detection."""

    _IMPORT_PATTERNS = {
        'python': [
            re.compile(r'^import\s+([\w.]+)', re.MULTILINE),
            re.compile(r'^from\s+([\w.]+)\s+import', re.MULTILINE),
        ],
        'javascript': [
            re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
            re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE),
        ],
        'typescript': [
            re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
            re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE),
        ],
        'rust': [
            re.compile(r'^use\s+([\w:]+)', re.MULTILINE),
        ],
    }

    _PATTERNS = {
        'python': {
            'function': re.compile(r'^def\s+(\w+)\s*\(', re.MULTILINE),
            'class': re.compile(r'^class\s+(\w+)\s*[\(:]', re.MULTILINE),
        },
        'javascript': {
            'function': re.compile(r'function\s+(\w+)\s*\(', re.MULTILINE),
            'class': re.compile(r'class\s+(\w+)\s*[{]', re.MULTILINE),
            'arrow': re.compile(r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', re.MULTILINE),
        },
        'typescript': {
            'function': re.compile(r'function\s+(\w+)\s*\(', re.MULTILINE),
            'class': re.compile(r'class\s+(\w+)\s*[{]', re.MULTILINE),
            'arrow': re.compile(r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', re.MULTILINE),
        },
        'rust': {
            'function': re.compile(r'^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*<?[^>]*>?\(', re.MULTILINE),
            'struct': re.compile(r'^\s*(?:pub\s+)?struct\s+(\w+)\s*[{]', re.MULTILINE),
            'trait': re.compile(r'^\s*(?:pub\s+)?trait\s+(\w+)\s*[{]', re.MULTILINE),
            'impl': re.compile(r'^\s*impl(?:<[^>]+>)?\s+(?:[^for]+for\s+)?(\w+)\s*[{]', re.MULTILINE),
            'enum': re.compile(r'^\s*(?:pub\s+)?enum\s+(\w+)\s*[{]', re.MULTILINE),
        },
    }

    def __init__(self):
        self.ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.rs': 'rust',
        }
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
        if not language or language not in self._PATTERNS:
            return []
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        chunks = []
        relative_path = str(file_path.relative_to(repo_root))
        lines = content.split('\n')

        file_imports = self._extract_imports(content, language)

        for pattern_name, pattern in self._PATTERNS[language].items():
            for match in pattern.finditer(content):
                symbol_name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1
                end_line = self._find_block_end(content, match.start(), lines, language)
                chunk_content = '\n'.join(lines[start_line - 1:end_line])

                chunks.append(CodeChunk(
                    path=relative_path,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    symbols_defined=[symbol_name],
                    symbols_referenced=file_imports,
                    language=language
                ))

        return chunks

    def _find_block_end(
        self,
        content: str,
        definition_start: int,
        lines: List[str],
        language: str
    ) -> int:
        start_line_0 = content[:definition_start].count('\n')
        if language == 'python':
            return self._python_indent_end(lines, start_line_0)
        return self._brace_matching_end(content, definition_start, lines, start_line_0)

    def _brace_matching_end(
        self,
        content: str,
        definition_start: int,
        lines: List[str],
        start_line_0: int
    ) -> int:
        brace_pos = content.find('{', definition_start)
        if brace_pos == -1:
            return start_line_0 + 1

        depth = 0
        in_string: Optional[str] = None
        i = brace_pos

        while i < len(content):
            ch = content[i]
            if in_string:
                if ch == '\\':
                    i += 2
                    continue
                if ch == in_string:
                    in_string = None
            else:
                if ch in ('"', "'"):
                    in_string = ch
                elif ch == '/' and i + 1 < len(content):
                    if content[i + 1] == '/':
                        nl = content.find('\n', i)
                        i = nl if nl != -1 else len(content)
                        continue
                    elif content[i + 1] == '*':
                        end = content.find('*/', i + 2)
                        i = end + 2 if end != -1 else len(content)
                        continue
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end_line_0 = content[:i + 1].count('\n')
                        return end_line_0 + 1
            i += 1

        return len(lines)

    def _python_indent_end(self, lines: List[str], start_line_0: int) -> int:
        if start_line_0 >= len(lines):
            return len(lines)
        def_line = lines[start_line_0]
        base_indent = len(def_line) - len(def_line.lstrip())
        last_body_line = start_line_0
        for i in range(start_line_0 + 1, len(lines)):
            stripped = lines[i].strip()
            if not stripped or stripped.startswith('#'):
                continue
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= base_indent:
                break
            last_body_line = i
        return last_body_line + 1

    def _extract_imports(self, content: str, language: str) -> List[str]:
        patterns = self._IMPORT_PATTERNS.get(language, [])
        imports: Set[str] = set()
        for pat in patterns:
            for match in pat.finditer(content):
                name = match.group(1).strip()
                imports.add(name.split('.')[0])
        return list(imports)
