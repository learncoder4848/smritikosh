"""Models shared by retrieval application services and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from smritikosh.models.types import SearchResult

__all__ = [
    "CandidateScore",
    "DiscoveredFile",
    "DiscoveryEvidence",
    "DiscoveryOptions",
    "DiscoveryPack",
    "EvidenceCandidate",
    "EvidenceItem",
    "EvidenceOptions",
    "EvidencePack",
    "IndexInfo",
    "IndexedChunk",
    "OutlineEntry",
    "RetrievalChannel",
    "SearchOptions",
    "SourceLine",
    "TextFileMatch",
    "TextMatch",
]


class RetrievalChannel(StrEnum):
    """Identify one independent candidate-generation channel."""

    DENSE = "dense"
    LEXICAL = "lexical"


@dataclass(frozen=True)
class IndexInfo:
    """Summarize the contents of a Smritikosh index."""

    files: int
    chunks: int
    vectors: int
    dimensions: int | None


@dataclass(frozen=True)
class IndexedChunk:
    """Represent one source chunk stored in the index."""

    chunk_id: str
    path: str
    start_line: int
    end_line: int
    text: str
    chunk_kind: str | None
    symbol: str | None = None


@dataclass(frozen=True)
class SourceLine:
    """Represent one numbered source line."""

    line_number: int
    text: str


@dataclass(frozen=True)
class OutlineEntry:
    """Summarize one definition stored for a path."""

    symbol: str | None
    chunk_kind: str | None
    start_line: int
    end_line: int


@dataclass(frozen=True)
class TextMatch:
    """Locate one source line containing exact text."""

    path: str
    line_number: int
    text: str
    exact_line: bool


@dataclass(frozen=True)
class TextFileMatch:
    """Represent one indexed file containing an exact text anchor."""

    path: str
    start_line: int
    end_line: int
    symbol: str | None = None


@dataclass(frozen=True)
class DiscoveryEvidence:
    """Locate one representative section without returning its source."""

    start_line: int
    end_line: int
    symbol: str | None = None


@dataclass(frozen=True)
class DiscoveredFile:
    """Summarize why one indexed file is a retrieval candidate."""

    path: str
    score: float
    signals: tuple[str, ...]
    matched_facets: tuple[str, ...]
    matched_anchors: tuple[str, ...]
    referenced_by: tuple[str, ...]
    evidence: tuple[DiscoveryEvidence, ...]


@dataclass(frozen=True)
class DiscoveryOptions:
    """Bound high-recall candidate-file discovery."""

    candidates_per_channel: int = 40
    max_files: int = 30
    evidence_per_file: int = 2
    max_exact_files: int = 1_000
    max_indexed_paths: int = 10_000
    max_reference_files: int = 12
    rrf_k: int = 60
    exclude_paths: tuple[str, ...] = (
        ".claude/%",
        ".cursor/%",
        ".git/%",
        ".windsurf/%",
        ".venv/%",
        "node_modules/%",
        "vendor/%",
    )


@dataclass(frozen=True)
class DiscoveryPack:
    """Return compact file candidates and whether the file cap was reached."""

    files: tuple[DiscoveredFile, ...]
    truncated: bool


@dataclass(frozen=True)
class SearchOptions:
    """Configure one candidate retrieval operation."""

    top_k: int = 10
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateScore:
    """Retain channel ranks and fused relevance for diagnostics."""

    dense_rank: int | None = None
    lexical_rank: int | None = None
    fused: float = 0.0


@dataclass
class EvidenceCandidate:
    """Represent a deduplicated candidate that may cover several facets."""

    result: SearchResult
    facets: set[str] = field(default_factory=set)
    facet_scores: dict[str, float] = field(default_factory=dict)
    score: CandidateScore = field(default_factory=CandidateScore)


@dataclass(frozen=True)
class EvidenceOptions:
    """Bound hybrid candidate generation and evidence selection."""

    candidates_per_channel: int = 30
    max_candidates: int = 400
    max_seeds: int = 16
    max_results: int = 24
    max_source_lines: int = 120
    max_chars: int = 45_000
    rrf_k: int = 60
    mmr_lambda: float = 0.7
    max_per_file: int = 2
    topic_path_boost: float = 1.25
    documentation_penalty: float = 0.75
    migration_penalty: float = 0.85
    unrelated_test_penalty: float = 0.9
    max_dependencies_per_seed: int = 4
    exclude_paths: tuple[str, ...] = (
        ".claude/%",
        ".cursor/%",
        ".git/%",
        ".windsurf/%",
        ".venv/%",
        "node_modules/%",
        "vendor/%",
    )


@dataclass(frozen=True)
class EvidenceItem:
    """Carry one selected source span and its retrieval provenance."""

    evidence_id: str
    facets: tuple[str, ...]
    result: SearchResult
    source: str
    source_truncated: bool


@dataclass(frozen=True)
class EvidencePack:
    """Return bounded evidence plus observable facet coverage."""

    items: tuple[EvidenceItem, ...]
    covered_facets: tuple[str, ...]
    missing_facets: tuple[str, ...]
    truncated: bool
