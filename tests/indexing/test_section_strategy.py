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


class TestJsonSectionChunking:
    """JSON: depth chosen by size, plus a key-path label on every chunk."""

    def test_should_keep_a_small_config_flat(self) -> None:
        """Top-level sections that fit are emitted; their children are skipped.

        Both keys here are below the fragment floor, so they merge into one
        run rather than becoming two chunks too small to retrieve — see
        test_should_not_merge_a_section_that_is_already_big_enough for the
        stand-alone case.
        """
        content = '{\n  "a": {"inner": 1},\n  "b": 2\n}'
        p = parsed(content, "c.json", language="json")
        captures = [
            cap("definition.section", node_for(content, '"a": {"inner": 1}'), key="a"),
            cap("definition.subsection", node_for(content, '"inner": 1'), key="inner"),
            cap("definition.section", node_for(content, '"b": 2'), key="b"),
        ]

        chunks = SectionChunkingStrategy(max_chars=500).chunk(p, captures)

        assert len(chunks) == 1
        assert chunks[0].text.splitlines()[0] == "// a+b"
        assert '"inner": 1' in chunks[0].text  # child travelled with its parent

    def test_should_not_merge_a_section_that_is_already_big_enough(self) -> None:
        """A capture at or above the floor stands alone with its own path."""
        big_a = '"a": "' + "x" * 120 + '"'
        big_b = '"b": "' + "y" * 120 + '"'
        content = "{\n  " + big_a + ",\n  " + big_b + "\n}"
        p = parsed(content, "c.json", language="json")
        captures = [
            cap("definition.section", node_for(content, big_a), key="a"),
            cap("definition.section", node_for(content, big_b), key="b"),
        ]

        chunks = SectionChunkingStrategy(max_chars=500).chunk(p, captures)

        assert [c.text.splitlines()[0] for c in chunks] == ["// a", "// b"]

    def test_should_descend_into_an_oversized_section(self) -> None:
        """An oversized parent is discarded in favour of the keys inside it."""
        inner_a = '"inner_a": "' + "x" * 200 + '"'
        inner_b = '"inner_b": "' + "y" * 200 + '"'
        outer = f'"outer": {{{inner_a}, {inner_b}}}'
        content = "{\n  " + outer + "\n}"
        p = parsed(content, "c.json", language="json")
        captures = [
            cap("definition.section", node_for(content, outer), key="outer"),
            cap("definition.subsection", node_for(content, inner_a), key="inner_a"),
            cap("definition.subsection", node_for(content, inner_b), key="inner_b"),
        ]

        chunks = SectionChunkingStrategy(max_chars=300).chunk(p, captures)

        first_lines = [c.text.splitlines()[0] for c in chunks]
        assert "// outer.inner_a" in first_lines
        assert "// outer.inner_b" in first_lines
        assert not any(line == "// outer" for line in first_lines)

    def test_should_emit_an_oversized_leaf_rather_than_dropping_it(self) -> None:
        """No deeper capture exists, so line-window splitting is the backstop."""
        big = '"solo": "' + "z" * 900 + '"'
        content = "{\n  " + big + "\n}"
        p = parsed(content, "c.json", language="json")

        chunks = SectionChunkingStrategy(max_chars=300).chunk(
            p, [cap("definition.section", node_for(content, big), key="solo")]
        )

        assert chunks
        assert all("z" in c.text for c in chunks)

    def test_should_not_label_markdown_sections(self) -> None:
        """A heading is already natural language; a path would add noise."""
        content = "# Heading\n\nSome text.\n"
        p = parsed(content, "doc.md", language="markdown")

        heading = cap(
            "definition.section", node_for(content, "# Heading"), key="Heading"
        )

        chunks = SectionChunkingStrategy(max_chars=500).chunk(p, [heading])

        assert not chunks[0].text.startswith("//")

    def test_should_reserve_budget_for_the_key_path_prefix(self) -> None:
        """The prefix eats the window, so the budget must account for it.

        Uses a multi-line body: a single over-long line is deliberately never
        broken (see split_oversized), so it is the wrong fixture for a budget
        assertion.
        """
        body = '"k": [\n' + "\n".join(f'    "v{i}",' for i in range(60)) + "\n  ]"
        content = "{\n  " + body + "\n}"
        p = parsed(content, "c.json", language="json")

        chunks = SectionChunkingStrategy(max_chars=200).chunk(
            p, [cap("definition.section", node_for(content, body), key="k")]
        )

        assert len(chunks) > 1
        assert all(len(c.text) <= 200 for c in chunks)
        assert all(c.text.startswith("// k\n") for c in chunks)

    def test_should_keep_an_unsplittable_line_whole(self) -> None:
        """One giant line is a literal; cutting it would corrupt the snippet."""
        body = '"k": "' + "q" * 400 + '"'
        content = "{\n  " + body + "\n}"
        p = parsed(content, "c.json", language="json")

        chunks = SectionChunkingStrategy(max_chars=200).chunk(
            p, [cap("definition.section", node_for(content, body), key="k")]
        )

        assert len(chunks) == 1
        assert "q" * 400 in chunks[0].text

    def test_should_not_descend_into_fragment_sized_children(self) -> None:
        """Tiny keys retrieve worse than one coarse chunk, so keep the parent."""
        kids = ", ".join(f'"k{i}": {i}' for i in range(40))
        outer = f'"outer": {{{kids}}}'
        content = "{\n  " + outer + "\n}"
        p = parsed(content, "c.json", language="json")
        captures = [cap("definition.section", node_for(content, outer), key="outer")]
        captures += [
            cap("definition.subsection", node_for(content, f'"k{i}": {i}'), key=f"k{i}")
            for i in range(40)
        ]

        chunks = SectionChunkingStrategy(max_chars=200).chunk(p, captures)

        # Every chunk is labelled with the parent, not the fragment-sized keys.
        assert all(c.text.startswith("// outer\n") for c in chunks)
