"""The call-graph contract -- implementations live in adapters/graph_store/.

The store holds two populations with different lifetimes, and the split is the
whole design:

``references``
    What a file says. Written per file, during indexing, carrying the name as
    written rather than a pointer to whatever it might mean. A reference
    survives the rename of its target, which is what lets the graph be rebuilt
    without re-reading the file that recorded it.

``edges``
    What those names meant. Derived by looking every reference up once all
    files are known, and rebuilt whole rather than invalidated — redoing the
    set costs less than one traversal query, so nothing tracks staleness.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from smritikosh.models import Reference, Symbol

__all__ = ["GraphStore"]


class GraphStore(ABC):
    """Stores symbols, the names they mention, and the resolved edges between."""

    @abstractmethod
    def setup(self) -> None:
        """Create the graph tables and indexes if they do not yet exist."""

    # ---------------------------------------------------------------- symbols

    @abstractmethod
    def upsert_symbols(self, symbols: list[Symbol]) -> None:
        """Insert or update the definitions found in one file."""

    @abstractmethod
    def get_symbol_ids_for_file(self, path: str) -> set[str]:
        """Return the ids of every symbol currently stored for *path*."""

    @abstractmethod
    def delete_symbol(self, symbol_id: str) -> None:
        """Remove one symbol, by id."""

    # ------------------------------------------------------------- references

    @abstractmethod
    def replace_references(self, path: str, references: list[Reference]) -> None:
        """Replace every reference recorded for *path*.

        The file is the unit that changed, so its whole set is rewritten rather
        than diffed -- a mention that moved by one line is the same mention.
        """

    # ------------------------------------------------------------------ edges

    @abstractmethod
    def rebuild_edges(self) -> None:
        """Resolve every reference into edges, replacing the previous set.

        Runs once, after all files are indexed: a name can only be looked up
        when every definition is known. Implementations must keep **every**
        candidate -- a name matching three symbols yields three edges, each
        with its own confidence -- so that an ambiguous call is reported rather
        than guessed.
        """

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """Remove every symbol and reference belonging to *path*."""
