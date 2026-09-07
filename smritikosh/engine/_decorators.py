"""FunctionDecorator — implements @sm.memoized and @sm.tracked."""

from __future__ import annotations

import functools
import hashlib
import inspect
from collections.abc import Callable
from typing import Any

import smritikosh.engine._memo as _memo_module
from smritikosh.engine._context import _COMPONENT_PATH
from smritikosh.engine._fingerprint import (
    _compute_context_fingerprint,
    _compute_input_fingerprint,
    _compute_logic_fingerprint,
    _tracked_logic_fps,
)


class FunctionDecorator:
    """Implements ``@sm.memoized`` (memo=True) and ``@sm.tracked`` (memo=False).

    **Logic fingerprint** — ``sha256(inspect.getsource(fn))`` — is computed
    *once* at decoration time; only input + context fingerprints are recomputed
    at call time.

    Cache key (memoized only)::

        sha256(logic_fp | input_fp | context_fp)

    On a cache hit the entire function body is skipped and the stored result
    is returned immediately.

    ``@sm.tracked`` skips caching but registers the decorated function's logic
    fingerprint in :data:`~._fingerprint._tracked_logic_fps` so that editing
    its source automatically invalidates all downstream ``@sm.memoized`` caches.
    """

    def __init__(self, memo: bool) -> None:
        self._memo = memo

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        logic_fp = _compute_logic_fingerprint(fn)
        memo = self._memo

        if not memo:
            _tracked_logic_fps.add(logic_fp)

        if inspect.iscoroutinefunction(fn):
            return self._wrap_async(fn, logic_fp, memo)
        return self._wrap_sync(fn, logic_fp, memo)

    # -- internal --------------------------------------------------------------

    @staticmethod
    def _wrap_async(
        fn: Callable[..., Any], logic_fp: str, memo: bool
    ) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not memo:
                return await fn(*args, **kwargs)

            store = _memo_module._memo_store
            component_path = _COMPONENT_PATH.get() or fn.__qualname__
            cache_key = hashlib.sha256(
                f"{logic_fp}"
                f"|{_compute_input_fingerprint(*args, **kwargs)}"
                f"|{_compute_context_fingerprint()}".encode()
            ).hexdigest()

            if store is not None:
                hit, cached = store.get(component_path, cache_key)
                if hit:
                    return cached

            result = await fn(*args, **kwargs)

            if store is not None:
                store.set(component_path, cache_key, result)
            return result

        wrapper._logic_fingerprint = logic_fp  # type: ignore[attr-defined]
        return wrapper

    @staticmethod
    def _wrap_sync(
        fn: Callable[..., Any], logic_fp: str, memo: bool
    ) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not memo:
                return fn(*args, **kwargs)

            store = _memo_module._memo_store
            component_path = _COMPONENT_PATH.get() or fn.__qualname__
            cache_key = hashlib.sha256(
                f"{logic_fp}"
                f"|{_compute_input_fingerprint(*args, **kwargs)}"
                f"|{_compute_context_fingerprint()}".encode()
            ).hexdigest()

            if store is not None:
                hit, cached = store.get(component_path, cache_key)
                if hit:
                    return cached

            result = fn(*args, **kwargs)

            if store is not None:
                store.set(component_path, cache_key, result)
            return result

        wrapper._logic_fingerprint = logic_fp  # type: ignore[attr-defined]
        return wrapper
