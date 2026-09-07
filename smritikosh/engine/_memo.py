"""DuckDB-backed memoization store."""

from __future__ import annotations

import pickle
from typing import Any

# ---------------------------------------------------------------------------
# MemoizationStore
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS memo_cache (
        component_path  TEXT NOT NULL,
        cache_key       TEXT NOT NULL,
        result          BLOB,
        created_at      TIMESTAMP DEFAULT now(),
        PRIMARY KEY (component_path, cache_key)
    )
"""


class MemoizationStore:
    """DuckDB-backed memoization cache.

    Table schema::

        memo_cache (
            component_path  TEXT,   -- e.g. "process_file/src/foo.py"
            cache_key       TEXT,   -- sha256(logic_fp|input_fp|context_fp)
            result          BLOB,   -- pickle.dumps(return_value)
            created_at      TIMESTAMP
        )

    Parameters
    ----------
    con:
        An open ``duckdb.Connection``.  The caller owns the connection
        lifetime — this class does not close it.
    """

    def __init__(self, con: Any) -> None:
        self._con = con
        self._con.execute(_CREATE_TABLE_SQL)

    # -- public API ------------------------------------------------------------

    def get(self, component_path: str, cache_key: str) -> tuple[bool, Any]:
        """Return ``(True, result)`` on hit, ``(False, None)`` on miss."""
        row = self._con.execute(
            "SELECT result FROM memo_cache "
            "WHERE component_path = ? AND cache_key = ?",
            [component_path, cache_key],
        ).fetchone()
        if row is None:
            return False, None
        return True, pickle.loads(row[0])  # noqa: S301

    def set(self, component_path: str, cache_key: str, result: Any) -> None:
        """Insert or replace a cache entry."""
        self._con.execute(
            "INSERT OR REPLACE INTO memo_cache "
            "(component_path, cache_key, result) VALUES (?, ?, ?)",
            [component_path, cache_key, pickle.dumps(result, protocol=4)],
        )

    def delete_component(self, fn_name: str, item_key: str) -> None:
        """Delete all memo entries whose path begins with ``fn_name/item_key``.

        Parameters
        ----------
        fn_name:
            Decorated function name, e.g. ``"process_file"``.
        item_key:
            Typically the file path, e.g. ``"src/billing/invoices.py"``.
        """
        prefix = f"{fn_name}/{item_key}"
        self._con.execute(
            "DELETE FROM memo_cache WHERE component_path LIKE ?",
            [f"{prefix}%"],
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_memo_store: MemoizationStore | None = None


def initialize_memo_store(con: Any) -> None:
    """Initialise the module-level :class:`MemoizationStore`.

    Must be called inside ``build_index()`` **before** ``asyncio.run()``::

        con = duckdb.connect("smritikosh.duckdb")
        initialize_memo_store(con)
        asyncio.run(main())

    Parameters
    ----------
    con:
        An open ``duckdb.Connection``.
    """
    global _memo_store
    _memo_store = MemoizationStore(con)


def get_memo_store() -> MemoizationStore:
    """Return the active :class:`MemoizationStore`.

    Raises
    ------
    RuntimeError
        If :func:`initialize_memo_store` has not been called yet.
    """
    if _memo_store is None:
        raise RuntimeError(
            "MemoizationStore not initialised. "
            "Call initialize_memo_store(con) before asyncio.run()."
        )
    return _memo_store
