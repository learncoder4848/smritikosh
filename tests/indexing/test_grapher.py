"""Tests for turning captures into graph symbols and unresolved references."""

from __future__ import annotations

import pytest
from tree_sitter import Parser
from tree_sitter_language_pack import get_language

from smritikosh.indexing.extractor import extract_file, extract_references
from smritikosh.indexing.grapher import graph_file, name_tail
from smritikosh.models import ParsedFile, Reference, Symbol


def _graph(
    source: str,
    *,
    path: str = "app.py",
) -> tuple[list[Symbol], list[Reference]]:
    tree = Parser(get_language("python")).parse(source.encode("utf-8"))
    parsed = ParsedFile(path=path, language="python", content=source, tree=tree)
    return graph_file(
        parsed,
        extract_file(parsed, has_tags_scm=True),
        extract_references(parsed, has_tags_scm=True),
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("billing.validate", "validate"),
        ("utils.json.loads", "loads"),
        ("mod::fn", "fn"),
        ("log", "log"),
        ("", ""),
    ],
)
def test_should_return_last_segment_when_name_is_qualified(
    name: str,
    expected: str,
) -> None:
    assert name_tail(name) == expected


def test_should_record_the_name_as_written_rather_than_what_it_resolves_to() -> None:
    source = "def charge(amount):\n    billing.validate(amount)\n"

    _, references = _graph(source)

    assert [(r.name, r.line) for r in references] == [("validate", 2)]


def test_should_attribute_a_call_to_the_innermost_enclosing_definition() -> None:
    source = "class Client:\n    def fetch(self):\n        retrieve()\n"

    symbols, references = _graph(source)

    method = next(s for s in symbols if s.name == "fetch")
    assert [r.src_symbol for r in references] == [method.id]


def test_should_drop_a_mention_that_sits_outside_every_definition() -> None:
    source = "configure()\n\ndef run():\n    pass\n"

    _, references = _graph(source)

    assert references == []


def test_should_drop_builtins_that_no_repository_symbol_could_satisfy() -> None:
    source = "def run(items):\n    return len(sorted(items))\n"

    _, references = _graph(source)

    assert references == []


def test_should_keep_both_mentions_when_one_line_names_the_same_call_twice() -> None:
    source = "def run(a, b):\n    return combine(prepare(a), prepare(b))\n"

    _, references = _graph(source)

    prepare_ids = {r.id for r in references if r.name == "prepare"}
    assert len(prepare_ids) == 2


def test_should_give_same_named_definitions_in_one_file_distinct_ids() -> None:
    source = (
        "class First:\n"
        "    def run(self):\n"
        "        pass\n"
        "\n"
        "class Second:\n"
        "    def run(self):\n"
        "        pass\n"
    )

    symbols, _ = _graph(source)

    run_ids = {s.id for s in symbols if s.name == "run"}
    assert len(run_ids) == 2


def test_should_return_nothing_when_language_has_no_reference_rules() -> None:
    source = "# Title\n\nBody.\n"
    tree = Parser(get_language("markdown")).parse(source.encode("utf-8"))
    parsed = ParsedFile(
        path="README.md", language="markdown", content=source, tree=tree
    )

    _, references = graph_file(
        parsed,
        extract_file(parsed, has_tags_scm=True),
        extract_references(parsed, has_tags_scm=True),
    )

    assert references == []


def test_should_register_grapher_logic_for_memo_invalidation() -> None:
    assert hasattr(graph_file, "_logic_fingerprint")
