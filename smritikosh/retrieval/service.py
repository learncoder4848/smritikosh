"""Application service for bounded hybrid code search."""

from __future__ import annotations

from smritikosh.models.retrieval import (
    HybridSearchOptions,
    RankedCandidate,
    SearchLocation,
)
from smritikosh.ports.retrieval import CandidateRetriever, SourceReader
from smritikosh.retrieval.expansion import CandidateExpander
from smritikosh.retrieval.hybrid import HybridRetriever
from smritikosh.retrieval.priors import apply_metadata_priors, infer_topic
from smritikosh.retrieval.selection import select_seeds

__all__ = ["HybridSearchService"]


class HybridSearchService:
    """Locate high-recall definitions through independent retrieval ports."""

    def __init__(
        self,
        retrievers: tuple[CandidateRetriever, ...],
        reader: SourceReader,
    ) -> None:
        self._retrievers = retrievers
        self._reader = reader
        self._hybrid = HybridRetriever(retrievers)
        self._expander = CandidateExpander(reader)

    def search(
        self,
        facets: tuple[str, ...],
        *,
        options: HybridSearchOptions | None = None,
    ) -> list[SearchLocation]:
        """Retrieve, fuse, and expand locations for caller-supplied facets."""
        options = options or HybridSearchOptions()
        normalized: tuple[str, ...] = tuple(
            facet.strip() for facet in facets if facet.strip()
        )
        if not normalized:
            raise ValueError("At least one retrieval facet is required")
        topic, _ = infer_topic(self._reader, normalized[0])
        queries: dict[str, str] = {
            facet: (
                facet if topic is None or topic in facet.lower() else f"{topic} {facet}"
            )
            for facet in normalized
        }
        candidates: list[RankedCandidate] = self._hybrid.retrieve(
            normalized,
            options=options,
            queries=queries,
        )
        candidates = apply_metadata_priors(
            candidates,
            normalized,
            self._reader,
            options=options,
        )
        seeds: list[RankedCandidate] = select_seeds(
            candidates,
            normalized,
            options=options,
        )
        expanded: list[RankedCandidate] = self._expander.expand(
            seeds,
            options=options,
        )
        return [
            SearchLocation(
                path=candidate.result.path,
                start_line=candidate.result.start_line,
                end_line=candidate.result.end_line,
                symbol=candidate.result.symbol,
                # Facet order follows the caller's arguments so a renderer can
                # label facets positionally without re-deriving their order.
                facets=tuple(
                    facet for facet in normalized if facet in candidate.facets
                ),
            )
            for candidate in expanded
        ]
