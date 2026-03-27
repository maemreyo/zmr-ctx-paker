from __future__ import annotations

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

# Maps our internal language name → astchunk language name.
# astchunk (CMU, MIT License) supports: Python, Java, C#, TypeScript, JavaScript.
# Languages absent from this map fall back to the tree-sitter resolver path only.
# Java and C# use astchunk exclusively (no tree-sitter grammar bundled).
_ASTCHUNK_LANG_MAP: dict[str, str] = {
    "python": "python",
    "typescript": "typescript",
    "javascript": "javascript",
    "java": "java",
    "csharp": "csharp",
}

# Maximum non-whitespace characters per chunk fragment.
# Applied by astchunk on the astchunk path, and enforced manually on the
# tree-sitter resolver path via _split_large_chunk().
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


def _make_subchunk(
    chunk: "CodeChunk", lines: list[str], start_line: int, is_first: bool
) -> "CodeChunk":
    """Build one sub-chunk from *lines* starting at *start_line*.

    Only the first sub-chunk inherits ``symbols_defined``; subsequent ones get
    an empty list so downstream graph edges point to a single canonical node.
    """
    from dataclasses import replace

    return replace(
        chunk,
        content="".join(lines),
        start_line=start_line,
        end_line=start_line + len(lines) - 1,
        symbols_defined=chunk.symbols_defined if is_first else [],
    )


def _split_large_chunk(chunk: "CodeChunk") -> list["CodeChunk"]:
    """Split *chunk* into sub-chunks when non-whitespace content exceeds the limit.

    Splitting is done at line boundaries.  If the chunk is within the limit it
    is returned unchanged (as a 1-element list).
    """
    non_ws = sum(1 for ch in chunk.content if not ch.isspace())
    if non_ws <= _ASTCHUNK_MAX_CHUNK_SIZE:
        return [chunk]

    sub_chunks: list[CodeChunk] = []
    current_lines: list[str] = []
    current_non_ws = 0
    current_start = chunk.start_line

    for line in chunk.content.splitlines(keepends=True):
        line_non_ws = sum(1 for ch in line if not ch.isspace())
        if current_lines and current_non_ws + line_non_ws > _ASTCHUNK_MAX_CHUNK_SIZE:
            sub_chunks.append(_make_subchunk(chunk, current_lines, current_start, not sub_chunks))
            current_start += len(current_lines)
            current_lines = [line]
            current_non_ws = line_non_ws
        else:
            current_lines.append(line)
            current_non_ws += line_non_ws

    if current_lines:
        sub_chunks.append(_make_subchunk(chunk, current_lines, current_start, not sub_chunks))

    return sub_chunks if sub_chunks else [chunk]


