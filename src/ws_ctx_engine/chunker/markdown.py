import os
import re
from pathlib import Path
from typing import List, Set

from .base import ASTChunker
from .base import _should_include_file
from ..models import CodeChunk
from ..logger import get_logger

logger = get_logger()


class MarkdownChunker(ASTChunker):
    """Splits Markdown files into chunks based on heading boundaries.

    Each ATX heading starts a new chunk. A file with no headings is returned
    as a single chunk so nothing is silently dropped.
    """

    EXTENSIONS: Set[str] = {'.md', '.markdown', '.mdx'}
    _HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)

    def parse(self, repo_path: str, config=None) -> List[CodeChunk]:
        if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
            raise ValueError(
                f"Repository path does not exist or is not a directory: {repo_path}"
            )
        from ..config import Config
        if config is None:
            config = Config()

        repo_path_obj = Path(repo_path)
        chunks: List[CodeChunk] = []

        for ext in self.EXTENSIONS:
            for file_path in repo_path_obj.rglob(f"*{ext}"):
                if not file_path.is_file():
                    continue
                from .base import _should_include_file
                if not _should_include_file(
                    file_path,
                    repo_path_obj,
                    config.include_patterns,
                    config.exclude_patterns
                ):
                    continue
                try:
                    chunks.extend(self._parse_file(file_path, repo_path_obj))
                except Exception as e:
                    logger.warning(f"MarkdownChunker failed on {file_path}: {e}")

        return chunks

    def _parse_file(self, file_path: Path, repo_root: Path) -> List[CodeChunk]:
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        relative_path = str(file_path.relative_to(repo_root))
        lines = content.splitlines()

        heading_starts = []
        for match in self._HEADING_RE.finditer(content):
            line_no = content[:match.start()].count('\n')
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
            chunk_lines = lines[start_0:end_0 + 1]
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
