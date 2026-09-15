"""Tests for the DuckDB call-graph store."""

from __future__ import annotations

import json

import duckdb
import pytest

from smritikosh.adapters.graph_store.duckdb import DuckDBGraphStore
from smritikosh.models import Reference, Symbol


@pytest.fixture
def store() -> DuckDBGraphStore:
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY, kind TEXT, name TEXT, path TEXT, metadata JSON
        )
        """
    )
    graph_store = DuckDBGraphStore(con=con)
    graph_store.setup()
    return graph_store


def _symbol(name: str, path: str, start: int = 1, end: int = 3) -> Symbol:
    return Symbol(
        id=f"sym:{path}:{name}:{start}",
        name=name,
        kind="function",
        path=path,
        start_line=start,
        end_line=end,
        parent=None,
    )


def _reference(src: Symbol, name: str, line: int = 2) -> Reference:
    return Reference(
        id=f"ref:{src.id}:{name}:{line}",
        src_symbol=src.id,
        name=name,
        kind="call",
        path=src.path,
        line=line,
    )


def test_should_store_symbols_as_nodes_so_existing_queries_still_reach_them(
    store: DuckDBGraphStore,
) -> None:
    symbol = _symbol("charge", "payments.py")

    store.upsert_symbols([symbol])

    row = store._con.execute(
        "SELECT kind, name, path, metadata FROM nodes WHERE id = ?", [symbol.id]
    ).fetchone()
    assert row[:3] == ("symbol", "charge", "payments.py")
    assert json.loads(row[3])["start_line"] == 1


def test_should_resolve_a_qualified_reference_by_its_last_segment(
    store: DuckDBGraphStore,
) -> None:
    caller = _symbol("charge", "payments.py")
    callee = _symbol("validate", "billing.py")
    store.upsert_symbols([caller, callee])
    store.replace_references("payments.py", [_reference(caller, "billing.validate")])

    store.rebuild_edges()

    assert store._con.execute("SELECT src, dst FROM edges").fetchall() == [
        (caller.id, callee.id)
    ]


def test_should_keep_every_candidate_when_a_name_is_ambiguous(
    store: DuckDBGraphStore,
) -> None:
    caller = _symbol("charge", "payments.py")
    store.upsert_symbols(
        [caller, _symbol("validate", "billing.py"), _symbol("validate", "tax.py")]
    )
    store.replace_references("payments.py", [_reference(caller, "validate")])

    store.rebuild_edges()

    targets = store._con.execute("SELECT dst FROM edges ORDER BY dst").fetchall()
    assert len(targets) == 2


def test_should_score_a_same_file_candidate_above_a_cross_file_one(
    store: DuckDBGraphStore,
) -> None:
    caller = _symbol("charge", "payments.py", start=10, end=12)
    store.upsert_symbols(
        [caller, _symbol("validate", "payments.py"), _symbol("validate", "tax.py")]
    )
    store.replace_references("payments.py", [_reference(caller, "validate", line=11)])

    store.rebuild_edges()

    scores = dict(
        store._con.execute(
            """
            SELECT n.path, e.confidence
            FROM edges AS e JOIN nodes AS n ON n.id = e.dst
            """
        ).fetchall()
    )
    assert scores["payments.py"] > scores["tax.py"]


def test_should_leave_no_edge_when_nothing_defines_the_mentioned_name(
    store: DuckDBGraphStore,
) -> None:
    caller = _symbol("charge", "payments.py")
    store.upsert_symbols([caller])
    store.replace_references("payments.py", [_reference(caller, "log")])

    store.rebuild_edges()

    assert store._con.execute("SELECT count(*) FROM edges").fetchone()[0] == 0
    assert store._con.execute("SELECT count(*) FROM refs").fetchone()[0] == 1


def test_should_rebuild_edges_from_references_after_a_rename(
    store: DuckDBGraphStore,
) -> None:
    caller = _symbol("charge", "payments.py")
    callee = _symbol("validate", "billing.py")
    store.upsert_symbols([caller, callee])
    store.replace_references("payments.py", [_reference(caller, "billing.validate")])
    store.rebuild_edges()

    # billing.py is re-indexed under a new name; payments.py is untouched, so
    # its reference — the text it wrote — is never rewritten.
    store.delete_symbol(callee.id)
    store.upsert_symbols([_symbol("validate_payment", "billing.py")])
    store.rebuild_edges()

    assert store._con.execute("SELECT count(*) FROM edges").fetchone()[0] == 0
    assert store._con.execute("SELECT name FROM refs").fetchone() == (
        "billing.validate",
    )


def test_should_replace_a_files_references_rather_than_accumulate_them(
    store: DuckDBGraphStore,
) -> None:
    caller = _symbol("charge", "payments.py")
    store.upsert_symbols([caller])
    store.replace_references("payments.py", [_reference(caller, "first")])

    store.replace_references("payments.py", [_reference(caller, "second")])

    assert store._con.execute("SELECT name FROM refs").fetchall() == [("second",)]


def test_should_drop_a_deleted_files_references(store: DuckDBGraphStore) -> None:
    caller = _symbol("charge", "payments.py")
    store.upsert_symbols([caller])
    store.replace_references("payments.py", [_reference(caller, "validate")])

    store.delete_file("payments.py")

    assert store._con.execute("SELECT count(*) FROM refs").fetchone()[0] == 0