def _inject_imports(chunks: list["CodeChunk"], file_imports: list[str]) -> list["CodeChunk"]:
    """Return *chunks* with *file_imports* merged into each chunk's ``symbols_referenced``.

    No-ops when *file_imports* is empty.  Uses ``dict.fromkeys`` to deduplicate
    while preserving insertion order.
    """
    if not file_imports:
        return chunks
    from dataclasses import replace

    return [
        replace(
            c,
            symbols_referenced=list(dict.fromkeys(c.symbols_referenced + file_imports)),
        )
        for c in chunks
    ]


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
            # Java and C# use astchunk exclusively; no tree-sitter grammar bundled.
            ".java": "java",
            ".cs": "csharp",
        }
        self._resolvers = {lang: resolver() for lang, resolver in ALL_RESOLVERS.items()}
        self._md_chunker = MarkdownChunker()

    def extract_edges(
        self, code: str, language: str, filepath: str
    ) -> "list[Edge]":
        """Return ``CONTAINS`` edges for all top-level symbols in *code*.

        This is a thin wrapper over ``_extract_top_level_symbol()`` that
        promotes the flat symbol list to typed ``Edge`` tuples for graph
        ingestion.  Import edges (``CALLS``, ``IMPORTS``) require a deeper
        AST call-site walk and are out of scope here (roadmap Phase 2).

        Args:
            code:     Source code text.
            language: Language identifier (e.g. ``"python"``, ``"rust"``).
            filepath: Repo-relative file path used as the edge source.

        Returns:
            List of ``Edge`` objects with ``relation="CONTAINS"``.
        """
        from ..graph.builder import Edge
        from ..graph.node_id import normalize_node_id

        symbols: set[str] = set()

        # For languages with a tree-sitter resolver, use it to extract accurate symbols.
        if language in self.languages and language in self._resolvers:
            try:
                parser = self.Parser(self.languages[language])
                tree = parser.parse(bytes(code, "utf8"))
                for chunk in self._extract_definitions(
                    tree.root_node, code, filepath, language
                ):
                    symbols.update(chunk.symbols_defined)
            except Exception as e:
                logger.debug(f"extract_edges tree-sitter parse failed for {filepath!r}: {e} — using regex fallback")
                symbols.update(_extract_top_level_symbol(code))
        else:
            # Fallback: regex-based extraction for astchunk-only languages.
            symbols.update(_extract_top_level_symbol(code))

        if not symbols:
            return []

        src_id = normalize_node_id(filepath)
        return [
            Edge(src=src_id, relation="CONTAINS", dst=normalize_node_id(filepath, sym))
            for sym in sorted(symbols)
        ]

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

        relative_path = str(file_path.relative_to(repo_root))

        # Languages without a bundled tree-sitter grammar (Java, C#) use
        # astchunk exclusively — there is no resolver-path fallback for them.
        if language not in self.languages:
            if language in _ASTCHUNK_LANG_MAP:
                return self._try_astchunk(content, relative_path, language) or []
            return []

        parser = self.Parser(self.languages[language])
        tree = parser.parse(bytes(content, "utf8"))
        file_imports = self._extract_file_imports(tree.root_node, language)

        # For astchunk-handled languages, also collect call-site references from
        # the full file AST via the resolver so CALLS edges can be built downstream.
        # (astchunk creates chunks with symbols_referenced=[] — it only splits code,
        # it doesn't extract references.  We backfill here at file granularity.)
        file_call_refs: list[str] = []
        if language in _ASTCHUNK_LANG_MAP and language in self._resolvers:
            resolver = self._resolvers[language]
            all_refs = resolver.extract_references(tree.root_node)
            imports_set = set(file_imports)
            file_call_refs = [r for r in all_refs if r not in imports_set]

        # Try astchunk for every language in _ASTCHUNK_LANG_MAP (Python, TS, JS).
        if language in _ASTCHUNK_LANG_MAP:
            ast_chunks = self._try_astchunk(content, relative_path, language)
            if ast_chunks is not None:
                return _inject_imports(ast_chunks, file_imports + file_call_refs)

        # tree-sitter resolver path (Rust, and any language astchunk failed on).
        return _inject_imports(
            self._parse_with_resolver(tree, content, relative_path, language),
            file_imports,
        )

    def _parse_with_resolver(
        self, tree: Any, content: str, relative_path: str, language: str
    ) -> list[CodeChunk]:
        """Run the tree-sitter resolver path: extract → split → enrich."""
        chunks = self._extract_definitions(tree.root_node, content, relative_path, language)
        chunks = [sc for c in chunks for sc in _split_large_chunk(c)]
        return [enrich_chunk(c) for c in chunks]

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

        astchunk_language = _ASTCHUNK_LANG_MAP.get(language, language)
        try:
            builder = astchunk.ASTChunkBuilder(
                language=astchunk_language,
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

    def _collect_imports(self, root: Any, import_types: set[str], imports: set[str]) -> None:
        stack = [root]
        while stack:
            node = stack.pop()
            if node.type in import_types:
                self._extract_import_names_from_node(node, imports)
            stack.extend(reversed(node.children))

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
        self, root_node: Any, content: str, file_path: str, language: str
    ) -> list[CodeChunk]:
        chunks: list[CodeChunk] = []
        resolver = self._resolvers.get(language)
        stack = [root_node]
        while stack:
            node = stack.pop()
            if resolver and resolver.should_extract(node.type):
                chunk = resolver.node_to_chunk(node, content, file_path)
                if chunk:
                    chunks.append(chunk)
            stack.extend(reversed(node.children))
        return chunks
