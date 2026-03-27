import os
import re
from pathlib import Path
from typing import Any

from ..config import Config
from ..logger import get_logger
from ..models import CodeChunk
from .base import ASTChunker
from .enrichment import enrich_chunk
from .markdown import MarkdownChunker
from .resolvers import ALL_RESOLVERS

logger = get_logger()

# Languages where astchunk is used for AST-boundary splitting.
# astchunk (CMU, MIT License) supports: Python, Java, C#, TypeScript, JavaScript
# We use it for Python and TypeScript primarily. JavaScript works via TypeScript grammar.
# Other languages (Rust, Go, Ruby, etc.) fall back to tree-sitter resolver path.
_ASTCHUNK_LANGUAGES = {"python", "typescript"}

# Maximum characters per astchunk fragment.  Kept as a named constant so it
# can be tuned without hunting for magic numbers in the code.
_ASTCHUNK_MAX_CHUNK_SIZE = 1500

# Matches top-level (column-0) definition statements for Python and
# TypeScript/JavaScript.  Indented methods and nested definitions are
# intentionally excluded — only column-0 identifiers are captured.
#
# Python:     def / async def / class
# TypeScript: function / async function / class / abstract class /
#             const / let / var / type / enum / interface
#             — all optionally prefixed with `export` or `export default`
_TOP_LEVEL_SYMBOL_RE = re.compile(
    r"^(?:export\s+(?:default\s+)?)?(?:async\s+)?"
    r"(?:abstract\s+class|def|class|function|const|let|var|type|enum|interface)\s+"
    r"(\w+)",
    re.MULTILINE,
)

# Matches indented Python method/class definitions (``def`` / ``async def`` / ``class``).
_INDENT_PYDEF_RE = re.compile(
    r"^[ \t]+(?:async\s+)?(?:def|class)\s+([a-zA-Z_]\w*)",
    re.MULTILINE,
)

# Matches indented TypeScript/JavaScript method definitions inside class bodies.
# Requires the statement body to start with ``{`` (distinguishes definitions from
# plain calls).  Control-flow keywords are excluded via a negative lookahead.
_INDENT_TS_METHOD_RE = re.compile(
    r"^[ \t]+"
    r"(?:(?:public|private|protected|static|abstract|async|override|readonly)\s+)*"
    r"(?!(?:if|for|while|switch|try|catch|else|do|with|return|throw|new"
    r"|typeof|instanceof|await|yield|import|export|const|let|var"
    r"|class|function|interface|type|enum|get|set)\b)"
    r"([a-zA-Z_]\w*)\s*\([^{]*\{",
    re.MULTILINE,
)


