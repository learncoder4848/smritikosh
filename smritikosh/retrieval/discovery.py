"""High-recall file discovery over hybrid chunk retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from smritikosh.models.retrieval import (
    DiscoveredFile,
    DiscoveryEvidence,
    DiscoveryOptions,
    DiscoveryPack,
    EvidenceCandidate,
    EvidenceOptions,
)
from smritikosh.ports.retrieval import CandidateRetriever, SourceReader
from smritikosh.retrieval.hybrid import HybridRetriever
from smritikosh.retrieval.tokenizer import tokenize_code

__all__ = ["DiscoveryService"]

_GENERIC_PATH_TOKENS = {
    "admin",
    "api",
    "application",
    "document",
    "documentation",
    "platform",
    "plugin",
    "portal",
    "processor",
    "service",
    "skill",
    "system",
}
_SIGNAL_ORDER = ("exact-anchor", "semantic", "lexical", "referenced-domain")


@dataclass
class _FileCandidate:
    candidates: list[EvidenceCandidate] = field(default_factory=list)
    facets: set[str] = field(default_factory=set)
    anchors: set[str] = field(default_factory=set)
    referenced_by: set[str] = field(default_factory=set)
    signals: set[str] = field(default_factory=set)
    exact_evidence: list[DiscoveryEvidence] = field(default_factory=list)


class DiscoveryService:
    """Discover candidate files before loading detailed evidence."""

    def __init__(
        self,
        retrievers: tuple[CandidateRetriever, ...],
        reader: SourceReader,
    ) -> None:
        self._retrievers = retrievers
        self._reader = reader
        self._hybrid = HybridRetriever(retrievers)

    def retrieve(
        self,
        facets: tuple[str, ...],
        *,
        anchors: tuple[str, ...] = (),
        options: DiscoveryOptions | None = None,
    ) -> DiscoveryPack:
        """Combine semantic, lexical, exact, and reference signals by file."""
        options = options or DiscoveryOptions()
        normalized_facets = self._normalize(facets)
        normalized_anchors = self._normalize(anchors)
        if not normalized_facets:
            raise ValueError("At least one discovery facet is required")

        evidence_options = EvidenceOptions(
            candidates_per_channel=options.candidates_per_channel,
            max_candidates=max(400, options.max_files * 20),
            rrf_k=options.rrf_k,
            exclude_paths=options.exclude_paths,
        )
        candidates = self._hybrid.retrieve(
            normalized_facets,
            options=evidence_options,
        )
        files: dict[str, _FileCandidate] = {}
        for candidate in candidates:
            if self._is_excluded(candidate.result.path, options.exclude_paths):
                continue
            item = files.setdefault(candidate.result.path, _FileCandidate())
            item.candidates.append(candidate)
            item.facets.update(candidate.facets)
            if candidate.score.dense_rank is not None:
                item.signals.add("semantic")
            if candidate.score.lexical_rank is not None:
                item.signals.add("lexical")

        self._add_exact_matches(
            files,
            normalized_anchors,
            options=options,
        )
        self._add_referenced_domains(files, candidates, options=options)
        return self._build_pack(
            files,
            normalized_facets,
            normalized_anchors,
            options=options,
        )

    def _add_exact_matches(
        self,
        files: dict[str, _FileCandidate],
        anchors: tuple[str, ...],
        *,
        options: DiscoveryOptions,
    ) -> None:
        for anchor in anchors:
            for match in self._reader.find_text_files(
                anchor,
                limit=options.max_exact_files,
            ):
                if self._is_excluded(match.path, options.exclude_paths):
                    continue
                item = files.setdefault(match.path, _FileCandidate())
                item.anchors.add(anchor)
                item.signals.add("exact-anchor")
                evidence = DiscoveryEvidence(
                    match.start_line,
                    match.end_line,
                    match.symbol,
                )
                if evidence not in item.exact_evidence:
                    item.exact_evidence.append(evidence)

    def _add_referenced_domains(
        self,
        files: dict[str, _FileCandidate],
        candidates: list[EvidenceCandidate],
        *,
        options: DiscoveryOptions,
    ) -> None:
        paths = self._reader.find_paths("", limit=options.max_indexed_paths)
        aliases = {
            path: pattern
            for path in paths
            if not self._is_excluded(path, options.exclude_paths)
            if (pattern := self._reference_pattern(path)) is not None
        }
        references: set[tuple[str, str]] = set()
        for candidate in candidates:
            source_path = candidate.result.path
            for target_path, pattern in aliases.items():
                if target_path == source_path:
                    continue
                if pattern.search(candidate.result.snippet):
                    references.add((target_path, source_path))

        referenced_paths = sorted({target for target, _ in references})[
            : options.max_reference_files
        ]
        for target_path in referenced_paths:
            item = files.setdefault(target_path, _FileCandidate())
            item.signals.add("referenced-domain")
            item.referenced_by.update(
                source for target, source in references if target == target_path
            )

    def _build_pack(
        self,
        files: dict[str, _FileCandidate],
        facets: tuple[str, ...],
        anchors: tuple[str, ...],
        *,
        options: DiscoveryOptions,
    ) -> DiscoveryPack:
        top_fused = max(
            (
                candidate.score.fused
                for item in files.values()
                for candidate in item.candidates
            ),
            default=1.0,
        )
        scored = [
            (self._file_score(item, top_fused=top_fused), path, item)
            for path, item in files.items()
        ]
        scored.sort(key=lambda value: (-value[0], value[1]))
        truncated = len(scored) > options.max_files
        selected = scored[: options.max_files]
        maximum = max((score for score, _, _ in selected), default=1.0)
        discovered = tuple(
            DiscoveredFile(
                path=path,
                score=round(score / maximum, 3),
                signals=tuple(
                    signal for signal in _SIGNAL_ORDER if signal in item.signals
                ),
                matched_facets=tuple(facet for facet in facets if facet in item.facets),
                matched_anchors=tuple(
                    anchor for anchor in anchors if anchor in item.anchors
                ),
                referenced_by=tuple(sorted(item.referenced_by)),
                evidence=self._representative_evidence(
                    item,
                    limit=options.evidence_per_file,
                ),
            )
            for score, path, item in selected
        )
        return DiscoveryPack(discovered, truncated)

    @staticmethod
    def _file_score(item: _FileCandidate, *, top_fused: float) -> float:
        relevance = max(
            (candidate.score.fused for candidate in item.candidates),
            default=0.0,
        )
        return (
            3.0 * bool(item.anchors)
            + 3.0 * bool(item.referenced_by)
            + float(len(item.facets))
            + 0.5 * ("semantic" in item.signals)
            + 0.5 * ("lexical" in item.signals)
            + 2.0 * relevance / top_fused
        )

    @staticmethod
    def _representative_evidence(
        item: _FileCandidate,
        *,
        limit: int,
    ) -> tuple[DiscoveryEvidence, ...]:
        evidence: list[DiscoveryEvidence] = item.exact_evidence[:1]
        if len(evidence) == limit:
            return tuple(evidence)
        ranked = sorted(
            item.candidates,
            key=lambda candidate: (
                -candidate.score.fused,
                candidate.result.start_line,
            ),
        )
        for candidate in ranked:
            result = candidate.result
            location = DiscoveryEvidence(
                result.start_line,
                result.end_line,
                result.symbol,
            )
            if location not in evidence:
                evidence.append(location)
            if len(evidence) == limit:
                return tuple(evidence)
        return tuple(evidence)

    @staticmethod
    def _normalize(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))

    @staticmethod
    def _is_excluded(path: str, patterns: tuple[str, ...]) -> bool:
        return any(fnmatchcase(path, pattern.replace("%", "*")) for pattern in patterns)

    @staticmethod
    def _reference_pattern(path: str) -> re.Pattern[str] | None:
        stem = PurePosixPath(path).stem
        tokens = [
            token
            for token in tokenize_code(stem)
            if "_" not in token
            and len(token) >= 3
            and token not in _GENERIC_PATH_TOKENS
        ]
        tokens = list(dict.fromkeys(tokens))
        if not tokens:
            return None
        pluralized = [
            rf"{re.escape(token)}s?" if not token.endswith("s") else re.escape(token)
            for token in tokens
        ]
        phrase = r"[-_\s]+".join(pluralized)
        return re.compile(
            rf"\b{phrase}[-_\s]+(?:service|system|platform)\b",
            re.IGNORECASE,
        )
