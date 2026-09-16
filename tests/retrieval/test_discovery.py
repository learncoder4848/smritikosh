"""Tests for high-recall file-level discovery."""

from __future__ import annotations

from smritikosh.models import (
    DiscoveryOptions,
    RetrievalChannel,
    SearchResult,
    TextFileMatch,
)
from smritikosh.retrieval.discovery import DiscoveryService


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
        return [
            "Account_System.md",
            "Card_System.md",
            "Offers_System.md",
        ][:limit]

    def find_text_files(
        self,
        text: str,
        *,
        limit: int = 1_000,
    ) -> list[TextFileMatch]:
        if text != "product_id":
            return []
        return [
            TextFileMatch("Account_System.md", 38, 41, "Events"),
            TextFileMatch("Offers_System.md", 203, 214, "Offers API"),
        ][:limit]


def test_should_union_hybrid_exact_and_referenced_file_signals() -> None:
    query = "change an account product"
    account = SearchResult(
        "Account_System.md",
        38,
        41,
        "propagates to cards-service after changing the account",
        0.9,
        "section",
        "Event capabilities",
        "account-events",
    )
    service = DiscoveryService(
        (
            _Retriever(RetrievalChannel.DENSE, {query: [account]}),
            _Retriever(RetrievalChannel.LEXICAL, {query: [account]}),
        ),
        _Reader(),
    )

    pack = service.retrieve(
        (query,),
        anchors=("product_id",),
        options=DiscoveryOptions(max_files=10, evidence_per_file=1),
    )

    discovered = {item.path: item for item in pack.files}
    assert set(discovered) == {
        "Account_System.md",
        "Card_System.md",
        "Offers_System.md",
    }
    assert discovered["Account_System.md"].signals == (
        "exact-anchor",
        "semantic",
        "lexical",
    )
    assert discovered["Offers_System.md"].matched_anchors == ("product_id",)
    assert discovered["Card_System.md"].signals == ("referenced-domain",)
    assert discovered["Card_System.md"].referenced_by == ("Account_System.md",)
    assert len(discovered["Account_System.md"].evidence) == 1


def test_should_return_one_ranked_entry_per_file_and_enforce_cap() -> None:
    query = "account state"
    results = [
        SearchResult("a.md", 1, 3, "account", 0.9, "section", "A", "a-1"),
        SearchResult("a.md", 10, 12, "state", 0.8, "section", "B", "a-2"),
        SearchResult("b.md", 1, 2, "state", 0.7, "section", "C", "b-1"),
    ]
    service = DiscoveryService(
        (_Retriever(RetrievalChannel.DENSE, {query: results}),),
        _Reader(),
    )

    pack = service.retrieve(
        (query,),
        options=DiscoveryOptions(max_files=1, evidence_per_file=2),
    )

    assert pack.truncated is True
    assert [item.path for item in pack.files] == ["a.md"]
    assert len(pack.files[0].evidence) == 2
