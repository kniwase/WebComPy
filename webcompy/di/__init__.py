from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from webcompy.di._exceptions import InjectionError
from webcompy.di._key import InjectKey
from webcompy.di._scope import _MISSING, DIScope, _active_di_scope

_pending_di_parent: ContextVar[DIScope | None] = ContextVar("_pending_di_parent", default=None)


def provide(key: object, value: Any) -> None:
    try:
        scope = _active_di_scope.get()
        if scope is None:
            raise LookupError
    except LookupError:
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
    try:
        scope = _active_di_scope.get()
        if scope is None:
            raise LookupError
    except LookupError:
        if default is not _MISSING:
            return default
        raise InjectionError(key) from None
    return scope.inject(key, default)


__all__ = [
    "DIScope",
    "InjectKey",
    "InjectionError",
    "inject",
    "provide",
]
