"""smritikosh.indexing.pipeline — incremental indexing pipeline.

Public API
----------
All symbols below are importable directly from ``smritikosh.indexing.pipeline``::

    from smritikosh.indexing.pipeline import (
        build_index,
        process_file,
        process_chunk,
        EMBEDDER,
        STORAGE,
        VECTOR_STORE,
    )

Sub-modules (private, prefixed with ``_``) are an implementation detail:

    _stages.py    — @sm.threaded CPU stage wrappers (_parse, _extract, _chunk)
    _router.py    — @functools.cache file router factory (_build_router)
    _pipeline.py  — orchestration, ContextKeys, and build_index entry point
"""

from smritikosh.indexing.pipeline._pipeline import (
    EMBEDDER,
    STORAGE,
    VECTOR_STORE,
    build_index,
    process_chunk,
    process_file,
)

__all__ = [
    "EMBEDDER",
    "STORAGE",
    "VECTOR_STORE",
    "build_index",
    "process_chunk",
    "process_file",
]
