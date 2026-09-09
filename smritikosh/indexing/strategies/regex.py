"""Regex-based chunking for config files (TOML). Tree-sitter captures are ignored."""

from __future__ import annotations

import re

from smritikosh.engine import sm
from smritikosh.indexing.strategies._helpers import make_text_chunk
from smritikosh.models import Capture, Chunk, ParsedFile

__all__ = ["RegexChunkingStrategy"]


class RegexChunkingStrategy:
    """Split content at regex pattern boundaries; whole-file fallback."""

    mode_name = "regex"

    def __init__(self, split_pattern: str) -> None:
        self._pattern = re.compile(split_pattern, re.MULTILINE)

    @sm.tracked
    def chunk(self, parsed: ParsedFile, captures: list[Capture]) -> list[Chunk]:  # noqa: ARG002
        content = parsed.content
        matches = list(self._pattern.finditer(content))

        if not matches:
            lines = content.splitlines()
            return [make_text_chunk(parsed, content, "regex", 1, max(len(lines), 1))]

        chunks: list[Chunk] = []
        boundaries = [m.start() for m in matches] + [len(content)]

        for i, start_pos in enumerate(boundaries[:-1]):
            end_pos = boundaries[i + 1]
            section = content[start_pos:end_pos].rstrip("\n")
            if not section.strip():
                continue
            start_line = content[:start_pos].count("\n") + 1
            end_line = max(content[:end_pos].count("\n"), start_line)
            chunks.append(
                make_text_chunk(parsed, section, "regex", start_line, end_line)
            )

        return chunks
