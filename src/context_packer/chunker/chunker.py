"""AST-based code chunking with fallback strategies."""

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Set
import fnmatch

from ..logger import get_logger
from ..models import CodeChunk

logger = get_logger()


def _should_include_file(file_path: Path, repo_root: Path, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
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


class ASTChunker(ABC):
    @abstractmethod
    def parse(self, repo_path: str, config=None) -> List[CodeChunk]:
        pass


# =============================================================================
# FIX 1 – MarkdownChunker
# =============================================================================

class MarkdownChunker:
    """Splits Markdown files into chunks based on heading boundaries (# / ##).

    Each ATX heading starts a new chunk.  A file with no headings is returned
    as a single chunk so nothing is silently dropped.
    """

    EXTENSIONS: Set[str] = {'.md', '.markdown', '.mdx'}
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)

    def parse_file(self, file_path: Path, repo_root: Path) -> List[CodeChunk]:
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        relative_path = str(file_path.relative_to(repo_root))
        lines = content.splitlines()

        heading_starts = []
        for match in self._HEADING_RE.finditer(content):
            line_no = content[: match.start()].count('\n')
            heading_text = match.group(2).strip()
            heading_starts.append((line_no, heading_text))

        if not heading_starts:
            return [CodeChunk(
                path=relative_path,
                start_line=1,
                end_line=len(lines),
                content=content,
                symbols_defined=[file_path.stem],
                symbols_referenced=[],
                language='markdown',
            )]

        chunks: List[CodeChunk] = []
        for idx, (start_0, heading_text) in enumerate(heading_starts):
            end_0 = heading_starts[idx + 1][0] - 1 if idx + 1 < len(heading_starts) else len(lines) - 1
            if start_0 > end_0:
                continue
            chunk_lines = lines[start_0: end_0 + 1]
            chunks.append(CodeChunk(
                path=relative_path,
                start_line=start_0 + 1,
                end_line=end_0 + 1,
                content='\n'.join(chunk_lines),
                symbols_defined=[heading_text],
                symbols_referenced=[],
                language='markdown',
            ))

        return chunks

    def parse(self, repo_path: str, config=None) -> List[CodeChunk]:
        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            raise ValueError(f"Repository path does not exist or is not a directory: {repo_path}")
        from ..config import Config
        if config is None:
            config = Config()
        repo_path_obj = Path(repo_path)
        chunks: List[CodeChunk] = []
        for ext in self.EXTENSIONS:
            for file_path in repo_path_obj.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                if not _should_include_file(file_path, repo_path_obj,
                                            config.include_patterns,
                                            config.exclude_patterns):
                    continue
                try:
                    chunks.extend(self.parse_file(file_path, repo_path_obj))
                except Exception as e:
                    logger.warning(f"MarkdownChunker failed on {file_path}: {e}")
        return chunks


# =============================================================================
# TreeSitterChunker
# =============================================================================

class TreeSitterChunker(ASTChunker):
    """Primary AST parser using py-tree-sitter.

    FIX 1: delegates .md/.markdown/.mdx files to MarkdownChunker.
    FIX 2: expanded AST target types (TS interfaces/types, Python constants,
            Rust const/type/static/mod items).
    """

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

        # FIX 1 – parse Markdown files
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
        if not language:
            return []
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []
        parser = self.Parser(self.languages[language])
        tree = parser.parse(bytes(content, 'utf8'))
        return self._extract_definitions(tree.root_node, content,
                                         str(file_path.relative_to(repo_root)),
                                         language)

    def _extract_definitions(self, node, content: str, file_path: str, language: str) -> List[CodeChunk]:
        chunks = []

        # FIX 2 – expanded target types
        if language == 'python':
            target_types = {'function_definition', 'class_definition', 'expression_statement'}
        elif language in ('javascript', 'typescript'):
            target_types = {
                'function_declaration', 'class_declaration', 'method_definition',
                'interface_declaration',    # TS: interface Foo { … }
                'type_alias_declaration',   # TS: type Bar = …
                'enum_declaration',         # TS: enum Direction { … }
                'abstract_class_declaration',
            }
        elif language == 'rust':
            target_types = {
                'function_item', 'struct_item', 'trait_item', 'impl_item', 'enum_item',
                'const_item', 'type_item', 'static_item', 'mod_item',   # FIX 2
            }
        else:
            target_types = set()

        if node.type in target_types:
            if language == 'python' and node.type == 'expression_statement':
                chunk = self._extract_python_constant(node, content, file_path)
            else:
                chunk = self._node_to_chunk(node, content, file_path, language)
            if chunk:
                chunks.append(chunk)

        if language in ('javascript', 'typescript') and node.type == 'lexical_declaration':
            chunk = self._extract_arrow_function(node, content, file_path, language)
            if chunk:
                chunks.append(chunk)

        for child in node.children:
            chunks.extend(self._extract_definitions(child, content, file_path, language))
        return chunks

    def _extract_python_constant(self, node, content: str, file_path: str) -> Optional[CodeChunk]:
        """Capture module-level Python ALL_CAPS constants."""
        if node.parent is None or node.parent.type != 'module':
            return None
        raw = content.encode('utf8')[node.start_byte:node.end_byte].decode('utf8')
        match = re.match(r'^([A-Z][A-Z0-9_]+)\s*=', raw.strip())
        if not match:
            return None
        return CodeChunk(
            path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            content=raw,
            symbols_defined=[match.group(1)],
            symbols_referenced=[],
            language='python',
        )

    def _node_to_chunk(self, node, content: str, file_path: str, language: str) -> Optional[CodeChunk]:
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        content_bytes = content.encode('utf8')
        node_content = content_bytes[node.start_byte:node.end_byte].decode('utf8')
        symbol_name = self._extract_symbol_name(node, language)
        return CodeChunk(
            path=file_path,
            start_line=start_line,
            end_line=end_line,
            content=node_content,
            symbols_defined=[symbol_name] if symbol_name else [],
            symbols_referenced=self._extract_references(node),
            language=language
        )

    def _extract_symbol_name(self, node, language: str) -> Optional[str]:
        for child in node.children:
            if child.type in ('identifier', 'property_identifier'):
                return child.text.decode('utf8')
        return None

    def _extract_arrow_function(self, node, content: str, file_path: str, language: str) -> Optional[CodeChunk]:
        for child in node.children:
            if child.type == 'variable_declarator':
                identifier = None
                has_arrow = False
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        identifier = subchild.text.decode('utf8')
                    elif subchild.type == 'arrow_function':
                        has_arrow = True
                if identifier and has_arrow:
                    content_bytes = content.encode('utf8')
                    node_content = content_bytes[node.start_byte:node.end_byte].decode('utf8')
                    return CodeChunk(
                        path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        content=node_content,
                        symbols_defined=[identifier],
                        symbols_referenced=[],
                        language=language
                    )
        return None

    def _extract_references(self, node) -> List[str]:
        references: Set[str] = set()
        self._collect_references(node, references)
        return list(references)

    def _collect_references(self, node, references: Set[str]) -> None:
        if node.type in ('import_statement', 'import_from_statement', 'call_expression'):
            for child in node.children:
                if child.type == 'identifier':
                    references.add(child.text.decode('utf8'))
        for child in node.children:
            self._collect_references(child, references)


