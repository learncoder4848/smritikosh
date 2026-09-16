"""Tests for generic post-fusion metadata priors."""

from smritikosh.models import SearchResult
from smritikosh.models.retrieval import (
    CandidateScore,
    EvidenceCandidate,
    EvidenceOptions,
)
from smritikosh.retrieval.priors import apply_metadata_priors


class _Reader:
    def find_paths(self, pattern: str, *, limit: int = 50) -> list[str]:
        if pattern == "order_export":
            return [
                "src/order_export.py",
                "src/order_export_handler.py",
                "tests/test_order_export.py",
            ]
        return []


def _candidate(path: str, score: float = 0.1) -> EvidenceCandidate:
    return EvidenceCandidate(
        result=SearchResult(path, 1, 2, "code", 0.5, "function", "run"),
        facets={"order export retry"},
        facet_scores={"order export retry": score},
        score=CandidateScore(fused=score),
    )


def test_should_prefer_topic_source_and_demote_unrequested_documentation() -> None:
    documentation = _candidate("docs/order_export.md")
    sibling = _candidate("src/payment_export.py")
    topic = _candidate("src/order_export.py")

    ranked = apply_metadata_priors(
        [documentation, sibling, topic],
        ("order export flow",),
        _Reader(),
        options=EvidenceOptions(),
    )

    assert [candidate.result.path for candidate in ranked] == [
        "src/order_export.py",
        "src/payment_export.py",
        "docs/order_export.md",
    ]


def test_should_not_demote_docs_when_documentation_dominates_candidates() -> None:
    primary = _candidate("knowledge/Transaction_System.md", 0.1)
    secondary = _candidate("knowledge/Ledger_System.md", 0.09)
    code = _candidate("src/transaction.py", 0.08)

    ranked = apply_metadata_priors(
        [primary, secondary, code],
        ("transaction lifecycle",),
        _Reader(),
        options=EvidenceOptions(),
    )

    assert [candidate.result.path for candidate in ranked] == [
        "knowledge/Transaction_System.md",
        "knowledge/Ledger_System.md",
        "src/transaction.py",
    ]
