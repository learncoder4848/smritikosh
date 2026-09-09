"""Tests for ContextKeys, process_chunk, process_file, and build_index."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import duckdb

from smritikosh.adapters.storage.duckdb import DuckDBAdapter
from smritikosh.adapters.vector_store.duckdb import DuckDBVectorStore
from smritikosh.engine import PipelineContext
from smritikosh.indexing.pipeline._pipeline import (
    EMBEDDER,
    STORAGE,
    VECTOR_STORE,
    build_index,
    process_chunk,
    process_file,
)
from smritikosh.models import Chunk, SourceFile
from smritikosh.ports.embedder import Embedder

# ── Stubs ─────────────────────────────────────────────────────────────────────


class _Embedder(Embedder):
    """Fixed 4-dim embedder — no model loading."""

    dims = 4
    model_id = "stub:4"

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class _VectorStore:
    def __init__(self) -> None:
        self._store: dict[str, list[float]] = {}

    def setup(self, dims: int) -> None: ...  # noqa: D401
    def exists(self, chunk_id: str) -> bool:
        return chunk_id in self._store
    def upsert(self, chunk_id: str, vector: list[float]) -> None:
        self._store[chunk_id] = vector
    def delete(self, chunk_id: str) -> None:
        self._store.pop(chunk_id, None)


class _Storage:
    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._files: dict[str, str] = {}

    def get_chunk_ids_for_file(self, path: str) -> set[str]:
        return {c.id for c in self._chunks.values() if c.path == path}

    def upsert_file_node(self, source: SourceFile) -> None: ...
    def upsert_chunk_nodes(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._chunks[c.id] = c
    def delete_chunk_node(self, chunk_id: str) -> None:
        self._chunks.pop(chunk_id, None)
    def get_all_file_paths(self) -> set[str]:
        return set(self._files.keys())
    def get_file_hash(self, path: str) -> str | None:
        return self._files.get(path)
    def set_file_hash(self, path: str, hash: str) -> None:  # noqa: A002
        self._files[path] = hash
    def delete_file(self, path: str) -> None:
        self._files.pop(path, None)
    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[dict[str, Any]]:
        return []


def _make_chunk(text: str = "def foo(): pass", path: str = "a.py") -> Chunk:
    h = hashlib.sha256(text.encode()).hexdigest()
    return Chunk(
        id=h[:16], path=path, start_line=1, end_line=1,
        text=text, chunk_kind="function", content_hash=h,
    )


def _make_source(
    content: str = "def foo(): pass\n",
    path: str = "a.py",
) -> SourceFile:
    from smritikosh.indexing.strategies.section import SectionChunkingStrategy
    return SourceFile(
        path=path, language="python", content=content,
        has_tags_scm=False, strategy=SectionChunkingStrategy(),
    )


# ── ContextKeys ───────────────────────────────────────────────────────────────


def test_embedder_key_has_detect_change() -> None:
    assert EMBEDDER.name == "embedder"
    assert EMBEDDER.detect_change is True


def test_storage_key_has_no_detect_change() -> None:
    assert STORAGE.name == "storage"
    assert STORAGE.detect_change is False


def test_vector_store_key_has_no_detect_change() -> None:
    assert VECTOR_STORE.name == "vector_store"
    assert VECTOR_STORE.detect_change is False


# ── process_chunk ─────────────────────────────────────────────────────────────


async def test_process_chunk_skips_when_vector_already_exists() -> None:
    vs = _VectorStore()
    chunk = _make_chunk()
    vs.upsert(chunk.id, [0.1, 0.2, 0.3, 0.4])  # pre-populate

    ctx = PipelineContext()
    ctx.provide(VECTOR_STORE, vs)
    ctx.provide(EMBEDDER, _Embedder())
    with ctx:
        await process_chunk(chunk)

    assert list(vs._store.values()) == [[0.1, 0.2, 0.3, 0.4]]  # unchanged


async def test_process_chunk_embeds_and_upserts_new_chunk() -> None:
    vs = _VectorStore()
    chunk = _make_chunk()

    ctx = PipelineContext()
    ctx.provide(VECTOR_STORE, vs)
    ctx.provide(EMBEDDER, _Embedder())
    with ctx:
        await process_chunk(chunk)

    assert chunk.id in vs._store
    assert len(vs._store[chunk.id]) == 4


# ── process_file ──────────────────────────────────────────────────────────────


async def test_process_file_writes_file_hash_after_success() -> None:
    storage = _Storage()
    vs = _VectorStore()
    source = _make_source()

    ctx = PipelineContext()
    ctx.provide(STORAGE, storage)
    ctx.provide(VECTOR_STORE, vs)
    ctx.provide(EMBEDDER, _Embedder())
    with ctx:
        await process_file(source)

    expected_hash = hashlib.sha256(source.content.encode()).hexdigest()
    assert storage.get_file_hash(source.path) == expected_hash


async def test_process_file_removes_stale_chunks() -> None:
    storage = _Storage()
    vs = _VectorStore()
    source = _make_source()

    # Pre-populate a stale chunk that will no longer appear after processing.
    stale = _make_chunk("stale", path=source.path)
    storage._chunks[stale.id] = stale
    vs.upsert(stale.id, [0.0, 0.0, 0.0, 0.0])

    ctx = PipelineContext()
    ctx.provide(STORAGE, storage)
    ctx.provide(VECTOR_STORE, vs)
    ctx.provide(EMBEDDER, _Embedder())
    with ctx:
        await process_file(source)

    assert stale.id not in storage._chunks
    assert stale.id not in vs._store


# ── build_index ───────────────────────────────────────────────────────────────


def test_build_index_runs_end_to_end(tmp_path: Path) -> None:
    """Smoke test: build_index over a one-file repo without errors."""
    (tmp_path / "hello.py").write_text("def hello(): pass\n")

    con = duckdb.connect(":memory:")
    storage = DuckDBAdapter(con=con)
    vs = DuckDBVectorStore(con=con)

    build_index(
        str(tmp_path),
        embedder=_Embedder(),
        storage=storage,
        vector_store=vs,
    )

    paths = storage.get_all_file_paths()
    assert "hello.py" in paths


def test_build_index_second_run_is_idempotent(tmp_path: Path) -> None:
    """Second run on unchanged repo: file_hash hit, no new rows written."""
    (tmp_path / "hello.py").write_text("def hello(): pass\n")

    con = duckdb.connect(":memory:")
    storage = DuckDBAdapter(con=con)
    vs = DuckDBVectorStore(con=con)

    build_index(str(tmp_path), embedder=_Embedder(), storage=storage, vector_store=vs)
    chunk_ids_after_first = storage.get_chunk_ids_for_file("hello.py")

    build_index(str(tmp_path), embedder=_Embedder(), storage=storage, vector_store=vs)
    chunk_ids_after_second = storage.get_chunk_ids_for_file("hello.py")

    assert chunk_ids_after_first == chunk_ids_after_second
