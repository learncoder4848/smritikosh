"""IncrementalEngine — the sm singleton and component-path context manager."""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import Callable
from typing import Any

from smritikosh.engine._batch import AsyncWrapper
from smritikosh.engine._context import _COMPONENT_PATH
from smritikosh.engine._decorators import FunctionDecorator

# ---------------------------------------------------------------------------
# Component-path context manager
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager  # type: ignore[arg-type]
async def _component_context(path: str):  # type: ignore[return]
    """Set the component path for the duration of an async block."""
    token = _COMPONENT_PATH.set(path)
    try:
        yield
    finally:
        _COMPONENT_PATH.reset(token)


# ---------------------------------------------------------------------------
# IncrementalEngine
# ---------------------------------------------------------------------------


class IncrementalEngine:
    """The ``sm`` singleton — exposes all decorators and async pipeline helpers.

    Attributes
    ----------
    memoized:
        ``@sm.memoized`` — caches the function result in DuckDB; skips the
        function body on a cache hit.
    tracked:
        ``@sm.tracked`` — no caching, but registers the function's source hash
        so that editing it invalidates all downstream memoized caches.
    threaded:
        ``@sm.threaded`` — wraps a sync function in ``asyncio.to_thread()``.
    batched:
        ``@sm.batched(max_size=N)`` — groups per-item async calls into batches.
    """

    def __init__(self) -> None:
        self.memoized: FunctionDecorator = FunctionDecorator(memo=True)
        self.tracked: FunctionDecorator = FunctionDecorator(memo=False)
        self.threaded: Callable[..., Any] = AsyncWrapper.threaded
        self.batched: Callable[..., Any] = AsyncWrapper.batched

    # -- async helpers ---------------------------------------------------------

    async def gather(self, fn: Callable[..., Any], items: list[Any]) -> list[Any]:
        """Run ``fn`` concurrently over *items* within the **current** component path.

        No new memo boundary is introduced — all calls share the caller's
        existing component path.  Use for per-chunk work inside
        ``process_file``.

        Returns
        -------
        list[Any]
            Results in the same order as *items*.
        """
        return list(await asyncio.gather(*[fn(item) for item in items]))

    async def fan_out(
        self,
        fn: Callable[..., Any],
        items: list[Any],
        *,
        concurrency: int | None = None,
    ) -> None:
        """Run ``fn`` concurrently over *items*, each in its **own** component path.

        Component path is ``"{fn.__name__}/{item.path}"`` when *item* has a
        ``path`` attribute, otherwise ``"{fn.__name__}/{item}"``.

        This creates stable memo boundaries so that each file's cache entries
        are stored and invalidated independently.

        Parameters
        ----------
        concurrency:
            Maximum number of items processed at the same time.  ``None``
            (default) auto-selects ``min(os.cpu_count() or 4, 32)``, which
            scales naturally with the machine: 4 on a quad-core laptop, up
            to 32 on a large server.  Lower this on memory-constrained
            machines (e.g. ``concurrency=2`` for a ONNX model on Intel Mac).
        """
        # Cap at 4 by default: ONNX models can be several hundred MB each;
        # more than 4 concurrent _fire tasks risks OOM on typical dev machines.
        # Pass an explicit concurrency= value to go higher on large servers.
        limit = concurrency or min(os.cpu_count() or 2, 4)
        sem = asyncio.Semaphore(limit)

        async def _run_one(item: Any) -> Any:
            item_key: str = getattr(item, "path", str(item))
            async with sem:
                async with _component_context(f"{fn.__name__}/{item_key}"):
                    return await fn(item)

        await asyncio.gather(*[_run_one(item) for item in items])


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

sm = IncrementalEngine()
