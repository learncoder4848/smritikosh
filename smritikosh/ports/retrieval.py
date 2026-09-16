"""Ports used by retrieval application services."""

from __future__ import annotations

from typing import Protocol

from smritikosh.models import Chunk, SearchResult
from smritikosh.models.retrieval import (
    IndexedChunk,
    OutlineEntry,
    RetrievalChannel,
    SearchOptions,
    SourceLine,
    TextFileMatch,
    TextMatch,
)

__all__ = ["CandidateRetriever", "LexicalStore", "SourceReader"]


class CandidateRetriever(Protocol):
    """Generate one ranked candidate list for a query."""

    @property
    def channel(self) -> RetrievalChannel:
        """Identify this independent retrieval channel."""

    def retrieve(
        self,
        query: str,
        *,
        options: SearchOptions,
    ) -> list[SearchResult]:
        """Return candidates ordered from most to least relevant."""


class SourceReader(Protocol):
    """Read indexed source metadata without knowing its storage backend."""

    def find_paths(self, pattern: str, *, limit: int = 50) -> list[str]: ...

    def find_text_lines(
        self,
        text: str,
        *,
        path: str | None = None,
        limit: int = 20,
    ) -> list[TextMatch]: ...

    def find_text_files(self, text: str, *, limit: int = 1_000) -> list[TextFileMatch]:
        """Return at most one exact-anchor location per indexed file."""

    def get_chunks(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> list[IndexedChunk]: ...

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[IndexedChunk]: ...

    def get_outline(self, path: str) -> list[OutlineEntry]: ...

    def get_source_lines(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> list[SourceLine]: ...


class LexicalStore(Protocol):
    """Maintain and query a lexical index alongside dense vectors."""

    def setup(self) -> None:
        """Create lexical storage when absent."""

    def upsert(self, chunks: list[Chunk]) -> None:
        """Insert or replace lexical documents for chunks."""

    def delete(self, chunk_id: str) -> None:
        """Remove one lexical document."""

    def delete_path(self, path: str) -> None:
        """Remove every lexical document belonging to a path."""

    def clear(self) -> None:
        """Remove every lexical document and posting."""

    def search(
        self,
        query: str,
        *,
        options: SearchOptions,
    ) -> list[tuple[str, float]]:
        """Return chunk ids and BM25 scores ordered by relevance."""
