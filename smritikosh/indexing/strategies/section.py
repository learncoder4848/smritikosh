"""Section-based chunking for document files (Markdown, JSON)."""

from __future__ import annotations

from smritikosh.engine import sm
from smritikosh.indexing.strategies._helpers import make_node_chunk, make_text_chunk
from smritikosh.models import Capture, Chunk, ParsedFile

__all__ = ["SectionChunkingStrategy"]


class SectionChunkingStrategy:
    """One chunk per @definition.section capture; whole-file fallback."""

    mode_name = "section"

    @sm.tracked
    def chunk(self, parsed: ParsedFile, captures: list[Capture]) -> list[Chunk]:
        if not captures:
            lines = parsed.content.splitlines()
            return [
                make_text_chunk(
                    parsed, parsed.content, "section", 1, max(len(lines), 1)
                )
            ]
        return [make_node_chunk(parsed, cap.node, "section") for cap in captures]
