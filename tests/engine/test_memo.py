"""Tests for MemoizationStore, initialize_memo_store, get_memo_store."""

import pytest

import smritikosh.engine._memo as _memo_module
from smritikosh.engine import MemoizationStore, get_memo_store

# ---------------------------------------------------------------------------
# MemoizationStore.get / set
# ---------------------------------------------------------------------------


def test_get_miss(memo_store):
    hit, val = memo_store.get("proc/a.py", "key1")
    assert hit is False
    assert val is None


def test_set_then_get_hit(memo_store):
    memo_store.set("proc/a.py", "key1", {"chunks": 3})
    hit, val = memo_store.get("proc/a.py", "key1")
    assert hit is True
    assert val == {"chunks": 3}


def test_set_overwrites(memo_store):
    memo_store.set("proc/a.py", "key1", "old")
    memo_store.set("proc/a.py", "key1", "new")
    _, val = memo_store.get("proc/a.py", "key1")
    assert val == "new"


def test_different_paths_independent(memo_store):
    memo_store.set("proc/a.py", "key1", "A")
    memo_store.set("proc/b.py", "key1", "B")
    _, val_a = memo_store.get("proc/a.py", "key1")
    _, val_b = memo_store.get("proc/b.py", "key1")
    assert val_a == "A"
    assert val_b == "B"


def test_different_keys_independent(memo_store):
    memo_store.set("proc/a.py", "key1", 1)
    memo_store.set("proc/a.py", "key2", 2)
    _, v1 = memo_store.get("proc/a.py", "key1")
    _, v2 = memo_store.get("proc/a.py", "key2")
    assert v1 == 1 and v2 == 2


def test_stores_arbitrary_python_objects(memo_store):
    payload = {"list": [1, 2, 3], "nested": {"x": True}}
    memo_store.set("path", "k", payload)
    _, result = memo_store.get("path", "k")
    assert result == payload


# ---------------------------------------------------------------------------
# MemoizationStore.delete_component
# ---------------------------------------------------------------------------


def test_delete_component_removes_matching_entries(memo_store):
    memo_store.set("process_file/src/a.py", "k1", "v1")
    memo_store.set("process_file/src/a.py", "k2", "v2")
    memo_store.delete_component("process_file", "src/a.py")
    assert memo_store.get("process_file/src/a.py", "k1") == (False, None)
    assert memo_store.get("process_file/src/a.py", "k2") == (False, None)


def test_delete_component_keeps_other_paths(memo_store):
    memo_store.set("process_file/src/a.py", "k", "a")
    memo_store.set("process_file/src/b.py", "k", "b")
    memo_store.delete_component("process_file", "src/a.py")
    hit, val = memo_store.get("process_file/src/b.py", "k")
    assert hit is True and val == "b"


def test_delete_component_noop_when_not_found(memo_store):
    # Should not raise
    memo_store.delete_component("process_file", "nonexistent.py")


# ---------------------------------------------------------------------------
# initialize_memo_store / get_memo_store
# ---------------------------------------------------------------------------


def test_get_memo_store_before_init_raises():
    original = _memo_module._memo_store
    _memo_module._memo_store = None
    try:
        with pytest.raises(RuntimeError, match="not initialised"):
            get_memo_store()
    finally:
        _memo_module._memo_store = original


def test_get_memo_store_after_init_returns_store(memo_store):
    store = get_memo_store()
    assert isinstance(store, MemoizationStore)
