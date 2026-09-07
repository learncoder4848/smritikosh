"""smritikosh.engine — incremental, memoized pipeline in plain Python.

Public API
----------
All symbols below are importable directly from ``smritikosh.engine``::

    from smritikosh.engine import (
        sm,
        PipelineContext,
        ContextKey,
        use_context,
        initialize_memo_store,
        get_memo_store,
        MemoizationStore,
        RetryWithSmallerBatch,
    )

Sub-modules (private, prefixed with ``_``) are an implementation detail and
should not be imported directly.
"""

from smritikosh.engine._batch import AsyncWrapper, BatchGatherer, RetryWithSmallerBatch
from smritikosh.engine._context import (
    ContextKey,
    PipelineContext,
    _ACTIVE_CONTEXT,
    _COMPONENT_PATH,
    use_context,
)
from smritikosh.engine._decorators import FunctionDecorator
from smritikosh.engine._engine import IncrementalEngine, _component_context, sm
from smritikosh.engine._fingerprint import (
    _compute_context_fingerprint,
    _compute_input_fingerprint,
    _compute_logic_fingerprint,
    _hash_bytes,
    _tracked_logic_fps,
)
from smritikosh.engine._memo import (
    MemoizationStore,
    _memo_store,
    get_memo_store,
    initialize_memo_store,
)

__all__ = [
    # Core
    "sm",
    "IncrementalEngine",
    # Context
    "ContextKey",
    "PipelineContext",
    "use_context",
    # Memoization
    "MemoizationStore",
    "initialize_memo_store",
    "get_memo_store",
    # Batching
    "RetryWithSmallerBatch",
    "BatchGatherer",
    "AsyncWrapper",
    # Decorators
    "FunctionDecorator",
]
