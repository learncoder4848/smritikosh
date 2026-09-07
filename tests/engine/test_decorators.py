"""Tests for @sm.memoized and @sm.tracked."""

import pytest

from smritikosh.engine import PipelineContext, sm
import smritikosh.engine._memo as _memo_module


# ---------------------------------------------------------------------------
# @sm.memoized — caching behaviour
# ---------------------------------------------------------------------------


async def test_memoized_caches_result(memo_store):
    calls = []

    @sm.memoized
    async def add(x: int, y: int) -> int:
        calls.append((x, y))
        return x + y

    with PipelineContext():
        r1 = await add(1, 2)
        r2 = await add(1, 2)  # should hit cache

    assert r1 == r2 == 3
    assert len(calls) == 1  # body executed only once


async def test_memoized_different_args_both_execute(memo_store):
    calls = []

    @sm.memoized
    async def square(n: int) -> int:
        calls.append(n)
        return n * n

    with PipelineContext():
        await square(2)
        await square(3)

    assert len(calls) == 2


async def test_memoized_without_store_still_runs():
    """When no memo store is set, @sm.memoized falls through to the function."""
    _memo_module._memo_store = None
    calls = []

    @sm.memoized
    async def fn() -> str:
        calls.append(1)
        return "ok"

    with PipelineContext():
        r1 = await fn()
        r2 = await fn()

    assert r1 == r2 == "ok"
    assert len(calls) == 2  # no cache → runs every time


async def test_memoized_sync_function(memo_store):
    calls = []

    @sm.memoized
    def multiply(a: int, b: int) -> int:
        calls.append(1)
        return a * b

    with PipelineContext():
        assert multiply(3, 4) == 12
        assert multiply(3, 4) == 12
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# @sm.tracked — no caching
# ---------------------------------------------------------------------------


async def test_tracked_always_executes():
    calls = []

    @sm.tracked
    async def parse(src: str) -> str:
        calls.append(src)
        return src.upper()

    assert await parse("hello") == "HELLO"
    assert await parse("hello") == "HELLO"
    assert len(calls) == 2  # no caching


async def test_tracked_sync_always_executes():
    calls = []

    @sm.tracked
    def extract(x: int) -> int:
        calls.append(x)
        return x + 1

    assert extract(5) == 6
    assert extract(5) == 6
    assert len(calls) == 2


def test_tracked_registers_logic_fingerprint():
    from smritikosh.engine._fingerprint import _tracked_logic_fps

    before = len(_tracked_logic_fps)

    @sm.tracked
    def new_tracked_fn() -> None:
        pass

    assert len(_tracked_logic_fps) > before


# ---------------------------------------------------------------------------
# Cache invalidation via detect_change context key
# ---------------------------------------------------------------------------


async def test_memoized_invalidated_by_detect_change_key(memo_store):
    from smritikosh.engine import ContextKey

    model_key = ContextKey("model", detect_change=True)
    calls = []

    @sm.memoized
    async def embed(text: str) -> str:
        calls.append(text)
        return text[::-1]

    with PipelineContext() as ctx:
        ctx.provide(model_key, "v1")
        await embed("hello")

    with PipelineContext() as ctx:
        ctx.provide(model_key, "v2")  # different model → different context_fp
        await embed("hello")

    assert len(calls) == 2  # both executed — different cache keys
