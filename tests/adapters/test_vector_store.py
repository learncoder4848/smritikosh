"""Tests for the DuckDB vector store."""

from pathlib import Path

import duckdb
import pytest

from smritikosh.adapters.vector_store import DuckDBVectorStore


@pytest.fixture
def store() -> DuckDBVectorStore:
    return DuckDBVectorStore(con=duckdb.connect(":memory:"))


def test_should_store_dims_when_setup_runs() -> None:
    # Arrange
    store = DuckDBVectorStore(con=duckdb.connect(":memory:"))

    # Act
    store.setup(4)

    # Assert
    assert store.get_stored_dims() == 4


def test_should_reject_dims_when_not_positive(store: DuckDBVectorStore) -> None:
    # Act / Assert
    with pytest.raises(ValueError, match="dims must be positive"):
        store.setup(0)


def test_should_drop_stored_vectors_when_dims_change(
    store: DuckDBVectorStore,
) -> None:
    # Arrange
    store.setup(4)
    store.upsert("chunk-1", [0.1, 0.2, 0.3, 0.4])

    # Act
    store.setup(8)

    # Assert
    assert not store.exists("chunk-1")


def test_should_keep_stored_vectors_when_dims_unchanged(
    store: DuckDBVectorStore,
) -> None:
    # Arrange
    store.setup(4)
    store.upsert("chunk-1", [0.1, 0.2, 0.3, 0.4])

    # Act
    store.setup(4)

    # Assert
    assert store.exists("chunk-1")


def test_should_clear_incremental_caches_when_dims_change() -> None:
    # Arrange
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE file_hashes (path TEXT PRIMARY KEY, hash TEXT)")
    con.execute("INSERT INTO file_hashes VALUES ('app.py', 'abc123')")
    store = DuckDBVectorStore(con=con)
    store.setup(4)

    # Act
    store.setup(8)

    # Assert
    assert con.execute("SELECT count(*) FROM file_hashes").fetchone()[0] == 0


def test_should_report_true_when_chunk_upserted(store: DuckDBVectorStore) -> None:
    # Arrange
    store.setup(4)

    # Act
    store.upsert("chunk-1", [1.0, 0.0, 0.0, 0.0])

    # Assert
    assert store.exists("chunk-1")


def test_should_report_false_when_chunk_deleted(store: DuckDBVectorStore) -> None:
    # Arrange
    store.setup(4)
    store.upsert("chunk-1", [1.0, 0.0, 0.0, 0.0])

    # Act
    store.delete("chunk-1")

    # Assert
    assert not store.exists("chunk-1")


def test_should_replace_vector_when_chunk_upserted_twice(
    store: DuckDBVectorStore,
) -> None:
    # Arrange
    store.setup(4)
    store.upsert("chunk-1", [1.0, 0.0, 0.0, 0.0])

    # Act
    store.upsert("chunk-1", [0.0, 1.0, 0.0, 0.0])

    # Assert
    assert len(store.search([0.0, 1.0, 0.0, 0.0], top_k=10)) == 1


def test_should_rank_nearest_chunk_first_when_searching(
    store: DuckDBVectorStore,
) -> None:
    # Arrange
    store.setup(4)
    store.upsert("far", [0.0, 1.0, 0.0, 0.0])
    store.upsert("near", [1.0, 0.0, 0.0, 0.0])

    # Act
    hits = store.search([1.0, 0.0, 0.0, 0.0], top_k=2)

    # Assert
    assert [chunk_id for chunk_id, _ in hits] == ["near", "far"]


def test_should_limit_results_when_top_k_smaller_than_corpus(
    store: DuckDBVectorStore,
) -> None:
    # Arrange
    store.setup(4)
    for index in range(3):
        vector = [0.0, 0.0, 0.0, 0.0]
        vector[index] = 1.0
        store.upsert(f"chunk-{index}", vector)

    # Act
    hits = store.search([1.0, 0.0, 0.0, 0.0], top_k=2)

    # Assert
    assert len(hits) == 2


def test_should_return_empty_list_when_no_vectors_stored(
    store: DuckDBVectorStore,
) -> None:
    # Arrange
    store.setup(4)

    # Act
    hits = store.search([1.0, 0.0, 0.0, 0.0], top_k=10)

    # Assert
    assert hits == []


def test_should_raise_when_searching_before_setup(store: DuckDBVectorStore) -> None:
    # Act / Assert
    with pytest.raises(RuntimeError, match="setup"):
        store.search([1.0, 0.0, 0.0, 0.0], top_k=10)


def test_should_search_without_setup_when_database_reopened(tmp_path: Path) -> None:
    # Arrange
    db_path = str(tmp_path / "smritikosh.duckdb")
    first = DuckDBVectorStore(db_path)
    first.setup(4)
    first.upsert("chunk-1", [1.0, 0.0, 0.0, 0.0])
    first.close()

    # Act
    reopened = DuckDBVectorStore(db_path)
    hits = reopened.search([1.0, 0.0, 0.0, 0.0], top_k=10)

    # Assert
    assert [chunk_id for chunk_id, _ in hits] == ["chunk-1"]


def test_should_keep_connection_open_when_injected(store: DuckDBVectorStore) -> None:
    # Arrange
    store.setup(4)

    # Act
    store.close()

    # Assert
    assert store.get_stored_dims() == 4
