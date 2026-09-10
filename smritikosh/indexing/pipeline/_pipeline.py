"""Pipeline orchestration — ContextKeys, per-chunk/file processing, build_index."""

from __future__ import annotations

import asyncio
import hashlib

from smritikosh.adapters.embedder.fastembed import FastEmbedEmbedder
from smritikosh.adapters.file_source.local import LocalFileSource
from smritikosh.adapters.storage.duckdb import DuckDBAdapter
from smritikosh.adapters.vector_store.duckdb import DuckDBVectorStore
from smritikosh.constants import DEFAULT_DB_PATH
from smritikosh.engine import (
    ContextKey,
    PipelineContext,
    get_memo_store,
    initialize_memo_store,
    sm,
    use_context,
)
from smritikosh.indexing.discovery import iter_source_files
from smritikosh.indexing.pipeline._router import _build_router
from smritikosh.indexing.pipeline._stages import _chunk, _extract, _parse
from smritikosh.models import Chunk, SourceFile
from smritikosh.ports.embedder import Embedder
from smritikosh.ports.storage import StorageAdapter
from smritikosh.ports.vector_store import VectorStore

# ── ContextKeys ───────────────────────────────────────────────────────────────
# detect_change=True on EMBEDDER: swapping the model auto-invalidates all memos.

EMBEDDER: ContextKey[Embedder] = ContextKey("embedder", detect_change=True)
STORAGE: ContextKey[StorageAdapter] = ContextKey("storage")
VECTOR_STORE: ContextKey[VectorStore] = ContextKey("vector_store")


# ── Per-chunk embedding ───────────────────────────────────────────────────────


@sm.batched(max_size=32)
def _embed_one(texts: list[str]) -> list[list[float]]:
    """Batch single-item calls; raise RetryWithSmallerBatch on token errors."""
    embedder = use_context(EMBEDDER)
    return embedder.encode_documents(texts)


@sm.tracked
async def process_chunk(chunk: Chunk) -> None:
    """Embed and upsert one chunk; skip if content_hash is unchanged."""
    vector_store = use_context(VECTOR_STORE)
    if vector_store.exists(chunk.id):
        return
    vector: list[float] = await _embed_one(chunk.text)
    vector_store.upsert(chunk.id, vector)


# ── Per-file processing ───────────────────────────────────────────────────────


@sm.memoized
async def process_file(source: SourceFile) -> None:
    """Parse → extract → chunk → embed one source file incrementally."""
    storage      = use_context(STORAGE)
    vector_store = use_context(VECTOR_STORE)

    old_ids  = storage.get_chunk_ids_for_file(source.path)
    parsed   = await _parse(source)
    captures = await _extract(parsed, source.has_tags_scm)
    chunks   = await _chunk(parsed, captures, source.strategy)
    new_ids  = {c.id for c in chunks}

    for stale_id in old_ids - new_ids:
        storage.delete_chunk_node(stale_id)
        vector_store.delete(stale_id)

    storage.upsert_file_node(source)
    storage.upsert_chunk_nodes(chunks)
    await sm.gather(process_chunk, chunks)

    # Write file hash after success — a crash forces full re-process next run.
    storage.set_file_hash(
        source.path,
        hashlib.sha256(source.content.encode()).hexdigest(),
    )


# ── Root orchestrator ─────────────────────────────────────────────────────────


@sm.tracked
async def _run_pipeline(repo_path: str) -> None:
    """Discover files, clean up deleted ones, fan out process_file."""
    storage     = use_context(STORAGE)
    file_source = LocalFileSource(repo_path)
    files       = list(iter_source_files(file_source, _build_router()))

    stored_paths  = set(storage.get_all_file_paths())
    current_paths = {f.path for f in files}
    memo_store    = get_memo_store()

    for deleted in stored_paths - current_paths:
        storage.delete_file(deleted)
        memo_store.delete_component("process_file", deleted)

    await sm.fan_out(process_file, files)


# ── Public entry point ────────────────────────────────────────────────────────


def build_index(
    repo_path: str,
    embedder: Embedder | None = None,
    storage: StorageAdapter | None = None,
    vector_store: VectorStore | None = None,
) -> None:
    """Build or incrementally update the vector index for *repo_path*.

    Parameters
    ----------
    repo_path:
        Root directory of the repository to index.
    embedder:
        Defaults to FastEmbedEmbedder (local ONNX, no PyTorch, no API key).
    storage:
        Defaults to DuckDBAdapter writing to ``smritikosh.duckdb``.
    vector_store:
        Defaults to DuckDBVectorStore sharing the storage connection.
    """
    embedder = embedder or FastEmbedEmbedder()
    storage  = storage  or DuckDBAdapter(DEFAULT_DB_PATH)

    # Share DuckDB connection across vector store and memo cache when available.
    # Adapters without .con skip memoization and always re-evaluate the pipeline.
    _con         = getattr(storage, "con", None)
    vector_store = vector_store or DuckDBVectorStore(DEFAULT_DB_PATH, con=_con)

    vector_store.setup(embedder.dims)

    if _con is not None:
        initialize_memo_store(_con)

    ctx = PipelineContext()
    ctx.provide(EMBEDDER, embedder)
    ctx.provide(STORAGE, storage)
    ctx.provide(VECTOR_STORE, vector_store)

    with ctx:
        asyncio.run(_run_pipeline(repo_path))
