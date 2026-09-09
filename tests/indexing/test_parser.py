"""Tests for tree-sitter parsing of selected source files."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import smritikosh.indexing.parser as parser
from smritikosh.models import SourceFile
from tests.indexing.conftest import FakeStrategy


@pytest.fixture(autouse=True)
def clear_language_cache() -> Iterator[None]:
    """Keep the process-local grammar cache isolated between tests."""
    parser._LANGUAGE_CACHE.clear()
    yield
    parser._LANGUAGE_CACHE.clear()


def _source(path: str, language: str, content: str) -> SourceFile:
    return SourceFile(
        path=path,
        language=language,
        content=content,
        has_tags_scm=True,
        strategy=FakeStrategy(),
    )


@pytest.mark.parametrize(
    ("language", "content", "root_type"),
    [
        ("python", "def run():\n    pass\n", "module"),
        ("java", "class Client {}\n", "program"),
        ("markdown", "# Introduction\n", "document"),
        ("toml", "[project]\n", "document"),
    ],
)
def test_should_build_a_tree_for_each_routed_language(
    language: str,
    content: str,
    root_type: str,
) -> None:
    source = _source(f"example.{language}", language, content)

    parsed = parser.parse_file(source)

    assert parsed.tree.root_node.type == root_type
    assert not parsed.tree.root_node.has_error


def test_should_carry_path_language_and_content_onto_the_parsed_file() -> None:
    source = _source("src/app.py", "python", "import os\n")

    parsed = parser.parse_file(source)

    assert parsed.path == "src/app.py"
    assert parsed.language == "python"
    assert parsed.content == "import os\n"


def test_should_reuse_the_grammar_when_language_is_already_cached() -> None:
    first = parser._get_language("python")

    second = parser._get_language("python")

    assert second is first
    assert list(parser._LANGUAGE_CACHE) == ["python"]


def test_should_return_a_tree_with_error_nodes_when_syntax_is_broken() -> None:
    source = _source("src/broken.py", "python", "def run(:\n")

    parsed = parser.parse_file(source)

    assert parsed.tree.root_node.has_error


def test_should_register_parser_logic_for_memo_invalidation() -> None:
    assert hasattr(parser.parse_file, "_logic_fingerprint")
