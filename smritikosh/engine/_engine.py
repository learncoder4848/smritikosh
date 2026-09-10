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
# ByteBudget — memory-aware concurrency gate
# ---------------------------------------------------------------------------


class ByteBudget:
    """Async semaphore that gates concurrency by **bytes**, not item count.

    Unlike a plain ``asyncio.Semaphore``, this allows variable-sized items:

    * **Small items** (size ≤ max_bytes): admitted as long as the running
      total stays within the budget.
    * **Large items** (size > max_bytes): wait until the budget is completely
      empty, then run alone — like a wide truck waiting for the road to clear.

    Parameters
    ----------
    max_bytes:
        Maximum total bytes that may be in-flight simultaneously.
    """

    def __init__(self, max_bytes: int) -> None:
        self._max = max_bytes
        self._used: int = 0
        self._cond: asyncio.Condition | None = None

    def _get_cond(self) -> asyncio.Condition:
        if self._cond is None:
            self._cond = asyncio.Condition()
        return self._cond

    async def acquire(self, size: int) -> None:
        """Block until *size* bytes can be admitted into the budget."""
        cond = self._get_cond()
        async with cond:
            # Large item → wait for a completely empty floor.
            # Small item → wait until there's room.
            await cond.wait_for(
                lambda: self._used == 0 or self._used + size <= self._max
            )
            self._used += size

    async def release(self, size: int) -> None:
        """Return *size* bytes to the budget and wake up any waiters."""
        cond = self._get_cond()
        async with cond:
            self._used -= size
            cond.notify_all()


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
        item_done: Callable[[Any], None] | None = None,
        max_inflight_bytes: int | None = None,
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
            (default) auto-selects ``min(os.cpu_count() or 2, 4)``.
            Lower this on memory-constrained machines.
        max_inflight_bytes:
            Optional byte-budget limit.  When set, both the row semaphore
            *and* the byte budget must have capacity before a new item starts.
            Items whose ``content`` attribute is larger than the budget wait
            for the budget to empty completely, then run alone.  Useful on
            machines where individual files vary wildly in size.
        item_done:
            Optional callback fired after each item completes (including
            cache hits).  Receives the raw item object.
        """
        # Cap at 4 by default: ONNX models can be several hundred MB each;
        # more than 4 concurrent _fire tasks risks OOM on typical dev machines.
        # Pass an explicit concurrency= value to go higher on large servers.
        limit = concurrency or min(os.cpu_count() or 2, 4)
        sem = asyncio.Semaphore(limit)
        budget = ByteBudget(max_inflight_bytes) if max_inflight_bytes else None

        async def _run_one(item: Any) -> Any:
            # Measure bytes of this item's source content (0 for non-files).
            content: str = getattr(item, "content", "") or ""
            item_bytes = len(content.encode("utf-8"))

            if budget is not None:
                await budget.acquire(item_bytes)
            try:
                item_key: str = getattr(item, "path", str(item))
                async with sem:
                    async with _component_context(f"{fn.__name__}/{item_key}"):
                        result = await fn(item)
                # Fire outside the semaphore — progress update is cheap and
                # shouldn't block the next item from starting.
                if item_done is not None:
                    item_done(item)
                return result
            finally:
                if budget is not None:
                    await budget.release(item_bytes)

        await asyncio.gather(*[_run_one(item) for item in items])


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

sm = IncrementalEngine()
