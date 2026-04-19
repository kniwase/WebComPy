from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, TypeVar, overload

from webcompy.di._exceptions import InjectionError
from webcompy.di._key import InjectKey

T = TypeVar("T")
D = TypeVar("D")

_MISSING: Any = object()

_active_di_scope: ContextVar[DIScope | None] = ContextVar("_active_di_scope", default=None)


class DIScope:
    __slots__ = ("_children", "_disposed", "_parent", "_providers", "_token")

    def __init__(
        self,
        providers: dict[Any, Any] | None = None,
        parent: DIScope | None = None,
    ) -> None:
        self._providers: dict[Any, Any] = {}
        self._parent = parent
        self._children: list[DIScope] = []
        self._disposed = False
        self._token: Token[DIScope | None] | None = None
        if providers:
            self._providers.update(providers)

    def provide(self, key: Any, value: Any) -> None:
        if self._disposed:
            raise RuntimeError("Cannot provide into a disposed DIScope")
        self._providers[key] = value

    @overload
    def inject(self, key: type[T]) -> T: ...
    @overload
    def inject(self, key: InjectKey[T]) -> T: ...
    @overload
    def inject(self, key: type[T], default: D) -> T | D: ...
    @overload
    def inject(self, key: InjectKey[T], default: D) -> T | D: ...
    @overload
    def inject(self, key: object) -> Any: ...
    @overload
    def inject(self, key: object, default: D) -> Any: ...

    def inject(self, key: Any, default: Any = _MISSING) -> Any:
        if self._disposed:
            if default is _MISSING:
                raise InjectionError(key, "Cannot inject from a disposed DIScope")
            return default

        current: DIScope | None = self
        while current is not None:
            if key in current._providers:
                value = current._providers[key]
                if callable(value) and not isinstance(value, type):
                    resolved = value()
                    current._providers[key] = resolved
                    return resolved
                return value
            current = current._parent

        if default is not _MISSING:
            return default

        raise InjectionError(key)

    def create_child(self, providers: dict[Any, Any] | None = None) -> DIScope:
        if self._disposed:
            raise RuntimeError("Cannot create child of a disposed DIScope")
        child = DIScope(providers=providers, parent=self)
        self._children.append(child)
        return child

    def dispose(self) -> None:
        for child in self._children:
            child.dispose()
        self._children.clear()
        self._providers.clear()
        self._disposed = True

    def __enter__(self) -> DIScope:
        token = _active_di_scope.set(self)
        self._token = token
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _active_di_scope.reset(self._token)
