"""Tests for the hybrid evidence application service."""

from __future__ import annotations

from smritikosh.models import SearchResult
from smritikosh.models.retrieval import (
    CandidateScore,
    EvidenceCandidate,
    EvidenceOptions,
    IndexedChunk,
    OutlineEntry,
    RetrievalChannel,
    SourceLine,
)
from smritikosh.retrieval.expansion import EvidenceExpander
from smritikosh.retrieval.service import EvidenceService


class _Retriever:
    def __init__(
        self,
        channel: RetrievalChannel,
        results: dict[str, list[SearchResult]],
    ) -> None:
        self.channel = channel
        self._results = results

    def retrieve(self, query: str, *, options: object) -> list[SearchResult]:
        return self._results.get(query, [])


class _Reader:
    def find_paths(self, pattern: str, *, limit: int = 50) -> list[str]:
        return []

    def find_text_lines(
        self,
        text: str,
        *,
        path: str | None = None,
        limit: int = 20,
    ) -> list[object]:
        return []

    def get_chunks(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> list[IndexedChunk]:
        return []

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[IndexedChunk]:
        return []

    def get_outline(self, path: str) -> list[OutlineEntry]:
        return [OutlineEntry("load", "function", 1, 2)]

    def get_source_lines(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> list[SourceLine]:
        return [SourceLine(1, f"def load_{path.replace('/', '_')}():")]


def test_should_return_observable_coverage_for_every_facet() -> None:
    flow = SearchResult(
        "src/flow.py",
        1,
        2,
        "def load(): pass",
        0.9,
        "function",
        "load",
    )
    retry = SearchResult(
        "src/retry.py",
        1,
        2,
        "def load(): pass",
        0.8,
        "function",
        "load",
    )
    service = EvidenceService(
        (
            _Retriever(RetrievalChannel.DENSE, {"flow": [flow], "retry": [retry]}),
            _Retriever(RetrievalChannel.LEXICAL, {"flow": [flow], "retry": [retry]}),
        ),
        _Reader(),
    )

    pack = service.retrieve(
        ("flow", "retry"),
        options=EvidenceOptions(max_seeds=2, max_results=2),
    )

    assert pack.covered_facets == ("flow", "retry")
    assert pack.missing_facets == ()
    assert [item.result.path for item in pack.items] == [
        "src/flow.py",
        "src/retry.py",
    ]


def test_should_keep_distinct_chunks_from_the_same_markdown_section() -> None:
    seeds = [
        EvidenceCandidate(
            result=SearchResult(
                "Transaction_System.md",
                start,
                end,
                snippet,
                0.9,
                "section",
                "Transaction Lifecycle Management",
                chunk_id,
            ),
            facets={"transaction lifecycle"},
            score=CandidateScore(fused=0.1),
        )
        for start, end, snippet, chunk_id in (
            (20, 42, "states and statuses", "lifecycle-1"),
            (43, 46, "reversal versioning", "lifecycle-2"),
        )
    ]

    expanded = EvidenceExpander(_Reader()).expand(
        seeds,
        options=EvidenceOptions(max_results=2, max_dependencies_per_seed=0),
    )

    assert [item.result.chunk_id for item in expanded] == [
        "lifecycle-1",
        "lifecycle-2",
    ]
