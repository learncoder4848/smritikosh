"""Character-budgeted evidence context packing."""

from __future__ import annotations

from dataclasses import replace

from smritikosh.models import SearchResult
from smritikosh.models.retrieval import (
    EvidenceCandidate,
    EvidenceItem,
    EvidenceOptions,
    EvidencePack,
    SourceLine,
)
from smritikosh.ports.retrieval import SourceReader

__all__ = ["EvidencePacker"]

_METADATA_RESERVE = 5_000
_ITEM_METADATA_ESTIMATE = 180


class EvidencePacker:
    """Pack evidence without silently dropping facet coverage."""

    def __init__(self, reader: SourceReader) -> None:
        self._reader = reader

    def pack(
        self,
        candidates: list[EvidenceCandidate],
        facets: tuple[str, ...],
        *,
        options: EvidenceOptions,
    ) -> EvidencePack:
        """Read numbered source and retain items fitting the character budget."""
        items: list[EvidenceItem] = []
        used_chars: int = 0
        covered: set[str] = set()
        metadata_reserve: int = min(_METADATA_RESERVE, options.max_chars // 4)
        for candidate in candidates:
            item: EvidenceItem = self._item(
                candidate,
                evidence_id=f"E{len(items) + 1}",
                max_source_lines=options.max_source_lines,
            )
            estimated_chars: int = (
                len(item.source)
                + len(item.result.path)
                + sum(len(facet) for facet in item.facets)
                + _ITEM_METADATA_ESTIMATE
            )
            if used_chars + estimated_chars > options.max_chars - metadata_reserve:
                continue
            items.append(item)
            used_chars += estimated_chars
            covered.update(item.facets)
            if len(items) == options.max_results:
                break
        missing: tuple[str, ...] = tuple(
            facet for facet in facets if facet not in covered
        )
        return EvidencePack(
            items=tuple(items),
            covered_facets=tuple(facet for facet in facets if facet in covered),
            missing_facets=missing,
            truncated=len(items) < len(candidates),
        )

    def _item(
        self,
        candidate: EvidenceCandidate,
        *,
        evidence_id: str,
        max_source_lines: int,
    ) -> EvidenceItem:
        result: SearchResult = candidate.result
        returned_end: int = min(
            result.end_line,
            result.start_line + max_source_lines - 1,
        )
        lines: list[SourceLine] = self._reader.get_source_lines(
            result.path,
            start_line=result.start_line,
            end_line=returned_end,
        )
        source: str = self._numbered_source(lines)
        if not source:
            source = self._numbered_snippet(
                result,
                max_source_lines=max_source_lines,
            )
        return EvidenceItem(
            evidence_id=evidence_id,
            facets=tuple(sorted(candidate.facets)),
            result=replace(result, end_line=returned_end),
            source=source,
            source_truncated=returned_end < result.end_line,
        )

    @staticmethod
    def _numbered_source(lines: list[SourceLine]) -> str:
        if not lines:
            return ""
        width: int = len(str(lines[-1].line_number))
        return "\n".join(f"{line.line_number:>{width}}  {line.text}" for line in lines)

    @staticmethod
    def _numbered_snippet(
        result: SearchResult,
        *,
        max_source_lines: int,
    ) -> str:
        lines: list[str] = result.snippet.splitlines()[:max_source_lines]
        if not lines:
            return ""
        width: int = len(str(result.start_line + len(lines) - 1))
        return "\n".join(
            f"{result.start_line + offset:>{width}}  {line}"
            for offset, line in enumerate(lines)
        )
