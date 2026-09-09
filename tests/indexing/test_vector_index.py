"""Tests for VectorIndex.search()."""

from __future__ import annotations

from typing import Any

import pytest

from smritikosh.indexing.vector_index import VectorIndex
from smritikosh.models import SearchResult

# ── Stubs ─────────────────────────────────────────────────────────────────────


class _Embedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class _VectorStore:
    def __init__(self, hits: list[tuple[str, float]] | None = None) -> None:
        self._hits = hits if hits is not None else [("c1", 0.9), ("c2", 0.7)]

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        return self._hits[:top_k]


class _Storage:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self._rows = rows if rows is not None else [
            {
                "id": "c1",
                "path": "src/foo.py",
                "start_line": 1,
                "end_line": 5,
                "text": "def foo(): pass",
                "chunk_kind": "function",
            },
            {
                "id": "c2",
                "path": "src/bar.py",
                "start_line": 10,
                "end_line": 12,
                "text": "def bar(): pass",
                "chunk_kind": "function",
            },
        ]

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[dict[str, Any]]:
        return [r for r in self._rows if r["id"] in chunk_ids]


def _index(
    hits: list[tuple[str, float]] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> VectorIndex:
    return VectorIndex(_VectorStore(hits), _Storage(rows), _Embedder())


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_raises_for_zero_top_k() -> None:
    with pytest.raises(ValueError, match="top_k"):
        await _index().search("query", top_k=0)


async def test_raises_for_negative_top_k() -> None:
    with pytest.raises(ValueError, match="top_k"):
        await _index().search("query", top_k=-1)


async def test_returns_empty_when_vector_store_has_no_hits() -> None:
    results = await _index(hits=[]).search("query")
    assert results == []


async def test_returns_empty_when_storage_returns_no_rows() -> None:
    results = await _index(rows=[]).search("query")
    assert results == []


async def test_results_sorted_by_score_descending() -> None:
    results = await _index().search("query", top_k=2)
    assert results[0].score > results[1].score
    assert results[0].score == pytest.approx(0.9)
    assert results[1].score == pytest.approx(0.7)


async def test_result_fields_are_populated_correctly() -> None:
    results = await _index().search("query", top_k=1)
    r = results[0]
    assert isinstance(r, SearchResult)
    assert r.path == "src/foo.py"
    assert r.snippet == "def foo(): pass"
    assert r.chunk_kind == "function"
    assert r.start_line == 1
    assert r.end_line == 5


async def test_top_k_limits_results() -> None:
    results = await _index().search("query", top_k=1)
    assert len(results) == 1


async def test_ignores_hit_whose_chunk_id_is_missing_from_storage() -> None:
    # Vector store returns c3 but storage only knows c1 and c2.
    hits = [("c1", 0.9), ("c3", 0.5)]
    results = await _index(hits=hits).search("query", top_k=2)
    assert len(results) == 1
    assert results[0].path == "src/foo.py"
