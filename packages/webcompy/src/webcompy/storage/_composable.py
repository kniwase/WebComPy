from __future__ import annotations

import contextlib
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar, cast, overload

from webcompy import logging
from webcompy.di._keys import _STORAGE_SYNC_REGISTRY_KEY
from webcompy.di._scope import _get_app_di_scope
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


def _browser_window() -> Any:
    from pyscript import context  # type: ignore[import-untyped]

    return context.window


def _create_event_proxy(handler: Callable[[Any], None]) -> Any:
    from pyscript import ffi  # type: ignore[import-untyped]

    return ffi.create_proxy(handler)


def _resolve_default(default: T | Callable[[], T]) -> T:
    if callable(default):
        return cast("Callable[[], T]", default)()
    return cast("T", default)


def _pyscript_ffi_is_none(raw: Any) -> bool:
    from pyscript import ffi as _pyscript_ffi  # type: ignore[import-untyped]

    return bool(_pyscript_ffi.is_none(raw))


def _is_missing(raw: Any) -> bool:
    if raw is None:
        return True
    if ENVIRONMENT == "pyscript":
        return _pyscript_ffi_is_none(raw)
    return False


def _is_missing_pyscript(raw: Any) -> bool:
    # Browser-only null detection without an ENVIRONMENT guard: unlike _is_missing,
    # this SHALL only be called from browser event-dispatch paths (the storage
    # listener is attached only in PyScript), where the ffi check is always wanted.
    if raw is None:
        return True
    return _pyscript_ffi_is_none(raw)


def _read(storage: Any, key: str, default: T | Callable[[], T]) -> T:
    raw = storage.getItem(key)
    if _is_missing(raw):
        return _resolve_default(default)
    try:
        return cast("T", json.loads(str(raw)))
    except (ValueError, TypeError):
        logging.warning(f"webcompy storage: ignoring corrupted value for key {key!r}")
        return _resolve_default(default)


def _write(storage: Any, key: str, value: Any) -> None:
    try:
        payload = json.dumps(value)
    except (TypeError, ValueError):
        logging.warning(f"webcompy storage: value for key {key!r} is not JSON-serializable; write skipped")
        return
    try:
        storage.setItem(key, payload)
    except Exception:
        logging.warning(f"webcompy storage: failed to write key {key!r}")


