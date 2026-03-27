"""Context prefix enrichment for CodeChunk objects.

Adds a structured header comment block to the top of each chunk's content so
the embedding model (and any LLM consuming the packed context) understands
which file and line range a code fragment came from.

Header format::

    # File: src/auth.py
    # Type: python
    # Lines: 10-25

    def authenticate(user): ...
"""

from dataclasses import replace

from ..models import CodeChunk


def enrich_chunk(chunk: CodeChunk) -> CodeChunk:
    """Return a new CodeChunk whose content is prefixed with a context header.

    The original chunk is never mutated.  All fields except ``content`` are
    copied verbatim.

    Args:
        chunk: Source chunk produced by the chunker pipeline.

    Returns:
        New CodeChunk with a ``# File / # Type / # Lines`` header prepended.
    """
    header = (
        f"# File: {chunk.path}\n"
        f"# Type: {chunk.language}\n"
        f"# Lines: {chunk.start_line}-{chunk.end_line}\n"
        "\n"
    )
    return replace(chunk, content=header + chunk.content)