def _extract_top_level_symbol(content: str) -> list[str]:
    """Return all symbol names defined in *content*.

    Captures three categories:

    1. **Column-0 top-level definitions** — Python ``def``/``async def``/``class``
       and TypeScript/JavaScript ``function``/``const``/``let``/``var``/``class``/
       ``type``/``enum``/``interface``, optionally prefixed with ``export``.
    2. **Indented Python methods** — ``def``/``async def`` inside a class body.
    3. **Indented TypeScript/JavaScript methods** — ``identifier(`` patterns
       inside a class body whose statement opens with ``{``.

    Returns a deduplicated list preserving first-occurrence order.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(name: str) -> None:
        if name not in seen:
            seen.add(name)
            result.append(name)

    for m in _TOP_LEVEL_SYMBOL_RE.finditer(content):
        _add(m.group(1))
    for m in _INDENT_PYDEF_RE.finditer(content):
        _add(m.group(1))
    for m in _INDENT_TS_METHOD_RE.finditer(content):
        _add(m.group(1))

    return result


class TreeSitterChunker(ASTChunker):
    """AST parser using py-tree-sitter with language-specific resolvers."""

    IMPORT_TYPES = {
        "python": {"import_statement", "import_from_statement"},
        "javascript": {"import_statement"},
        "typescript": {"import_statement"},
        "rust": {"use_declaration"},
    }

    def __init__(self) -> None:
        try:
            import tree_sitter_javascript
            import tree_sitter_python
            import tree_sitter_rust
            import tree_sitter_typescript
            from tree_sitter import Language, Parser
        except ImportError as e:
            raise ImportError(
                f"tree-sitter dependencies not available: {e}\n"
                "Install with: pip install py-tree-sitter tree-sitter-python "
                "tree-sitter-javascript tree-sitter-typescript tree-sitter-rust"
            ) from e

        self.Parser = Parser
        self.languages = {
            "python": Language(tree_sitter_python.language()),
            "javascript": Language(tree_sitter_javascript.language()),
            "typescript": Language(tree_sitter_typescript.language_typescript()),
            "rust": Language(tree_sitter_rust.language()),
        }
        self.ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
        }
        self._resolvers = {lang: resolver() for lang, resolver in ALL_RESOLVERS.items()}
        self._md_chunker = MarkdownChunker()

    def parse(self, repo_path: str, config: Any = None) -> list[CodeChunk]:
        if not os.path.exists(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        if not os.path.isdir(repo_path):
            raise ValueError(f"Repository path is not a directory: {repo_path}")

        chunks = []
        repo_path_obj = Path(repo_path)

        if config is None:
            config = Config()

        include_patterns = config.include_patterns
        exclude_patterns = config.exclude_patterns

        chunks.extend(self._md_chunker.parse(repo_path, config=config))

        from .base import _should_include_file

        for ext in self.ext_to_lang.keys():
            for file_path in repo_path_obj.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                if not _should_include_file(
                    file_path, repo_path_obj, include_patterns, exclude_patterns
                ):
                    continue
                try:
                    chunks.extend(self._parse_file(file_path, repo_path_obj))
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

        return chunks

    def _parse_file(self, file_path: Path, repo_root: Path) -> list[CodeChunk]:
        ext = file_path.suffix
        language = self.ext_to_lang.get(ext)
        if not language:
            return []
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        parser = self.Parser(self.languages[language])
        tree = parser.parse(bytes(content, "utf8"))
        relative_path = str(file_path.relative_to(repo_root))

        file_imports = self._extract_file_imports(tree.root_node, language)

        # Use astchunk for Python and TypeScript when available; fall back to
        # the tree-sitter resolver for other languages or if astchunk is absent.
        if language in _ASTCHUNK_LANGUAGES:
            ast_chunks = self._try_astchunk(content, relative_path, language)
            if ast_chunks is not None:
                for chunk in ast_chunks:
                    for imp in file_imports:
                        if imp not in chunk.symbols_referenced:
                            chunk.symbols_referenced.append(imp)
                return ast_chunks

        chunks = self._extract_definitions(tree.root_node, content, relative_path, language)

        for chunk in chunks:
            for imp in file_imports:
                if imp not in chunk.symbols_referenced:
                    chunk.symbols_referenced.append(imp)

        return chunks

    def _try_astchunk(
        self, content: str, relative_path: str, language: str
    ) -> list[CodeChunk] | None:
        """Attempt to split *content* using astchunk.

        Returns a list of enriched CodeChunks on success, or ``None`` if
        astchunk is unavailable / errors so the caller can fall back.
        """
        try:
            import astchunk  # type: ignore[import-untyped]
        except ImportError:
            return None

        try:
            builder = astchunk.ASTChunkBuilder(
                language=language,
                max_chunk_size=_ASTCHUNK_MAX_CHUNK_SIZE,
                metadata_template="default",
            )
            raw_chunks = builder.chunkify(content, filepath=relative_path)
        except Exception as e:
            logger.debug(f"astchunk failed for {relative_path!r}: {e} — falling back")
            return None

        chunks: list[CodeChunk] = []
        for item in raw_chunks:
            meta = item.get("metadata", {})
            # astchunk uses 0-based line numbers; convert to 1-based.
            start_line = int(meta.get("start_line_no", 0)) + 1
            end_line = int(meta.get("end_line_no", 0)) + 1
            chunk = CodeChunk(
                path=relative_path,
                start_line=start_line,
                end_line=end_line,
                content=item["content"],
                symbols_defined=_extract_top_level_symbol(item["content"]),
                symbols_referenced=[],
                language=language,
            )
            chunks.append(enrich_chunk(chunk))

        return chunks

    def _extract_file_imports(self, root_node: Any, language: str) -> list[str]:
        imports: set[str] = set()
        import_types = self.IMPORT_TYPES.get(language, set())
        self._collect_imports(root_node, import_types, imports)
        return list(imports)

    def _collect_imports(self, node: Any, import_types: set[str], imports: set[str]) -> None:
        if node.type in import_types:
            self._extract_import_names_from_node(node, imports)
        for child in node.children:
            self._collect_imports(child, import_types, imports)

    def _extract_import_names_from_node(self, node: Any, imports: set[str]) -> None:
        for child in node.children:
            text = child.text.decode("utf8") if hasattr(child, "text") else ""
            if child.type == "identifier":
                imports.add(text)
            elif child.type == "string":
                cleaned = text.strip("'\"")
                imports.add(cleaned)
            elif child.type in ("dotted_name", "qualified_imports", "scoped_identifier"):
                self._extract_import_names_from_node(child, imports)
            elif child.type == "scoped_use_list":
                for use_child in child.children:
                    if use_child.type == "identifier":
                        imports.add(use_child.text.decode("utf8"))
                    elif use_child.type == "scoped_identifier":
                        self._extract_import_names_from_node(use_child, imports)

    def _extract_definitions(
        self, node: Any, content: str, file_path: str, language: str
    ) -> list[CodeChunk]:
        chunks = []
        resolver = self._resolvers.get(language)

        if resolver and resolver.should_extract(node.type):
            chunk = resolver.node_to_chunk(node, content, file_path)
            if chunk:
                chunks.append(chunk)

        for child in node.children:
            chunks.extend(self._extract_definitions(child, content, file_path, language))

        return chunks
