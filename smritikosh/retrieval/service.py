"""Application service for bounded hybrid evidence retrieval."""

from __future__ import annotations

from smritikosh.models.retrieval import (
    EvidenceCandidate,
    EvidenceOptions,
    EvidencePack,
)
from smritikosh.ports.retrieval import CandidateRetriever, SourceReader
from smritikosh.retrieval.expansion import EvidenceExpander
from smritikosh.retrieval.hybrid import HybridRetriever
from smritikosh.retrieval.packing import EvidencePacker
from smritikosh.retrieval.priors import apply_metadata_priors, infer_topic
from smritikosh.retrieval.selection import select_evidence_seeds

__all__ = ["EvidenceService"]


class EvidenceService:
    """Retrieve high-recall evidence through independent retrieval ports."""

    def __init__(
        self,
        retrievers: tuple[CandidateRetriever, ...],
        reader: SourceReader,
    ) -> None:
        self._retrievers = retrievers
        self._reader = reader
        self._hybrid = HybridRetriever(retrievers)
        self._expander = EvidenceExpander(reader)
        self._packer = EvidencePacker(reader)

    def retrieve(
        self,
        facets: tuple[str, ...],
        *,
        options: EvidenceOptions | None = None,
    ) -> EvidencePack:
        """Retrieve, fuse, expand, and pack evidence for caller-supplied facets."""
        options = options or EvidenceOptions()
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
        candidates: list[EvidenceCandidate] = self._hybrid.retrieve(
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
        seeds: list[EvidenceCandidate] = select_evidence_seeds(
            candidates,
            normalized,
            options=options,
        )
        expanded: list[EvidenceCandidate] = self._expander.expand(
            seeds,
            options=options,
        )
        return self._packer.pack(expanded, normalized, options=options)
