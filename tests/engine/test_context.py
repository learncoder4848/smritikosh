"""Tests for ContextKey, PipelineContext, use_context."""

import pytest

from smritikosh.engine import ContextKey, PipelineContext, use_context


# ---------------------------------------------------------------------------
# ContextKey
# ---------------------------------------------------------------------------


def test_context_key_defaults():
    key = ContextKey("db")
    assert key.name == "db"
    assert key.detect_change is False


def test_context_key_detect_change():
    key = ContextKey("embedder", detect_change=True)
    assert key.detect_change is True


def test_context_key_repr():
    key = ContextKey("db", detect_change=True)
    assert repr(key) == "ContextKey('db', detect_change=True)"


# ---------------------------------------------------------------------------
# PipelineContext — provide / get
# ---------------------------------------------------------------------------


def test_provide_and_get():
    key: ContextKey[str] = ContextKey("x")
    ctx = PipelineContext()
    ctx.provide(key, "hello")
    assert ctx.get(key) == "hello"


def test_get_missing_key_raises():
    key: ContextKey[str] = ContextKey("missing")
    ctx = PipelineContext()
    with pytest.raises(KeyError, match="No value provided"):
        ctx.get(key)


def test_provide_overwrites():
    key: ContextKey[int] = ContextKey("n")
    ctx = PipelineContext()
    ctx.provide(key, 1)
    ctx.provide(key, 2)
    assert ctx.get(key) == 2


# ---------------------------------------------------------------------------
# PipelineContext — detect_change_fingerprint
# ---------------------------------------------------------------------------


def test_fingerprint_ignores_non_detect_change_keys():
    key = ContextKey("db", detect_change=False)
    ctx = PipelineContext()
    ctx.provide(key, "anything")
    # No detect_change=True keys → always the same zero-input hash
    fp1 = ctx.detect_change_fingerprint()
    fp2 = ctx.detect_change_fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 64  # sha256 hex digest


def test_fingerprint_changes_when_detect_change_value_changes():
    key = ContextKey("model", detect_change=True)
    ctx1 = PipelineContext()
    ctx1.provide(key, "jina-v1")
    ctx2 = PipelineContext()
    ctx2.provide(key, "jina-v2")
    assert ctx1.detect_change_fingerprint() != ctx2.detect_change_fingerprint()


def test_fingerprint_stable_for_same_value():
    key = ContextKey("model", detect_change=True)
    ctx1 = PipelineContext()
    ctx1.provide(key, "jina-v1")
    ctx2 = PipelineContext()
    ctx2.provide(key, "jina-v1")
    assert ctx1.detect_change_fingerprint() == ctx2.detect_change_fingerprint()


# ---------------------------------------------------------------------------
# PipelineContext — sync context manager
# ---------------------------------------------------------------------------


def test_sync_context_manager_activates_context():
    key: ContextKey[int] = ContextKey("val")
    with PipelineContext() as ctx:
        ctx.provide(key, 42)
        assert use_context(key) == 42


def test_context_deactivated_after_exit():
    with PipelineContext():
        pass
    with pytest.raises(RuntimeError, match="outside an active PipelineContext"):
        use_context(ContextKey("any"))


# ---------------------------------------------------------------------------
# PipelineContext — async context manager
# ---------------------------------------------------------------------------


async def test_async_context_manager_activates_context():
    key: ContextKey[str] = ContextKey("async_val")
    async with PipelineContext() as ctx:
        ctx.provide(key, "works")
        assert use_context(key) == "works"


# ---------------------------------------------------------------------------
# use_context
# ---------------------------------------------------------------------------


def test_use_context_outside_raises():
    with pytest.raises(RuntimeError, match="outside an active PipelineContext"):
        use_context(ContextKey("orphan"))


def test_use_context_inside_returns_value():
    key: ContextKey[list] = ContextKey("items")
    with PipelineContext() as ctx:
        ctx.provide(key, [1, 2, 3])
        assert use_context(key) == [1, 2, 3]


def test_use_context_missing_key_raises_key_error():
    with PipelineContext():
        with pytest.raises(KeyError):
            use_context(ContextKey("not_provided"))
