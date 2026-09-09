"""Stage 3: chunk orchestration — delegates to a ChunkingStrategy."""

from smritikosh.engine import sm
from smritikosh.models import Capture, Chunk, ChunkingStrategy, ParsedFile


@sm.tracked
def chunk_file(
    parsed: ParsedFile,
    captures: list[Capture],
    strategy: ChunkingStrategy,
) -> list[Chunk]:
    """Delegate chunking entirely to *strategy*."""
    return strategy.chunk(parsed, captures)
