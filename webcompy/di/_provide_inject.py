from __future__ import annotations

from typing import Any, TypeVar, overload

from webcompy.di._exceptions import InjectionError
from webcompy.di._key import InjectKey
from webcompy.di._scope import _MISSING, _active_di_scope

T = TypeVar("T")
D = TypeVar("D")


def provide(key: Any, value: Any) -> None:
    scope = _active_di_scope.get(None)
    if scope is None:
        raise InjectionError(
            key,
            "provide() must be called inside a DI scope. "
            "Use a DIScope context manager or call within a component setup function.",
        )
    from webcompy.components._hooks import _active_component_context

    try:
        context = _active_component_context.get()
    except LookupError:
        scope.provide(key, value)
        return

    child_scope_factory = getattr(context, "_ensure_child_di_scope", None)
    if child_scope_factory is not None:
        child_scope = child_scope_factory()
        child_scope.provide(key, value)
        _active_di_scope.set(child_scope)
    else:
        scope.provide(key, value)


@overload
def inject(key: type[T]) -> T: ...
@overload
def inject(key: InjectKey[T]) -> T: ...
@overload
def inject(key: type[T], default: D) -> T | D: ...
@overload
def inject(key: InjectKey[T], default: D) -> T | D: ...
@overload
def inject(key: object) -> Any: ...
@overload
def inject(key: object, default: D) -> Any: ...


def inject(key: Any, default: Any = _MISSING) -> Any:
    scope = _active_di_scope.get(None)
    if scope is None:
        if default is not _MISSING:
            return default
        raise InjectionError(
            key,
            "inject() must be called inside a DI scope. "
            "Use a DIScope context manager or call within a component setup function.",
        )
    return scope.inject(key, default)
