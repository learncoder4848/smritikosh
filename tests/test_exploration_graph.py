"""Tests for read-only call-graph traversal over an indexed database."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from smritikosh.adapters.graph_store.duckdb import DuckDBGraphStore
from smritikosh.exploration import GraphDirection, ReadOnlyExplorer
from smritikosh.models import Reference, Symbol


def _symbol(name: str, path: str, start: int, end: int) -> Symbol:
    return Symbol(
        id=f"sym:{path}:{name}:{start}",
        name=name,
        kind="function",
        path=path,
        start_line=start,
        end_line=end,
        parent=None,
    )


def _reference(src: Symbol, name: str, line: int) -> Reference:
    return Reference(
        id=f"ref:{src.id}:{name}:{line}",
        src_symbol=src.id,
        name=name,
        kind="call",
        path=src.path,
        line=line,
    )


#: checkout -> charge -> validate, with charge also calling an unindexed `log`.
CHECKOUT = _symbol("checkout", "payments.py", 1, 3)
CHARGE = _symbol("charge", "payments.py", 5, 8)
VALIDATE = _symbol("validate", "billing.py", 1, 4)


@pytest.fixture
def explorer(tmp_path: Path) -> Iterator[ReadOnlyExplorer]:
    db_path = str(tmp_path / "index.duckdb")
    con = duckdb.connect(db_path)
    con.execute(
        """
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY, kind TEXT, name TEXT, path TEXT, metadata JSON
        )
        """
    )
    store = DuckDBGraphStore(con=con)
    store.setup()
    store.upsert_symbols([CHECKOUT, CHARGE, VALIDATE])
    store.replace_references(
        "payments.py",
        [
            _reference(CHECKOUT, "charge", 2),
            _reference(CHARGE, "billing.validate", 6),
            _reference(CHARGE, "log", 7),
        ],
    )
    store.rebuild_edges()
    con.close()

    with ReadOnlyExplorer(db_path) as read_only:
        yield read_only


def test_should_report_direct_callers_when_walking_inwards(
    explorer: ReadOnlyExplorer,
) -> None:
    entries = explorer.impact("validate", direction=GraphDirection.IN, depth=1)

    assert [(e.symbol, e.depth) for e in entries] == [("charge", 1)]


def test_should_follow_callers_transitively_to_the_requested_depth(
    explorer: ReadOnlyExplorer,
) -> None:
    entries = explorer.impact("validate", direction=GraphDirection.IN, depth=2)

    assert [(e.symbol, e.depth) for e in entries] == [("charge", 1), ("checkout", 2)]


def test_should_report_what_a_symbol_reaches_when_walking_outwards(
    explorer: ReadOnlyExplorer,
) -> None:
    entries = explorer.impact("checkout", direction=GraphDirection.OUT, depth=2)

    assert [(e.symbol, e.depth) for e in entries] == [("charge", 1), ("validate", 2)]


def test_should_carry_the_weakest_confidence_along_the_path(
    explorer: ReadOnlyExplorer,
) -> None:
    entries = explorer.impact("checkout", direction=GraphDirection.OUT, depth=2)

    same_file, cross_file = entries
    assert same_file.confidence == 1.0
    # checkout -> charge is same-file, charge -> validate crosses one, and the
    # pair is only as certain as its weakest hop.
    assert cross_file.confidence < 1.0


def test_should_exclude_hops_below_the_requested_confidence(
    explorer: ReadOnlyExplorer,
) -> None:
    entries = explorer.impact(
        "checkout",
        direction=GraphDirection.OUT,
        depth=2,
        min_confidence=1.0,
    )

    assert [e.symbol for e in entries] == ["charge"]


def test_should_return_nothing_when_a_symbol_has_no_neighbours(
    explorer: ReadOnlyExplorer,
) -> None:
    assert explorer.impact("checkout", direction=GraphDirection.IN, depth=2) == []


def test_should_report_a_mention_no_indexed_definition_satisfies(
    explorer: ReadOnlyExplorer,
) -> None:
    unresolved = explorer.unresolved_references()

    assert [(u.name, u.src_symbol, u.line) for u in unresolved] == [
        ("log", "charge", 7)
    ]


def test_should_restrict_unresolved_mentions_to_one_path(
    explorer: ReadOnlyExplorer,
) -> None:
    assert explorer.unresolved_references(path="billing.py") == []


@pytest.mark.parametrize(("depth", "limit"), [(0, 10), (-1, 10), (1, 0)])
def test_should_reject_a_non_positive_depth_or_limit(
    explorer: ReadOnlyExplorer,
    depth: int,
    limit: int,
) -> None:
    with pytest.raises(ValueError):
        explorer.impact("validate", depth=depth, limit=limit)


def test_should_ignore_symbol_rows_when_finding_paths(
    explorer: ReadOnlyExplorer,
) -> None:
    """`find_paths` answers from file nodes, not from every row carrying a path."""
    assert explorer.find_paths("payments") == []