class _StorageSyncRegistry:
    """Per-app shared ``storage`` event listener with key-based dispatch.

    One listener (one ``create_proxy`` + one ``addEventListener``) is shared by
    every ``sync_tabs=True`` instance of the app; events are fanned out to the
    callbacks registered for the event's key. ``clear()`` events (``key`` null)
    notify every subscriber so all registered keys reset.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[str | None], None]]] = {}
        self._proxy: Any = None
        self._attached: bool = False

    def subscribe(self, key: str, callback: Callable[[str | None], None]) -> None:
        self._subscribers.setdefault(key, []).append(callback)
        self._ensure_attached()

    def unsubscribe(self, key: str, callback: Callable[[str | None], None]) -> None:
        callbacks = self._subscribers.get(key)
        if not callbacks:
            return
        with contextlib.suppress(ValueError):
            callbacks.remove(callback)
        if not callbacks:
            del self._subscribers[key]

    def _ensure_attached(self) -> None:
        if self._attached:
            return
        window = _browser_window()
        self._proxy = _create_event_proxy(self._dispatch)
        window.addEventListener("storage", self._proxy)
        self._attached = True

    def _dispatch(self, event: Any) -> None:
        key = None if _is_missing_pyscript(event.key) else str(event.key)
        new_value = None if _is_missing_pyscript(event.newValue) else str(event.newValue)
        if key is None:
            callbacks = [cb for subs in list(self._subscribers.values()) for cb in list(subs)]
        else:
            callbacks = list(self._subscribers.get(key, ()))
        for callback in callbacks:
            try:
                callback(new_value)
            except Exception as err:
                logging.warning(
                    f"webcompy storage: storage event handler for key {key!r} failed; continuing dispatch: {err}"
                )

    def dispose(self) -> None:
        if not self._attached:
            return
        with contextlib.suppress(Exception):
            _browser_window().removeEventListener("storage", self._proxy)
        with contextlib.suppress(Exception):
            self._proxy.destroy()
        self._proxy = None
        self._attached = False
        self._subscribers.clear()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.dispose()


def _get_or_create_registry() -> _StorageSyncRegistry | None:
    scope = _get_app_di_scope()
    if scope is None:
        return None
    existing = scope.inject(_STORAGE_SYNC_REGISTRY_KEY, default=None)
    if existing is None:
        existing = _StorageSyncRegistry()
        scope.provide(_STORAGE_SYNC_REGISTRY_KEY, existing)
    return cast("_StorageSyncRegistry", existing)


def _register_destroy_unregister(
    key: str,
    callback: Callable[[str | None], None],
    registry: _StorageSyncRegistry,
) -> None:
    from webcompy.components._hooks import _register_before_destroy_chained

    def _unregister() -> None:
        registry.unsubscribe(key, callback)

    _register_before_destroy_chained(_unregister)


def _make(
    key: str,
    default: T | Callable[[], T],
    storage: Any | None,
    *,
    sync_tabs: bool = False,
) -> Signal[T]:
    if storage is None:
        return Signal(_resolve_default(default))
    sig: Signal[T] = Signal(_read(storage, key, default))
    applying_remote = False

    def _write_back(value: Any) -> None:
        if applying_remote:
            return
        _write(storage, key, value)

    sig.on_after_updating(_write_back)

    if not sync_tabs:
        return sig

    registry = _get_or_create_registry()
    if registry is None:
        logging.warning(
            f"webcompy storage: sync_tabs=True for key {key!r} but no app DI scope is active; subscription skipped"
        )
        return sig

    def _apply_remote(raw: str | None) -> None:
        nonlocal applying_remote
        if raw is None:
            new_value = _resolve_default(default)
        else:
            try:
                new_value = cast("T", json.loads(raw))
            except (ValueError, TypeError):
                logging.warning(f"webcompy storage: ignoring corrupted remote value for key {key!r}")
                new_value = _resolve_default(default)
        if sig.value == new_value:
            return
        applying_remote = True
        try:
            sig.value = new_value
        finally:
            applying_remote = False

    registry.subscribe(key, _apply_remote)
    _register_destroy_unregister(key, _apply_remote, registry)
    return sig


@overload
def use_local_storage(key: str, default: Callable[[], T], *, sync_tabs: bool = False) -> Signal[T]: ...
@overload
def use_local_storage(key: str, default: T, *, sync_tabs: bool = False) -> Signal[T]: ...
def use_local_storage(
    key: str,
    default: T | Callable[[], T],
    *,
    sync_tabs: bool = False,
) -> Signal[T]:
    """Create a ``Signal`` persisted to ``localStorage``.

    In the browser the current stored value for ``key`` is read at
    creation time (JSON-decoded) and used as the initial value; when the
    key is absent, ``default`` is used. Every subsequent update of the
    returned signal is written back to ``localStorage`` (JSON-encoded).

    In any non-PyScript environment (SSR, SSG, server-side tests) no
    storage API is accessed and ``Signal(default)`` is returned.

    When ``sync_tabs=True`` (browser only) the signal additionally reacts
    to ``storage`` events fired by other tabs of the same origin: a write
    of ``key`` updates the signal to the incoming JSON-decoded value, and
    a removal (``removeItem`` or ``clear()`` covering it) resets it to
    ``default``. Concurrent writes follow last-writer-wins; applying a
    remote value never re-broadcasts to other tabs. ``sync_tabs=True`` is
    a no-op outside PyScript (no listener is created).

    The value type is inferred from ``default``. To declare a wider
    type (for example an optional value), annotate the variable::

        theme: Signal[str | None] = use_local_storage("theme", None)
    """
    if callable(default):
        _validate_factory(default)
    return _make(
        key,
        default,
        _local_storage() if ENVIRONMENT == "pyscript" else None,
        sync_tabs=sync_tabs,
    )


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
    _check_sync: Signal[str] = use_local_storage("k", "x", sync_tabs=True)
    _check_sync_factory: Signal[int] = use_local_storage("k", lambda: 0, sync_tabs=True)
