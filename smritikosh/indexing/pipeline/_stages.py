"""CPU-bound pipeline stages — each runs in a thread pool via @sm.threaded.

All three wrappers follow the same naming convention:

    verb_file()   ← the @sm.tracked implementation in its own module
    _verb()       ← the @sm.threaded wrapper used by the pipeline

This ensures the asyncio event loop is never blocked while sm.fan_out
processes many files concurrently.
"""

from __future__ import annotations

from smritikosh.engine import sm
from smritikosh.indexing.chunker import chunk_file
from smritikosh.indexing.extractor import extract_file, extract_references
from smritikosh.indexing.grapher import graph_file
from smritikosh.indexing.parser import parse_file
from smritikosh.models import (
    Capture,
    Chunk,
    ChunkingStrategy,
    ParsedFile,
    Reference,
    SourceFile,
    Symbol,
)


@sm.threaded
def _parse(source: SourceFile) -> ParsedFile:
    """Wrap parse_file in asyncio.to_thread — tree-sitter releases the GIL."""
    return parse_file(source)


@sm.threaded
def _extract(parsed: ParsedFile, has_tags_scm: bool) -> list[Capture]:
    """Wrap extract_file in asyncio.to_thread — tree-sitter query on a thread."""
    return extract_file(parsed, has_tags_scm)


@sm.threaded
def _chunk(
    parsed: ParsedFile,
    captures: list[Capture],
    strategy: ChunkingStrategy,
) -> list[Chunk]:
    """Wrap chunk_file in asyncio.to_thread — AST traversal on a thread."""
    return chunk_file(parsed, captures, strategy)


@sm.threaded
def _extract_references(parsed: ParsedFile, has_tags_scm: bool) -> list[Capture]:
    """Wrap extract_references in asyncio.to_thread — a second query pass.

    Deliberately a separate pass rather than one widened query: the chunker
    consumes ``_extract``'s output, and a reference capture arriving there
    would be grouped into chunks as though it defined something.
    """
    return extract_references(parsed, has_tags_scm)


@sm.threaded
def _graph(
    parsed: ParsedFile,
    definitions: list[Capture],
    references: list[Capture],
) -> tuple[list[Symbol], list[Reference]]:
    """Wrap graph_file in asyncio.to_thread — line arithmetic over captures."""
    return graph_file(parsed, definitions, references)