# =============================================================================
# RegexChunker
# =============================================================================

class RegexChunker(ASTChunker):
    """Fallback parser using regex patterns.

    FIX 1: Delegates .md files to MarkdownChunker.
    FIX 3: _find_block_end uses bracket-matching (no 20-line cap).
    FIX 4: symbols_referenced populated with imports from the whole file.
    """

    # FIX 4: import patterns per language
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

    def __init__(self):
        self.patterns = {
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
        self.ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.rs': 'rust',
        }
        self._md_chunker = MarkdownChunker()  # FIX 1

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

        # FIX 1 – parse Markdown files
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
        if not language or language not in self.patterns:
            return []
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        chunks = []
        relative_path = str(file_path.relative_to(repo_root))
        lines = content.split('\n')

        # FIX 4: extract file-wide imports once
        file_imports = self._extract_imports(content, language)

        for pattern_name, pattern in self.patterns[language].items():
            for match in pattern.finditer(content):
                symbol_name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1

                # FIX 3: accurate block-end detection
                end_line = self._find_block_end(content, match.start(), lines, language)

                chunk_content = '\n'.join(lines[start_line - 1:end_line])

                chunks.append(CodeChunk(
                    path=relative_path,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_content,
                    symbols_defined=[symbol_name],
                    symbols_referenced=file_imports,   # FIX 4
                    language=language
                ))

        return chunks

    # -------------------------------------------------------------------------
    # FIX 3: block-end helpers
    # -------------------------------------------------------------------------

    def _find_block_end(self, content: str, definition_start: int,
                        lines: List[str], language: str) -> int:
        start_line_0 = content[:definition_start].count('\n')
        if language == 'python':
            return self._python_indent_end(lines, start_line_0)
        return self._brace_matching_end(content, definition_start, lines, start_line_0)

    def _brace_matching_end(self, content: str, definition_start: int,
                             lines: List[str], start_line_0: int) -> int:
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
        return last_body_line + 1  # 1-indexed

    # -------------------------------------------------------------------------
    # FIX 4: import extraction
    # -------------------------------------------------------------------------

    def _extract_imports(self, content: str, language: str) -> List[str]:
        patterns = self._IMPORT_PATTERNS.get(language, [])
        imports: Set[str] = set()
        for pat in patterns:
            for match in pat.finditer(content):
                name = match.group(1).strip()
                imports.add(name.split('.')[0])
        return list(imports)

    # -------------------------------------------------------------------------
    # Kept for backward-compatibility – no longer used internally
    # -------------------------------------------------------------------------

    def _estimate_end_line(self, content: str, start_pos: int, lines: List[str]) -> int:
        """Deprecated: use _find_block_end instead."""
        start_line = content[:start_pos].count('\n')
        for i in range(start_line + 1, min(start_line + 100, len(lines))):
            if re.match(r'^(def|class|function|const\s+\w+\s*=)', lines[i].strip()):
                return i
        return min(start_line + 20, len(lines))


# =============================================================================
# Public entry point
# =============================================================================

def parse_with_fallback(repo_path: str, config=None) -> List[CodeChunk]:
    """Parse repository with automatic fallback from TreeSitter to Regex.

    Both chunkers now support:
      - Markdown files (FIX 1)
      - Wider AST target types: TS interfaces/types, Python constants,
        Rust const/type/static/mod items (FIX 2)
      - Accurate block-end detection – no 20-line cap (FIX 3)
      - Import-based symbols_referenced during regex fallback (FIX 4)

    Args:
        repo_path: Path to the repository root directory
        config: Configuration instance with include/exclude patterns

    Returns:
        List of CodeChunk objects representing parsed code segments

    Requirements: 1.5, 1.6, 10.1, 10.2
    """
    try:
        chunker = TreeSitterChunker()
        logger.info("Using TreeSitterChunker for AST parsing")
        return chunker.parse(repo_path, config=config)
    except ImportError as e:
        logger.warning(f"TreeSitter not available ({e}), falling back to RegexChunker")
        return RegexChunker().parse(repo_path, config=config)
    except Exception as e:
        logger.warning(f"TreeSitterChunker failed ({e}), falling back to RegexChunker")
        return RegexChunker().parse(repo_path, config=config)