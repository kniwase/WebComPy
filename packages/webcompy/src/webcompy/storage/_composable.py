from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast, overload

from webcompy import logging
from webcompy.signal import Signal
from webcompy.signal._composable import _validate_factory
from webcompy.utils._environment import ENVIRONMENT

T = TypeVar("T")


def _local_storage() -> Any:
    from pyscript import context  # type: ignore[import-untyped]

    return context.window.localStorage


def _session_storage() -> Any:
    from pyscript import context  # type: ignore[import-untyped]

    return context.window.sessionStorage


def _resolve_default(default: T | Callable[[], T]) -> T:
    if callable(default):
        return cast("Callable[[], T]", default)()
    return cast("T", default)


def _read(storage: Any, key: str, default: T | Callable[[], T]) -> T:
    raw = storage.getItem(key)
    if raw is None:
        return _resolve_default(default)
    try:
        return cast("T", json.loads(str(raw)))
    except (ValueError, TypeError):
        logging.warning(f"webcompy storage: ignoring corrupted value for key {key!r}")
        return _resolve_default(default)


def _write(storage: Any, key: str, value: Any) -> None:
    try:
        payload = json.dumps(value)
    except TypeError:
        logging.warning(f"webcompy storage: value for key {key!r} is not JSON-serializable; write skipped")
        return
    try:
        storage.setItem(key, payload)
    except Exception:
        logging.warning(f"webcompy storage: failed to write key {key!r}")


def _make(key: str, default: T | Callable[[], T], storage: Any | None) -> Signal[T]:
    if storage is None:
        return Signal(_resolve_default(default))
    sig: Signal[T] = Signal(_read(storage, key, default))
    sig.on_after_updating(lambda value: _write(storage, key, value))
    return sig


@overload
def use_local_storage(key: str, default: Callable[[], T]) -> Signal[T]: ...
@overload
def use_local_storage(key: str, default: T) -> Signal[T]: ...
def use_local_storage(key: str, default: T | Callable[[], T]) -> Signal[T]:
    """Create a ``Signal`` persisted to ``localStorage``.

    In the browser the current stored value for ``key`` is read at
    creation time (JSON-decoded) and used as the initial value; when the
    key is absent, ``default`` is used. Every subsequent update of the
    returned signal is written back to ``localStorage`` (JSON-encoded).

    In any non-PyScript environment (SSR, SSG, server-side tests) no
    storage API is accessed and ``Signal(default)`` is returned.

    The value type is inferred from ``default``. To declare a wider
    type (for example an optional value), annotate the variable::

        theme: Signal[str | None] = use_local_storage("theme", None)
    """
    if callable(default):
        _validate_factory(default)
    return _make(key, default, _local_storage() if ENVIRONMENT == "pyscript" else None)


@overload
def use_session_storage(key: str, default: Callable[[], T]) -> Signal[T]: ...
@overload
def use_session_storage(key: str, default: T) -> Signal[T]: ...
def use_session_storage(key: str, default: T | Callable[[], T]) -> Signal[T]:
    """Create a ``Signal`` persisted to ``sessionStorage``.

    Same semantics as :func:`use_local_storage` but backed by
    ``sessionStorage`` (per-tab lifetime).
    """
    if callable(default):
        _validate_factory(default)
    return _make(key, default, _session_storage() if ENVIRONMENT == "pyscript" else None)


if TYPE_CHECKING:
    _check_value: Signal[str] = use_local_storage("k", "x")
    _check_factory: Signal[int] = use_local_storage("k", lambda: 0)
    _check_optional: Signal[str | None] = use_local_storage("k", None)
    _check_session_optional: Signal[dict[str, int] | None] = use_session_storage("k", None)
