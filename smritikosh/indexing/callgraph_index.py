"""Call-graph index -- caller / callee edges."""

from smritikosh.models import CallEdge, SearchResult


class CallGraphIndex:
    """Graph index over caller/callee relationships."""

    def __init__(self, index_dir: str):
        self.index_dir = index_dir

    def build(self, edges: list[CallEdge]) -> None:
        """Build/update the call graph from extracted edges.

        TODO: pick a graph representation (adjacency lists, networkx, sqlite, etc).
        """
        raise NotImplementedError

    def callers_of(self, symbol: str) -> list[SearchResult]:
        """Return symbols that call the given symbol."""
        raise NotImplementedError

    def callees_of(self, symbol: str) -> list[SearchResult]:
        """Return symbols called by the given symbol."""
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError
