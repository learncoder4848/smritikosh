"""Tests for fingerprinting helpers."""


from smritikosh.engine._context import ContextKey, PipelineContext
from smritikosh.engine._fingerprint import (
    _compute_context_fingerprint,
    _compute_input_fingerprint,
    _compute_logic_fingerprint,
    _hash_bytes,
)

# ---------------------------------------------------------------------------
# _hash_bytes
# ---------------------------------------------------------------------------


def test_hash_bytes_returns_32_bytes():
    assert len(_hash_bytes("hello")) == 32


def test_hash_bytes_stable():
    assert _hash_bytes({"a": 1}) == _hash_bytes({"a": 1})


def test_hash_bytes_different_values():
    assert _hash_bytes("a") != _hash_bytes("b")


# ---------------------------------------------------------------------------
# _compute_logic_fingerprint
# ---------------------------------------------------------------------------


def test_logic_fingerprint_is_hex_64():
    def fn():
        return 1

    fp = _compute_logic_fingerprint(fn)
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_logic_fingerprint_changes_with_source():
    def fn_a():
        return 1

    def fn_b():
        return 2

    assert _compute_logic_fingerprint(fn_a) != _compute_logic_fingerprint(fn_b)


def test_logic_fingerprint_same_source_same_hash():
    def fn():  # noqa: E306
        return 99

    def fn2():  # noqa: E306
        return 99

    # Different function objects but identical bodies → different source lines
    # (different names), so fingerprints differ
    assert _compute_logic_fingerprint(fn) != _compute_logic_fingerprint(fn2)


# ---------------------------------------------------------------------------
# _compute_input_fingerprint
# ---------------------------------------------------------------------------


def test_input_fingerprint_positional():
    fp1 = _compute_input_fingerprint(1, 2)
    fp2 = _compute_input_fingerprint(1, 2)
    assert fp1 == fp2


def test_input_fingerprint_different_args():
    assert _compute_input_fingerprint(1) != _compute_input_fingerprint(2)


def test_input_fingerprint_kwargs_order_independent():
    fp1 = _compute_input_fingerprint(a=1, b=2)
    fp2 = _compute_input_fingerprint(b=2, a=1)
    assert fp1 == fp2


def test_input_fingerprint_args_vs_kwargs_differ():
    # positional vs keyword — different semantic → different hash
    assert _compute_input_fingerprint(1, 2) != _compute_input_fingerprint(a=1, b=2)


# ---------------------------------------------------------------------------
# _compute_context_fingerprint
# ---------------------------------------------------------------------------


def test_context_fingerprint_no_context():
    fp = _compute_context_fingerprint()
    assert len(fp) == 64  # still returns a valid hash


def test_context_fingerprint_with_detect_change_key():
    key = ContextKey("model", detect_change=True)
    with PipelineContext() as ctx:
        ctx.provide(key, "v1")
        fp_v1 = _compute_context_fingerprint()
    with PipelineContext() as ctx:
        ctx.provide(key, "v2")
        fp_v2 = _compute_context_fingerprint()
    assert fp_v1 != fp_v2


def test_context_fingerprint_without_detect_change_unchanged():
    key = ContextKey("storage", detect_change=False)
    with PipelineContext() as ctx:
        ctx.provide(key, "conn_a")
        fp1 = _compute_context_fingerprint()
    with PipelineContext() as ctx:
        ctx.provide(key, "conn_b")
        fp2 = _compute_context_fingerprint()
    # detect_change=False → context value changes don't affect fingerprint
    assert fp1 == fp2
