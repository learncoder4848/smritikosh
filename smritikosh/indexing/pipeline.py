"""Indexing pipeline orchestrator — process_file, process_chunk, build_index."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from smritikosh.adapters.embedder.sentence_transformer import (
    SentenceTransformerEmbedder,
)
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
from smritikosh.indexing.chunker import _chunk
from smritikosh.indexing.discovery import iter_source_files
from smritikosh.indexing.extractor import _extract
from smritikosh.indexing.file_router import FileRouter, JsonExcludeFilter
from smritikosh.indexing.parser import parse_file
from smritikosh.indexing.strategies import (
    AstChunkingStrategy,
    RegexChunkingStrategy,
    SectionChunkingStrategy,
)
from smritikosh.models import Chunk, SourceFile
from smritikosh.ports.embedder import Embedder
from smritikosh.ports.storage import StorageAdapter
from smritikosh.ports.vector_store import VectorStore

__all__ = [
    "EMBEDDER",
    "STORAGE",
    "VECTOR_STORE",
    "build_index",
    "process_chunk",
    "process_file",
]

# ── ContextKeys ───────────────────────────────────────────────────────────────
# detect_change=True on EMBEDDER: swapping the model auto-invalidates all memos.

EMBEDDER: ContextKey[Embedder] = ContextKey("embedder", detect_change=True)
STORAGE: ContextKey[StorageAdapter] = ContextKey("storage")
VECTOR_STORE: ContextKey[VectorStore] = ContextKey("vector_store")


# ── CPU-bound parse stage ─────────────────────────────────────────────────────


@sm.threaded
def _parse(source: SourceFile) -> Any:
    """Wrap parse_file in asyncio.to_thread — tree-sitter releases the GIL."""
    return parse_file(source)


# ── Per-chunk embedding ───────────────────────────────────────────────────────


@sm.batched(max_size=32)
def _embed_one(texts: list[str]) -> list[list[float]]:
    """Batch-embed document texts through the active Embedder.

    Decorated with @sm.batched: external callers pass a **single** text string
    and receive a **single** vector.  The BatchGatherer collects concurrent
    single-item calls and fires them together once max_size (32) is reached
    or after the 1 ms collection window.

    Raise :class:`~smritikosh.engine.RetryWithSmallerBatch` inside this
    function to halve the current batch and retry (e.g. for API token limits).
    """
    embedder = use_context(EMBEDDER)
    return embedder.encode_documents(texts)


@sm.tracked
async def process_chunk(chunk: Chunk) -> None:
    """Embed and persist one chunk; skip when its vector is already current.

    Skipping is driven by content-addressed chunk IDs (sha256(text)[:16]):
    if the chunk ID already exists in the vector store the text has not
    changed, so the stored embedding is still valid.
    """
    vector_store = use_context(VECTOR_STORE)
    if vector_store.exists(chunk.id):
        return  # content_hash unchanged — reuse stored vector
    vector: list[float] = await _embed_one(chunk.text)
    vector_store.upsert(chunk.id, vector)


# ── Per-file processing ───────────────────────────────────────────────────────


@sm.memoized
async def process_file(source: SourceFile) -> None:
    """Parse → extract → chunk → embed one source file incrementally.

    Memoised by @sm.memoized: the function body is skipped entirely on a
    cache hit (file content and all downstream logic unchanged).  A cache miss
    triggers the full pipeline and writes the file hash only after success.
    """
    storage = use_context(STORAGE)
    vector_store = use_context(VECTOR_STORE)

    old_ids = storage.get_chunk_ids_for_file(source.path)

    parsed = await _parse(source)
    captures = _extract(parsed, source.has_tags_scm)
    chunks = _chunk(parsed, captures, source.strategy)
    new_ids = {c.id for c in chunks}

    # Orphan cleanup: remove chunks that no longer appear in the file.
    for stale_id in old_ids - new_ids:
        storage.delete_chunk_node(stale_id)
        vector_store.delete(stale_id)

    storage.upsert_file_node(source)
    storage.upsert_chunk_nodes(chunks)
    await sm.gather(process_chunk, chunks)

    # Write file hash AFTER all chunks succeed — a crash here forces a full
    # re-process on the next run, which is intentionally conservative.
    storage.set_file_hash(
        source.path,
        hashlib.sha256(source.content.encode()).hexdigest(),
    )


# ── Root orchestrator ─────────────────────────────────────────────────────────


@sm.tracked
async def _run_pipeline(repo_path: str) -> None:
    """Discover files, prune deleted ones, then fan out process_file.

    Deletion detection: paths recorded in file_hashes but absent from the
    current walk are removed from nodes, file_hashes, and memo_cache so the
    next run starts clean.
    """
    storage = use_context(STORAGE)
    router = _build_router()
    file_source = LocalFileSource(repo_path)
    files = list(iter_source_files(file_source, router))

    stored_paths = set(storage.get_all_file_paths())
    current_paths = {f.path for f in files}
    memo_store = get_memo_store()

    for deleted in stored_paths - current_paths:
        storage.delete_file(deleted)
        memo_store.delete_component("process_file", deleted)

    await sm.fan_out(process_file, files)


# ── Router factory ────────────────────────────────────────────────────────────


def _build_router() -> FileRouter:
    """Return a FileRouter pre-configured for all supported file types.

    Adding a new language is one register_extension() call here — no other
    module needs to change (Open/Closed Principle).
    """
    ast = AstChunkingStrategy()
    sections = SectionChunkingStrategy()
    toml = RegexChunkingStrategy(r"^\[+[^\]]+\]")

    router = FileRouter(json_exclude_filter=JsonExcludeFilter())
    router.register_extension(".py",   "python",     ast)
    router.register_extension(".ts",   "typescript", ast)
    router.register_extension(".tsx",  "typescript", ast)
    router.register_extension(".js",   "javascript", ast)
    router.register_extension(".jsx",  "javascript", ast)
    router.register_extension(".java", "java",       ast)
    router.register_extension(".kt",   "kotlin",     ast)
    router.register_extension(".kts",  "kotlin",     ast)
    router.register_extension(".md",   "markdown",   sections)
    router.register_extension(".mdx",  "markdown",   sections)
    router.register_extension(".toml", "toml",       toml, has_tags_scm=False)
    router.register_extension(".json", "json",       sections)
    return router


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
        Embedding backend.  Defaults to
        :class:`~smritikosh.adapters.embedder.sentence_transformer.SentenceTransformerEmbedder`
        (local, no API key, CPU/GPU).
    storage:
        Metadata storage adapter.  Defaults to
        :class:`~smritikosh.adapters.storage.duckdb.DuckDBAdapter` writing to
        ``smritikosh.duckdb`` in the current directory.
    vector_store:
        Vector storage adapter.  Defaults to
        :class:`~smritikosh.adapters.vector_store.duckdb.DuckDBVectorStore`,
        sharing the storage connection so all tables live in a single file.

    Notes
    -----
    * ``vector_store.setup(embedder.dims)`` is called before the pipeline runs.
      If the model has changed since the last run, the vectors table is dropped
      and all file hashes and memo entries are cleared, forcing a full re-embed.
    * ``initialize_memo_store(con)`` creates the ``memo_cache`` table in the
      same DuckDB file and must be called before ``asyncio.run()``.
    """
    embedder = embedder or SentenceTransformerEmbedder()
    storage = storage or DuckDBAdapter(DEFAULT_DB_PATH)

    # Share the DuckDB connection when using the default backends so all tables
    # (nodes, file_hashes, vectors, memo_cache) live in a single file.
    _con: Any = getattr(storage, "con", None)
    vector_store = vector_store or DuckDBVectorStore(DEFAULT_DB_PATH, con=_con)

    # dims from embedder drives the FLOAT[dims] column; a model change drops and
    # recreates the vectors table and invalidates all incremental caches.
    vector_store.setup(embedder.dims)

    # MemoizationStore needs an open connection before asyncio.run() because
    # the ContextVar system is set up synchronously here.
    initialize_memo_store(_con or storage.con)  # type: ignore[union-attr]

    ctx = PipelineContext()
    ctx.provide(EMBEDDER, embedder)
    ctx.provide(STORAGE, storage)
    ctx.provide(VECTOR_STORE, vector_store)

    with ctx:
        asyncio.run(_run_pipeline(repo_path))
