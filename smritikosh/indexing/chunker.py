"""Stage 3: chunking source files into retrievable chunks."""

from smritikosh.models import Chunk, ParsedFile, Symbol


def chunk_file(parsed: ParsedFile, symbols: list[Symbol]) -> list[Chunk]:
    """Split a parsed file into retrievable chunks (e.g. per symbol, or sliding window).

    TODO: decide chunk boundaries and overlap strategy.
    """
    raise NotImplementedError


def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """Compute embedding vectors for a batch of chunks.

    TODO: call out to an embedding model/service.
    """
    raise NotImplementedError
