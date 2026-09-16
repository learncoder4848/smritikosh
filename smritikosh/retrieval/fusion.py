"""Rank-based fusion for independent retrieval channels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from smritikosh.models import SearchResult
from smritikosh.models.retrieval import (
    CandidateScore,
    EvidenceCandidate,
    RetrievalChannel,
)

__all__ = ["fuse_ranked_results"]

_FACET_COVERAGE_RANK: Final[int] = 10


@dataclass
class _Accumulator:
    result: SearchResult
    facets: set[str] = field(default_factory=set)
    dense_rank: int | None = None
    lexical_rank: int | None = None
    fused: float = 0.0
    facet_scores: dict[str, float] = field(default_factory=dict)


def _identity(result: SearchResult) -> tuple[str, str, str | None]:
    identity: str = result.symbol or f"@{result.start_line}:{result.end_line}"
    return (result.path, identity, result.chunk_kind)


def fuse_ranked_results(
    ranked: dict[str, dict[RetrievalChannel, list[SearchResult]]],
    *,
    rrf_k: int = 60,
) -> list[EvidenceCandidate]:
    """Fuse dense and lexical ranks with Reciprocal Rank Fusion."""
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    accumulated: dict[tuple[str, str, str | None], _Accumulator] = {}
    for facet, channels in ranked.items():
        for channel, results in channels.items():
            unique_results: list[SearchResult] = []
            seen: set[tuple[str, str, str | None]] = set()
            for result in results:
                key: tuple[str, str, str | None] = _identity(result)
                if key not in seen:
                    seen.add(key)
                    unique_results.append(result)
            for rank, result in enumerate(unique_results, start=1):
                key: tuple[str, str, str | None] = _identity(result)
                item: _Accumulator = accumulated.setdefault(
                    key,
                    _Accumulator(result=result),
                )
                contribution: float = 1.0 / (rrf_k + rank)
                if rank <= _FACET_COVERAGE_RANK:
                    item.facets.add(facet)
                item.fused += contribution
                item.facet_scores[facet] = (
                    item.facet_scores.get(facet, 0.0) + contribution
                )
                if channel is RetrievalChannel.DENSE:
                    item.dense_rank = min(item.dense_rank or rank, rank)
                elif channel is RetrievalChannel.LEXICAL:
                    item.lexical_rank = min(item.lexical_rank or rank, rank)
    candidates: list[EvidenceCandidate] = [
        EvidenceCandidate(
            result=item.result,
            facets=item.facets,
            facet_scores=item.facet_scores,
            score=CandidateScore(
                dense_rank=item.dense_rank,
                lexical_rank=item.lexical_rank,
                fused=item.fused,
            ),
        )
        for item in accumulated.values()
    ]
    candidates.sort(
        key=lambda candidate: (
            -candidate.score.fused,
            candidate.result.path,
            candidate.result.start_line,
        )
    )
    return candidates
