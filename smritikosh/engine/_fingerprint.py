"""Fingerprinting helpers for cache-key computation."""

from __future__ import annotations

import hashlib
import inspect
import pickle
from collections.abc import Callable
from typing import Any

from smritikosh.engine._context import _ACTIVE_CONTEXT

# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

#: Logic fingerprints of every @sm.tracked function registered in this process.
#: Included in every @sm.memoized cache key so that editing a tracked helper's
#: source automatically invalidates all downstream memos.
_tracked_logic_fps: set[str] = set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_bytes(value: Any) -> bytes:
    """Return a stable 32-byte digest for any pickle-able value."""
    return hashlib.sha256(pickle.dumps(value, protocol=4)).digest()


def _compute_logic_fingerprint(fn: Callable[..., Any]) -> str:
    """sha256 of the function's source — computed once at decoration time."""
    return hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()


def _compute_input_fingerprint(*args: Any, **kwargs: Any) -> str:
    """sha256 of serialised positional and keyword arguments."""
    h = hashlib.sha256()
    for arg in args:
        h.update(_hash_bytes(arg))
    for k, v in sorted(kwargs.items()):
        h.update(k.encode())
        h.update(_hash_bytes(v))
    return h.hexdigest()


def _compute_context_fingerprint() -> str:
    """Combine detect_change=True context values with all tracked logic fps.

    Two sources of invalidation:

    1. ``detect_change=True`` :class:`~._context.ContextKey` values
       (e.g. embedder model_id) from the active pipeline context.
    2. Logic fingerprints of every ``@sm.tracked`` function — so that
       editing a tracked helper's source invalidates all downstream memos.
    """
    ctx = _ACTIVE_CONTEXT.get()
    ctx_fp = ctx.detect_change_fingerprint() if ctx else ""
    tracked_fp = hashlib.sha256(
        "|".join(sorted(_tracked_logic_fps)).encode()
    ).hexdigest()
    return hashlib.sha256(f"{ctx_fp}|{tracked_fp}".encode()).hexdigest()
