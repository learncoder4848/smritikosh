"""Tests for SectionChunkingStrategy."""

from __future__ import annotations

from smritikosh.indexing.strategies.section import SectionChunkingStrategy
from tests.indexing.conftest import cap, node_for, parsed


class TestSectionChunkingStrategy:
    strategy = SectionChunkingStrategy()

    def test_mode_name(self) -> None:
        assert self.strategy.mode_name == "section"

    def test_one_chunk_per_capture(self) -> None:
        content = "# Heading\n\nSome text.\n"
        p = parsed(content, "doc.md")
        node = node_for(content, "# Heading")

        chunks = self.strategy.chunk(p, [cap("definition.section", node)])

        assert len(chunks) == 1
        assert chunks[0].chunk_kind == "section"

    def test_multiple_captures_produce_multiple_chunks(self) -> None:
        content = "# A\n\ntext\n\n# B\n\nmore\n"
        p = parsed(content, "doc.md")
        n1 = node_for(content, "# A")
        n2 = node_for(content, "# B")

        chunks = self.strategy.chunk(
            p, [cap("definition.section", n1), cap("definition.section", n2)]
        )

        assert len(chunks) == 2

    def test_no_captures_falls_back_to_whole_file(self) -> None:
        content = "just some text\n"
        p = parsed(content, "doc.md")

        chunks = self.strategy.chunk(p, [])

        assert len(chunks) == 1
        assert chunks[0].text == content
        assert chunks[0].chunk_kind == "section"

    def test_empty_file_no_captures_returns_one_chunk(self) -> None:
        p = parsed("", "empty.md")

        chunks = self.strategy.chunk(p, [])

        assert len(chunks) == 1
        assert chunks[0].start_line == 1
