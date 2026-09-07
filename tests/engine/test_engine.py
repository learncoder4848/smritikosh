"""Tests for IncrementalEngine — sm.gather and sm.fan_out."""

import asyncio

from smritikosh.engine import PipelineContext, sm
from smritikosh.engine._context import _COMPONENT_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeFile:
    def __init__(self, path: str) -> None:
        self.path = path


# ---------------------------------------------------------------------------
# sm.gather
# ---------------------------------------------------------------------------


async def test_gather_returns_results_in_order():
    @sm.tracked
    async def double(x: int) -> int:
        return x * 2

    with PipelineContext():
        results = await sm.gather(double, [1, 2, 3])

    assert results == [2, 4, 6]


async def test_gather_shares_component_path():
    """All sm.gather calls inherit the caller's component path."""
    paths: list[str] = []

    @sm.tracked
    async def record(_: int) -> None:
        paths.append(_COMPONENT_PATH.get())

    with PipelineContext():
        await sm.gather(record, [1, 2, 3])

    # All calls should share the same (empty default) path
    assert len(set(paths)) == 1


async def test_gather_runs_concurrently():
    order: list[int] = []

    @sm.tracked
    async def task(n: int) -> int:
        await asyncio.sleep(0.01)
        order.append(n)
        return n

    with PipelineContext():
        results = await sm.gather(task, [3, 1, 2])

    assert sorted(results) == [1, 2, 3]


# ---------------------------------------------------------------------------
# sm.fan_out
# ---------------------------------------------------------------------------


async def test_fan_out_sets_stable_component_paths():
    paths: list[str] = []

    @sm.memoized
    async def process(f: FakeFile) -> str:
        paths.append(_COMPONENT_PATH.get())
        return f.path

    files = [FakeFile("a.py"), FakeFile("b.py")]
    with PipelineContext():
        await sm.fan_out(process, files)

    assert set(paths) == {"process/a.py", "process/b.py"}


async def test_fan_out_path_uses_str_when_no_path_attr():
    paths: list[str] = []

    @sm.tracked
    async def record(item: str) -> None:
        paths.append(_COMPONENT_PATH.get())

    with PipelineContext():
        await sm.fan_out(record, ["foo", "bar"])

    assert set(paths) == {"record/foo", "record/bar"}


async def test_fan_out_all_items_processed():
    results: list[str] = []

    @sm.tracked
    async def collect(f: FakeFile) -> None:
        results.append(f.path)

    files = [FakeFile(p) for p in ["x.py", "y.py", "z.py"]]
    with PipelineContext():
        await sm.fan_out(collect, files)

    assert sorted(results) == ["x.py", "y.py", "z.py"]


async def test_fan_out_each_item_isolated_path(memo_store):
    """Each fan_out item gets its own memo boundary."""
    call_log: dict[str, int] = {}

    @sm.memoized
    async def process(f: FakeFile) -> str:
        call_log[f.path] = call_log.get(f.path, 0) + 1
        return f.path

    files = [FakeFile("a.py"), FakeFile("b.py")]

    with PipelineContext():
        await sm.fan_out(process, files)
        # Second run — both should hit cache (same input, same path)
        await sm.fan_out(process, files)

    assert call_log == {"a.py": 1, "b.py": 1}  # each file processed once
