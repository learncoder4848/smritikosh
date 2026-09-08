"""Tests for RegexChunkingStrategy."""

from __future__ import annotations

from smritikosh.indexing.strategies.regex import RegexChunkingStrategy
from tests.indexing.conftest import FakeNode, cap, parsed

TOML_PATTERN = r"^\[+[^\]]+\]"


class TestRegexChunkingStrategy:
    strategy = RegexChunkingStrategy(TOML_PATTERN)

    def test_mode_name(self) -> None:
        assert self.strategy.mode_name == "regex"

    def test_splits_toml_into_table_sections(self) -> None:
        content = "[tool.poetry]\nname = 'foo'\n\n[tool.ruff]\nline-length = 88\n"
        p = parsed(content, "pyproject.toml")

        chunks = self.strategy.chunk(p, [])

        assert len(chunks) == 2
        assert "[tool.poetry]" in chunks[0].text
        assert "[tool.ruff]" in chunks[1].text

    def test_no_matches_returns_whole_file_chunk(self) -> None:
        content = "just plain text\nno tables here\n"
        p = parsed(content, "config.toml")

        chunks = self.strategy.chunk(p, [])

        assert len(chunks) == 1
        assert chunks[0].text == content
        assert chunks[0].chunk_kind == "regex"

    def test_captures_are_ignored(self) -> None:
        """RegexChunkingStrategy must ignore any captures passed in."""
        content = "[section]\nkey = 'value'\n"
        p = parsed(content, "cfg.toml")
        dummy_node = FakeNode(
            start_byte=0, end_byte=5, start_point=(0, 0), end_point=(0, 5)
        )
        dummy_cap = cap("definition.section", dummy_node)

        assert self.strategy.chunk(p, [dummy_cap]) == self.strategy.chunk(p, [])

    def test_chunk_ids_stable_across_calls(self) -> None:
        content = "[a]\nx=1\n\n[b]\ny=2\n"
        p = parsed(content, "x.toml")

        c1 = self.strategy.chunk(p, [])
        c2 = self.strategy.chunk(p, [])

        assert [c.id for c in c1] == [c.id for c in c2]

    def test_single_table_produces_one_chunk(self) -> None:
        content = "[dependencies]\npytest = '^9'\n"
        p = parsed(content, "pyproject.toml")

        chunks = self.strategy.chunk(p, [])

        assert len(chunks) == 1
        assert "dependencies" in chunks[0].text
