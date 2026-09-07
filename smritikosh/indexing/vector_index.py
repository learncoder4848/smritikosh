"""Vector index -- semantic similarity search over embedded chunks."""

from smritikosh.models import Chunk, SearchResult


class VectorIndex:
    """Vector similarity index over embedded code chunks."""

    def __init__(self, index_dir: str):
        self.index_dir = index_dir

    def build(self, chunks: list[Chunk]) -> None:
        """Build/update the vector index.

        TODO: pick a backend (faiss, sqlite-vec, chroma, etc).
        """
        raise NotImplementedError

    def search(self, query_vector: list[float], top_k: int = 20) -> list[SearchResult]:
        """Return top-k nearest chunks by cosine/dot similarity.

        TODO: implement similarity search.
        """
        raise NotImplementedError

    def save(self) -> None:
        raise NotImplementedError

    def load(self) -> None:
        raise NotImplementedError
