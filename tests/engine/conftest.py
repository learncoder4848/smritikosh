"""Shared fixtures for engine tests."""

import duckdb
import pytest

from smritikosh.engine import initialize_memo_store
from smritikosh.engine._memo import _memo_store as _store_ref
import smritikosh.engine._memo as _memo_module


@pytest.fixture
def mem_db():
    """In-memory DuckDB connection, torn down after each test."""
    con = duckdb.connect(":memory:")
    yield con
    con.close()


@pytest.fixture
def memo_store(mem_db):
    """Initialised MemoizationStore backed by an in-memory DuckDB."""
    initialize_memo_store(mem_db)
    yield _memo_module._memo_store
    # reset so tests don't bleed into each other
    _memo_module._memo_store = None
