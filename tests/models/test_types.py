"""Tests for shared smritikosh model types."""

from dataclasses import fields, is_dataclass

from smritikosh.models import (
    Capture,
    Chunk,
    ParsedFile,
    SearchResult,
    SourceFile,
    Symbol,
)


class DummyStrategy:
    mode_name = "ast"


def test_should_define_pipeline_models_as_dataclasses() -> None:
    assert is_dataclass(Capture)
    assert is_dataclass(SourceFile)
    assert is_dataclass(Symbol)
    assert is_dataclass(ParsedFile)
    assert is_dataclass(Chunk)
    assert is_dataclass(SearchResult)


def test_should_derive_chunking_mode_from_strategy() -> None:
    source_file = SourceFile(
        path="app.py",
        language="python",
        content="def main(): pass",
        has_tags_scm=True,
        strategy=DummyStrategy(),
    )

    assert source_file.chunking_mode == "ast"


def test_should_not_store_chunking_mode_as_field() -> None:
    field_names = {field.name for field in fields(SourceFile)}

    assert "chunking_mode" not in field_names
