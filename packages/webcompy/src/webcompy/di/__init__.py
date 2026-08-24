"""Dependency injection: ``DIScope`` containers, keyed providers, and the ``provide``/``inject`` accessors."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from webcompy.di._exceptions import InjectionError
from webcompy.di._key import InjectKey
from webcompy.di._keys import (
    HYDRATION_DATA_KEY,
    HYDRATION_SIGNAL_DATA_KEY,
    RESOURCE_DATA_KEY,
    SUSPENSE_RESOLVING_KEY,
)
from webcompy.di._scope import _MISSING, DIScope, _active_di_scope, _get_app_di_scope

_pending_di_parent: ContextVar[DIScope | None] = ContextVar("_pending_di_parent", default=None)


def provide(key: object, value: Any) -> None:
    """Provide a value for a dependency key in the active DI scope.

    Registers ``key`` with ``value`` in the currently active ``DIScope``.
    When no render scope is active, the app-level DI scope is used.

    Args:
        key: Dependency key to register (an ``InjectKey`` or a type).
        value: Provider value stored for the key.

    Raises:
        InjectionError: If no active scope and no app-level scope exists.

    """
    try:
        scope = _active_di_scope.get()
        if scope is None:
            raise LookupError
    except LookupError:
        app_scope = _get_app_di_scope()
        if app_scope is not None:
            app_scope.provide(key, value)
            return
        raise InjectionError(key) from None
    pending_parent = _pending_di_parent.get(None)
    if pending_parent is not None:
        child = pending_parent.create_child()
        child.provide(key, value)
        _active_di_scope.set(child)
        _pending_di_parent.set(None)
    else:
        scope.provide(key, value)


def inject(key: object, default: Any = _MISSING) -> Any:
    """Resolve a dependency from the active DI scope.

    Looks up ``key`` in the currently active ``DIScope`` (or the app-level
    scope when no render scope is active), delegating to parent scopes.

    Args:
        key: Dependency key to resolve.
        default: Value to return when the key is not provided. When
            omitted, resolution failure raises ``InjectionError``.

    Returns:
        The value provided for ``key``.

    Raises:
        InjectionError: If the key is not provided and no ``default`` is
            given.

    """
    try:
        scope = _active_di_scope.get()
        if scope is None:
            raise LookupError
    except LookupError:
        app_scope = _get_app_di_scope()
        if app_scope is not None:
            if default is _MISSING:
                return app_scope.inject(key)
            return app_scope.inject(key, default)
        if default is not _MISSING:
            return default
        raise InjectionError(key) from None
    return scope.inject(key, default)


__all__ = [
    "HYDRATION_DATA_KEY",
    "HYDRATION_SIGNAL_DATA_KEY",
    "RESOURCE_DATA_KEY",
    "SUSPENSE_RESOLVING_KEY",
    "DIScope",
    "InjectKey",
    "InjectionError",
    "inject",
    "provide",
]
