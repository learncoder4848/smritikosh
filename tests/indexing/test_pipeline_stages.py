"""Tests for the @sm.threaded CPU-stage wrappers (_parse, _extract, _chunk)."""

from __future__ import annotations

import asyncio

from smritikosh.indexing.pipeline._stages import _chunk, _extract, _parse
from smritikosh.indexing.strategies.section import SectionChunkingStrategy
from smritikosh.models import Capture, Chunk, ParsedFile, SourceFile

# ── Helpers ───────────────────────────────────────────────────────────────────


def _source(content: str = "x = 1\n") -> SourceFile:
    return SourceFile(
        path="test.py",
        language="python",
        content=content,
        has_tags_scm=True,
        strategy=SectionChunkingStrategy(),
    )


def _parsed(content: str = "x = 1\n") -> ParsedFile:
    return ParsedFile(path="test.py", language="python", content=content, tree=None)


# ── @sm.threaded decoration ───────────────────────────────────────────────────


def test_parse_is_a_coroutine_function() -> None:
    assert asyncio.iscoroutinefunction(_parse)


def test_extract_is_a_coroutine_function() -> None:
    assert asyncio.iscoroutinefunction(_extract)


def test_chunk_is_a_coroutine_function() -> None:
    assert asyncio.iscoroutinefunction(_chunk)


# ── _parse ────────────────────────────────────────────────────────────────────


async def test_parse_returns_parsed_file() -> None:
    result = await _parse(_source())
    assert isinstance(result, ParsedFile)
    assert result.path == "test.py"
    assert result.language == "python"
    assert result.content == "x = 1\n"


# ── _extract ──────────────────────────────────────────────────────────────────


async def test_extract_returns_empty_when_has_tags_scm_is_false() -> None:
    result = await _extract(_parsed(), has_tags_scm=False)
    assert result == []


async def test_extract_returns_list_of_captures() -> None:
    real_parsed = await _parse(_source("def foo(): pass\n"))
    result = await _extract(real_parsed, has_tags_scm=True)
    assert isinstance(result, list)
    assert all(isinstance(c, Capture) for c in result)


# ── _chunk ────────────────────────────────────────────────────────────────────


async def test_chunk_returns_list_of_chunks() -> None:
    strategy = SectionChunkingStrategy()
    result = await _chunk(_parsed("# Heading\nBody.\n"), [], strategy)
    assert isinstance(result, list)
    assert all(isinstance(c, Chunk) for c in result)


async def test_chunk_whole_file_fallback_when_no_captures() -> None:
    strategy = SectionChunkingStrategy()
    content = "plain text\n"
    result = await _chunk(_parsed(content), [], strategy)
    assert len(result) == 1
    assert result[0].text == content
