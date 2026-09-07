"""Pipeline context — ContextKey, PipelineContext, use_context."""

from __future__ import annotations

import hashlib
import pickle
from contextvars import ContextVar
from typing import Any, Generic, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Module-level context vars
# ---------------------------------------------------------------------------

#: Active PipelineContext for the current async task tree.
_ACTIVE_CONTEXT: ContextVar[PipelineContext | None] = ContextVar(
    "_ACTIVE_CONTEXT", default=None
)

#: Component path set by sm.fan_out for each file boundary.
_COMPONENT_PATH: ContextVar[str] = ContextVar("_COMPONENT_PATH", default="")


# ---------------------------------------------------------------------------
# ContextKey
# ---------------------------------------------------------------------------


class ContextKey(Generic[T]):
    """Named slot for a shared resource in the pipeline context.

    Parameters
    ----------
    name:
        Human-readable identifier used in fingerprinting.
    detect_change:
        When *True* the hash of the bound value is folded into every
        ``@sm.memoized`` cache key so that swapping the value (e.g. a new
        embedder model) automatically invalidates all memos.
    """

    def __init__(self, name: str, detect_change: bool = False) -> None:
        self.name = name
        self.detect_change = detect_change

    def __repr__(self) -> str:
        return f"ContextKey({self.name!r}, detect_change={self.detect_change})"


# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------


class PipelineContext:
    """Holds all :class:`ContextKey` values for one pipeline run.

    Supports both sync and async context managers::

        # sync
        with PipelineContext() as ctx:
            ctx.provide(DB_KEY, con)
            asyncio.run(main())

        # async
        async with PipelineContext() as ctx:
            ctx.provide(DB_KEY, con)
            await sm.fan_out(process_file, files)
    """

    def __init__(self) -> None:
        self._store: dict[ContextKey[Any], Any] = {}
        self._token: Any = None

    # -- mutation --------------------------------------------------------------

    def provide(self, key: ContextKey[T], value: T) -> None:
        """Bind *value* to *key* for the duration of this context."""
        self._store[key] = value

    def get(self, key: ContextKey[T]) -> T:
        """Return the value bound to *key*.

        Raises
        ------
        KeyError
            If no value has been provided for *key*.
        """
        try:
            return self._store[key]  # type: ignore[return-value]
        except KeyError:
            raise KeyError(
                f"No value provided for {key!r}. "
                "Call ctx.provide(key, value) before entering the pipeline."
            ) from None

    def detect_change_fingerprint(self) -> str:
        """Hex digest covering all ``detect_change=True`` key/value pairs."""
        h = hashlib.sha256()
        for key, value in sorted(self._store.items(), key=lambda kv: kv[0].name):
            if key.detect_change:
                h.update(key.name.encode())
                h.update(hashlib.sha256(pickle.dumps(value, protocol=4)).digest())
        return h.hexdigest()

    # -- context managers ------------------------------------------------------

    def __enter__(self) -> PipelineContext:
        self._token = _ACTIVE_CONTEXT.set(self)
        return self

    def __exit__(self, *_: Any) -> None:
        _ACTIVE_CONTEXT.reset(self._token)
        self._token = None

    async def __aenter__(self) -> PipelineContext:
        return self.__enter__()

    async def __aexit__(self, *_: Any) -> None:
        self.__exit__()


# ---------------------------------------------------------------------------
# use_context
# ---------------------------------------------------------------------------


def use_context(key: ContextKey[T]) -> T:
    """Read a :class:`ContextKey` value from the active pipeline context.

    Must be called inside any sm-decorated function while a
    :class:`PipelineContext` is active.

    Raises
    ------
    RuntimeError
        If no :class:`PipelineContext` is currently active.
    KeyError
        If the key has not been provided to the context.
    """
    ctx = _ACTIVE_CONTEXT.get()
    if ctx is None:
        raise RuntimeError(
            "use_context() called outside an active PipelineContext. "
            "Wrap the pipeline entry-point with `with PipelineContext() as ctx:`."
        )
    return ctx.get(key)
