"""DuckDB call-graph store -- symbols in `nodes`, references and edges beside it."""

from __future__ import annotations

import json
from typing import Final

import duckdb

from smritikosh.constants import DEFAULT_DB_PATH
from smritikosh.indexing.grapher import name_tail
from smritikosh.models import Reference, Symbol
from smritikosh.ports.graph_store import GraphStore

__all__ = ["DuckDBGraphStore"]

#: Score given to a candidate defined in the same file as the mention. Anything
#: further away scores lower, so a caller can ask for certainty and get only
#: the matches nothing else could explain.
_SAME_FILE_CONFIDENCE: Final[float] = 1.0
_CROSS_FILE_CONFIDENCE: Final[float] = 0.6

_SCHEMA: Final[tuple[str, ...]] = (
    # References sit outside `nodes` because a reference is an edge, not a node:
    # it has no identity of its own, it outnumbers definitions several times
    # over, and `src_symbol` is joined on every traversal hop -- which wants a
    # real indexed column, not a field inside a JSON blob.
    """
    CREATE TABLE IF NOT EXISTS refs (
        id         TEXT PRIMARY KEY,
        src_symbol TEXT NOT NULL,
        name       TEXT NOT NULL,
        name_tail  TEXT NOT NULL,
        kind       TEXT NOT NULL,
        path       TEXT NOT NULL,
        line       INTEGER NOT NULL
    )
    """,
    # Derived from refs joined to symbols. Disposable: a bug here is repaired by
    # rebuilding, never by re-reading source.
    """
    CREATE TABLE IF NOT EXISTS edges (
        ref_id     TEXT NOT NULL,
        src        TEXT NOT NULL,
        dst        TEXT NOT NULL,
        kind       TEXT NOT NULL,
        line       INTEGER NOT NULL,
        confidence REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS refs_tail ON refs(name_tail)",
    "CREATE INDEX IF NOT EXISTS refs_src ON refs(src_symbol)",
    "CREATE INDEX IF NOT EXISTS refs_path ON refs(path)",
    "CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst)",
    "CREATE INDEX IF NOT EXISTS edges_src ON edges(src)",
)


class DuckDBGraphStore(GraphStore):
    """Stores the call graph in the same DuckDB file as chunks and vectors.

    Symbols are written into the existing ``nodes`` table under
    ``kind='symbol'``: they carry the same id/name/path/line shape a chunk
    does, which keeps ``delete_file`` and ``index_info`` working untouched and
    puts a symbol beside the chunk whose vector it borrows for ranking.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        *,
        con: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        self._con = con or duckdb.connect(db_path)
        self._owns_con = con is None

    def setup(self) -> None:
        for statement in _SCHEMA:
            self._con.execute(statement)

    # ---------------------------------------------------------------- symbols

    def upsert_symbols(self, symbols: list[Symbol]) -> None:
        if not symbols:
            return
        self._con.executemany(
            """
            INSERT OR REPLACE INTO nodes (id, kind, name, path, metadata)
            VALUES (?, 'symbol', ?, ?, ?)
            """,
            [
                (
                    symbol.id,
                    symbol.name,
                    symbol.path,
                    json.dumps(
                        {
                            "symbol_kind": symbol.kind,
                            "start_line": symbol.start_line,
                            "end_line": symbol.end_line,
                            "parent": symbol.parent,
                        }
                    ),
                )
                for symbol in symbols
            ],
        )

    def get_symbol_ids_for_file(self, path: str) -> set[str]:
        rows: list[tuple[str]] = self._con.execute(
            "SELECT id FROM nodes WHERE path = ? AND kind = 'symbol'", [path]
        ).fetchall()
        return {row[0] for row in rows}

    def delete_symbol(self, symbol_id: str) -> None:
        self._con.execute(
            "DELETE FROM nodes WHERE id = ? AND kind = 'symbol'", [symbol_id]
        )

    # ------------------------------------------------------------- references

    def replace_references(self, path: str, references: list[Reference]) -> None:
        self._con.execute("DELETE FROM refs WHERE path = ?", [path])
        if not references:
            return
        self._con.executemany(
            """
            INSERT OR REPLACE INTO refs
                (id, src_symbol, name, name_tail, kind, path, line)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    reference.id,
                    reference.src_symbol,
                    reference.name,
                    name_tail(reference.name),
                    reference.kind,
                    reference.path,
                    reference.line,
                )
                for reference in references
            ],
        )

    # ------------------------------------------------------------------ edges

    def rebuild_edges(self) -> None:
        """Resolve every reference, keeping each candidate as its own edge.

        The join is on ``name_tail`` because a definition writes its own bare
        name while a caller writes a qualified one -- ``def validate`` against
        ``billing.validate``. That match is deliberately loose, so the score
        below, not the join, is what separates a certain edge from a guess.
        """
        self._con.begin()
        try:
            self._con.execute("DELETE FROM edges")
            self._con.execute(
                f"""
                INSERT INTO edges (ref_id, src, dst, kind, line, confidence)
                SELECT r.id, r.src_symbol, s.id, r.kind, r.line,
                       CASE WHEN s.path = r.path
                            THEN {_SAME_FILE_CONFIDENCE}
                            ELSE {_CROSS_FILE_CONFIDENCE}
                       END
                FROM refs AS r
                JOIN nodes AS s
                  ON s.kind = 'symbol' AND s.name = r.name_tail
                """  # noqa: S608
            )
            self._con.commit()
        except Exception:
            self._con.rollback()
            raise

    def delete_file(self, path: str) -> None:
        """Drop one file's graph rows.

        Symbols are left to :meth:`StorageAdapter.delete_file`, which already
        clears every ``nodes`` row for the path in its own transaction.
        """
        self._con.execute("DELETE FROM refs WHERE path = ?", [path])

    def close(self) -> None:
        if self._owns_con:
            self._con.close()
