"""Tests for IncrementalEngine — sm.gather and sm.fan_out."""

import asyncio

from smritikosh.engine import PipelineContext, sm
from smritikosh.engine._context import _COMPONENT_PATH
from smritikosh.engine._engine import ByteBudget

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


async def test_fan_out_concurrency_limits_simultaneous_tasks():
    """At most *concurrency* items run at the same time."""
    peak = 0
    active = 0

    @sm.tracked
    async def task(f: FakeFile) -> None:
        nonlocal peak, active
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)   # yield so others can start
        active -= 1

    files = [FakeFile(f"{i}.py") for i in range(10)]
    with PipelineContext():
        await sm.fan_out(task, files, concurrency=3)

    assert peak <= 3


async def test_fan_out_concurrency_one_serialises_execution():
    """concurrency=1 means each item finishes before the next starts."""
    order: list[int] = []

    @sm.tracked
    async def task(f: FakeFile) -> None:
        idx = int(f.path.replace(".py", ""))
        await asyncio.sleep(0)      # yield to event loop
        order.append(idx)

    files = [FakeFile(f"{i}.py") for i in range(5)]
    with PipelineContext():
        await sm.fan_out(task, files, concurrency=1)

    # With concurrency=1 tasks are serialised — order must be sequential.
    assert order == list(range(5))


async def test_fan_out_default_concurrency_is_at_least_one():
    """Auto-detected concurrency must always be ≥ 1 (even on unusual hosts)."""
    results: list[str] = []

    @sm.tracked
    async def collect(f: FakeFile) -> None:
        results.append(f.path)

    files = [FakeFile("a.py"), FakeFile("b.py")]
    with PipelineContext():
        # No concurrency= arg — auto-detect must produce a valid semaphore.
        await sm.fan_out(collect, files)

    assert sorted(results) == ["a.py", "b.py"]


# ---------------------------------------------------------------------------
# ByteBudget
# ---------------------------------------------------------------------------


async def test_byte_budget_admits_small_items_in_parallel():
    """Items that fit within the budget run concurrently."""
    active = 0
    peak = 0

    async def work(size: int) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1

    budget = ByteBudget(max_bytes=100)
    # 3 items × 20 bytes each = 60 bytes total, well within 100-byte budget
    await asyncio.gather(
        *(asyncio.ensure_future(
            _acquire_work_release(budget, 20, work)
        ) for _ in range(3))
    )
    assert peak > 1  # ran concurrently


async def _acquire_work_release(budget: ByteBudget, size: int, fn) -> None:
    await budget.acquire(size)
    try:
        await fn(size)
    finally:
        await budget.release(size)


async def test_byte_budget_queues_when_full():
    """When the budget is exhausted, new items wait."""
    order: list[str] = []
    budget = ByteBudget(max_bytes=50)

    async def run(label: str, size: int) -> None:
        await budget.acquire(size)
        try:
            order.append(f"start:{label}")
            await asyncio.sleep(0.01)
            order.append(f"end:{label}")
        finally:
            await budget.release(size)

    # A (40B) starts immediately; B (40B) must wait for A to finish
    await asyncio.gather(run("A", 40), run("B", 40))

    assert order.index("end:A") < order.index("start:B")


async def test_byte_budget_large_item_waits_for_empty_floor():
    """An item larger than max_bytes waits until all others finish."""
    order: list[str] = []
    budget = ByteBudget(max_bytes=30)

    async def run(label: str, size: int) -> None:
        await budget.acquire(size)
        try:
            order.append(f"start:{label}")
            await asyncio.sleep(0.01)
            order.append(f"end:{label}")
        finally:
            await budget.release(size)

    # A (20B) + B (20B) fit in parallel; Giant (100B > 30B) must wait alone
    await asyncio.gather(run("A", 20), run("B", 20), run("Giant", 100))

    # Giant can only start after both A and B have finished
    giant_start = order.index("start:Giant")
    assert order.index("end:A") < giant_start
    assert order.index("end:B") < giant_start


async def test_fan_out_byte_budget_limits_inflight_content():
    """fan_out respects max_inflight_bytes via SourceFile.content size."""

    class FakeSource:
        def __init__(self, path: str, content: str) -> None:
            self.path = path
            self.content = content

    active = 0
    peak = 0

    @sm.tracked
    async def process(src: FakeSource) -> None:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1

    # 4 files × 10 bytes = 40 bytes; budget = 15 → at most 1 fits at a time
    files = [FakeSource(f"{i}.py", "x" * 10) for i in range(4)]
    with PipelineContext():
        await sm.fan_out(process, files, max_inflight_bytes=15)

    assert peak == 1   # budget forced serialisation
