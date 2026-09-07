"""Lexical (BM25) index -- identifier + token matches."""

from smritikosh.models import Chunk, SearchResult


class LexicalIndex:
    """BM25-style lexical index over code chunks."""

    def __init__(self, index_dir: str):
        self.index_dir = index_dir

    def build(self, chunks: list[Chunk]) -> None:
        """Build/update the BM25 index from chunks.

        TODO: tokenize (identifiers, camelCase/snake_case splitting) and index.
        """
        raise NotImplementedError

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        """Return top-k lexical matches for the query.

        TODO: implement BM25 scoring/lookup.
        """
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError
