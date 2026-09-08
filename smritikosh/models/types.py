"""Shared data types passed between smritikosh pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ChunkingStrategy(Protocol):
    """Contract for all chunking strategies (routing + chunk production)."""

    mode_name: str  # stable class-level constant used in @sm.memoized fingerprints

    def chunk(self, parsed: ParsedFile, captures: list[Capture]) -> list[Chunk]:
        """Split *parsed* into retrievable chunks using tree-sitter *captures*."""
        ...


@dataclass
class Capture:
    """A tree-sitter capture produced by the extractor."""

    capture_name: str
    node: Any
    name: str
    path: str


@dataclass
class SourceFile:
    """A source file selected for indexing."""

    path: str
    language: str
    content: str
    has_tags_scm: bool
    strategy: ChunkingStrategy

    @property
    def chunking_mode(self) -> str:
        """Return the stable chunking mode used for memo fingerprints."""
        return self.strategy.mode_name


@dataclass
class Symbol:
    """A named symbol discovered in a source file."""

    id: str
    name: str
    kind: str
    path: str
    start_line: int
    end_line: int
    parent: str | None


@dataclass
class ParsedFile:
    """A parsed source file and its tree-sitter tree."""

    path: str
    language: str
    content: str
    tree: Any


@dataclass
class Chunk:
    """A retrievable chunk of source text."""

    id: str
    path: str
    start_line: int
    end_line: int
    text: str
    chunk_kind: str
    content_hash: str


@dataclass
class SearchResult:
    """A semantic search hit returned to callers."""

    path: str
    start_line: int
    end_line: int
    snippet: str
    score: float
    chunk_kind: str | None = None
