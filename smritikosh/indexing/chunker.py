"""Stage 3: chunking + embedding -- code chunks -> vectors."""

from smritikosh.models import Chunk, EmbeddedChunk, ParsedFile, Symbol


def chunk_file(parsed: ParsedFile, symbols: list[Symbol]) -> list[Chunk]:
    """Split a parsed file into retrievable chunks (e.g. per symbol, or sliding window).

    TODO: decide chunk boundaries and overlap strategy.
    """
    raise NotImplementedError


def embed_chunks(chunks: list[Chunk]) -> list[EmbeddedChunk]:
    """Compute embedding vectors for a batch of chunks.

    TODO: call out to an embedding model/service.
    """
    raise NotImplementedError
