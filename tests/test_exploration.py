"""Tests for the read-only Smritikosh exploration API."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from smritikosh.exploration import ReadOnlyExplorer, SearchOptions


class _StubEmbedder:
    """Return deterministic vectors without loading an embedding model."""

    dims = 3

    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        vectors: dict[str, list[float]] = {
            "implementation": [1.0, 0.0, 0.0],
            "tests": [0.0, 1.0, 0.0],
        }
        return [vectors[text] for text in texts]


@pytest.fixture()
def indexed_db(tmp_path: Path) -> str:
    """Create a minimal on-disk index that can be reopened read-only."""
    db_path: Path = tmp_path / "index.duckdb"
    connection = duckdb.connect(str(db_path))
    connection.execute(
        """
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            path TEXT,
            metadata JSON
        );
        CREATE TABLE vectors (
            chunk_id TEXT PRIMARY KEY,
            vector FLOAT[3]
        );
        CREATE TABLE kv_store (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    rows: list[tuple[str, str, str, str]] = [
        ("file:src/billing.py", "file", "src/billing.py", "{}"),
        (
            "chunk:implementation",
            "chunk",
            "src/billing.py",
            json.dumps(
                {
                    "start_line": 10,
                    "end_line": 20,
                    "text": "def eligible_account():\n    return True",
                    "chunk_kind": "function",
                }
            ),
        ),
        (
            "chunk:test",
            "chunk",
            "tests/test_billing.py",
            json.dumps(
                {
                    "start_line": 30,
                    "end_line": 40,
                    "text": "def test_eligible_account():\n    assert True",
                    "chunk_kind": "function",
                }
            ),
        ),
    ]
    connection.executemany("INSERT INTO nodes VALUES (?, ?, ?, ?)", rows)
    connection.executemany(
        "INSERT INTO vectors VALUES (?, ?)",
        [
            ("chunk:implementation", [1.0, 0.0, 0.0]),
            ("chunk:test", [0.0, 1.0, 0.0]),
        ],
    )
    connection.execute("INSERT INTO kv_store VALUES ('embedder_dims', '3')")
    connection.close()
    return str(db_path)


def test_should_report_index_counts_when_index_exists(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act
    info = explorer.index_info()
    explorer.close()

    # Assert
    assert (info.files, info.chunks, info.vectors, info.dimensions) == (1, 2, 2, 3)


def test_should_merge_ad_hoc_queries_by_best_score(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act
    results = explorer.semantic_search(
        ["implementation", "tests"],
        embedder=_StubEmbedder(),
        options=SearchOptions(top_k=2),
    )
    explorer.close()

    # Assert
    assert {result.path for result in results} == {
        "src/billing.py",
        "tests/test_billing.py",
    }
    assert all(result.score == pytest.approx(1.0) for result in results)


def test_should_exclude_paths_when_semantically_searching(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act
    results = explorer.semantic_search(
        ["tests"],
        embedder=_StubEmbedder(),
        options=SearchOptions(top_k=2, exclude_paths=("tests/%",)),
    )
    explorer.close()

    # Assert
    assert [result.path for result in results] == ["src/billing.py"]


def test_should_find_paths_by_case_insensitive_substring(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act
    paths = explorer.find_paths("BILLING")
    explorer.close()

    # Assert
    assert paths == ["src/billing.py", "tests/test_billing.py"]


def test_should_find_exact_text_within_one_path(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act
    chunks = explorer.text_search("eligible_account", path="src/billing.py")
    explorer.close()

    # Assert
    assert [chunk.chunk_id for chunk in chunks] == ["chunk:implementation"]


def test_should_return_chunks_overlapping_requested_lines(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act
    chunks = explorer.get_chunks("src/billing.py", start_line=15, end_line=16)
    explorer.close()

    # Assert
    assert [chunk.chunk_id for chunk in chunks] == ["chunk:implementation"]


def test_should_reject_reversed_line_range(indexed_db: str) -> None:
    # Arrange
    explorer = ReadOnlyExplorer(indexed_db)

    # Act / Assert
    with pytest.raises(ValueError, match="cannot be greater"):
        explorer.get_chunks("src/billing.py", start_line=20, end_line=10)
    explorer.close()
