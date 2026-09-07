"""Hybrid retrieval: fuse, rerank, dedup results from lexical + call-graph + vector indexes."""

from smritikosh.indexing.callgraph_index import CallGraphIndex
from smritikosh.indexing.lexical_index import LexicalIndex
from smritikosh.indexing.vector_index import VectorIndex
from smritikosh.models import SearchResult


class HybridRetriever:
    """Fuses results across the three indexes for a single agent query."""

    def __init__(
        self,
        lexical_index: LexicalIndex,
        callgraph_index: CallGraphIndex,
        vector_index: VectorIndex,
    ):
        self.lexical_index = lexical_index
        self.callgraph_index = callgraph_index
        self.vector_index = vector_index

    def retrieve(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Run the query against all applicable indexes, fuse, rerank, and dedup.

        TODO:
          1. lexical_index.search(query)
          2. vector_index.search(embed(query))
          3. optionally expand via callgraph_index (callers/callees of top hits)
          4. fuse scores (e.g. reciprocal rank fusion), dedup by (path, line range)
          5. rerank, truncate to top_k
        """
        raise NotImplementedError
