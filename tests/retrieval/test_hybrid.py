"""Tests for hybrid candidate generation."""

from smritikosh.models import SearchResult
from smritikosh.models.retrieval import EvidenceOptions, RetrievalChannel, SearchOptions
from smritikosh.retrieval.hybrid import HybridRetriever


class _Retriever:
    channel = RetrievalChannel.LEXICAL

    def __init__(self) -> None:
        self.options: SearchOptions | None = None

    def retrieve(
        self,
        query: str,
        *,
        options: SearchOptions,
    ) -> list[SearchResult]:
        self.options = options
        return [
            SearchResult(
                "docs/Transaction_System.md",
                1,
                10,
                "transaction lifecycle",
                1.0,
                "section",
                "Transaction lifecycle",
                "markdown-chunk",
            )
        ]


def test_should_search_documentation_for_domain_queries() -> None:
    retriever = _Retriever()
    hybrid = HybridRetriever((retriever,))

    results = hybrid.retrieve(
        ("transaction lifecycle",),
        options=EvidenceOptions(),
    )

    assert [result.result.path for result in results] == ["docs/Transaction_System.md"]
    assert retriever.options is not None
    assert "docs/%" not in retriever.options.exclude_paths
