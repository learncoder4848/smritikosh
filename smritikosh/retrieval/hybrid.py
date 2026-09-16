"""Hybrid candidate generation and rank fusion."""

from __future__ import annotations

from smritikosh.models import SearchResult
from smritikosh.models.retrieval import (
    EvidenceCandidate,
    EvidenceOptions,
    RetrievalChannel,
    SearchOptions,
)
from smritikosh.ports.retrieval import CandidateRetriever
from smritikosh.retrieval.fusion import fuse_ranked_results

__all__ = ["HybridRetriever"]


class HybridRetriever:
    """Generate and fuse candidates from independent retrieval channels."""

    def __init__(self, retrievers: tuple[CandidateRetriever, ...]) -> None:
        self._retrievers = retrievers

    def retrieve(
        self,
        facets: tuple[str, ...],
        *,
        options: EvidenceOptions,
        queries: dict[str, str] | None = None,
    ) -> list[EvidenceCandidate]:
        """Retrieve each facet independently and fuse channel ranks."""
        queries = queries or {facet: facet for facet in facets}
        ranked: dict[str, dict[RetrievalChannel, list[SearchResult]]] = {}
        for facet in facets:
            query: str = queries[facet]
            lowered: str = query.lower()
            documentation_requested: bool = any(
                term in lowered for term in ("documentation", "docs", "readme")
            )
            exclusions: tuple[str, ...] = options.exclude_paths
            if not documentation_requested:
                exclusions += ("docs/%", "%/README.md", "%/README.mdx")
            search_options = SearchOptions(
                top_k=options.candidates_per_channel,
                exclude_paths=exclusions,
            )
            ranked[facet] = {
                retriever.channel: retriever.retrieve(
                    query,
                    options=search_options,
                )
                for retriever in self._retrievers
            }
        return fuse_ranked_results(ranked, rrf_k=options.rrf_k)[
            : options.max_candidates
        ]
