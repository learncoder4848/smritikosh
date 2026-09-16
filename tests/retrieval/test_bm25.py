"""Tests for the incremental DuckDB BM25 adapter."""

from __future__ import annotations

import hashlib

import duckdb
import pytest

from smritikosh.adapters.retrieval.duckdb import DuckDBBm25Store
from smritikosh.models import Chunk, SearchOptions


def _chunk(chunk_id: str, path: str, text: str, symbol: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        path=path,
        start_line=1,
        end_line=1,
        text=text,
        chunk_kind="function",
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        symbol=symbol,
    )


def test_should_rank_rare_identifier_above_common_report_terms() -> None:
    connection = duckdb.connect(":memory:")
    store = DuckDBBm25Store(con=connection)
    store.setup()
    store.upsert(
        [
            _chunk("common", "src/report.py", "publish report report", "publish"),
            _chunk(
                "specific",
                "src/idempotency.py",
                "skip duplicate completed event",
                "idempotent_handler",
            ),
        ]
    )

    hits = store.search(
        "duplicate report idempotency",
        options=SearchOptions(top_k=2),
    )

    assert [chunk_id for chunk_id, _ in hits] == ["specific", "common"]


def test_should_replace_and_delete_lexical_documents_incrementally() -> None:
    connection = duckdb.connect(":memory:")
    store = DuckDBBm25Store(con=connection)
    store.setup()
    initial = _chunk("one", "src/a.py", "before", "load")
    store.upsert([initial, initial])
    store.upsert([_chunk("one", "src/a.py", "after", "load")])

    before = store.search("before", options=SearchOptions(top_k=5))
    after = store.search("after", options=SearchOptions(top_k=5))
    store.delete("one")
    deleted = store.search("after", options=SearchOptions(top_k=5))

    assert before == []
    assert [chunk_id for chunk_id, _ in after] == ["one"]
    assert deleted == []


def test_should_apply_path_filters_to_bm25_results() -> None:
    connection = duckdb.connect(":memory:")
    store = DuckDBBm25Store(con=connection)
    store.setup()
    store.upsert(
        [
            _chunk("source", "src/a.py", "retry event", "retry"),
            _chunk("test", "tests/test_a.py", "retry event", "test_retry"),
        ]
    )

    hits = store.search(
        "retry",
        options=SearchOptions(top_k=5, exclude_paths=("tests/%",)),
    )

    assert [chunk_id for chunk_id, _ in hits] == ["source"]


def test_should_explain_how_to_rebuild_when_bm25_index_is_missing() -> None:
    store = DuckDBBm25Store(con=duckdb.connect(":memory:"))

    with pytest.raises(RuntimeError, match="index --full"):
        store.search("anything", options=SearchOptions(top_k=5))
