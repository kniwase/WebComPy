"""Scoped dependency-injection container: ``DIScope`` and scope context management."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from webcompy.di._exceptions import InjectionError

_active_di_scope: ContextVar[DIScope] = ContextVar("_active_di_scope")

_app_di_scope: DIScope | None = None

_MISSING: Any = object()


def _set_app_di_scope(scope: DIScope | None) -> None:
    global _app_di_scope
    _app_di_scope = scope


def _get_app_di_scope() -> DIScope | None:
    return _app_di_scope


class DIScope:
    """Provider map with parent delegation, child scopes, and disposal.

    ``inject`` resolves keys from the local provider map, then from the
    parent scope. Callable providers (that are not classes) are invoked
    lazily on first injection and cached. ``dispose`` marks the scope and
    all descendants as disposed; injection on a disposed scope falls
    through to the parent or ``default``.

    Args:
        providers: Initial key-to-value mappings for the scope.
        parent: Parent scope consulted when a key is not local.

    """

    __slots__ = ("_children", "_disposed", "_parent", "_providers", "_token")

    def __init__(
        self,
        providers: dict[object, Any] | None = None,
        parent: DIScope | None = None,
    ) -> None:
        self._providers: dict[object, Any] = dict(providers) if providers else {}
        self._parent = parent
        self._children: list[DIScope] = []
        self._disposed = False
        self._token: Token[DIScope] | None = None

    def provide(self, key: object, value: Any) -> None:
        """Register a value for a key in this scope.

        Args:
            key: Dependency key to register.
            value: Provider value stored for the key.

        Raises:
            RuntimeError: If the scope has been disposed.

        """
        if self._disposed:
            raise RuntimeError("Cannot provide into a disposed DIScope")
        self._providers[key] = value

    def inject(self, key: object, default: Any = _MISSING) -> Any:
        """Resolve a key from this scope, delegating to the parent.

        Callable providers that are not classes are invoked lazily and
        their result is cached.

        Args:
            key: Dependency key to resolve.
            default: Value to return when the key is not provided. When
                omitted, resolution failure raises ``InjectionError``.

        Returns:
            The value provided for ``key``.

        Raises:
            InjectionError: If the key is not provided (in this scope,
                its parent, or any ancestor) and no ``default`` is given.

        """
        if self._disposed:
            if self._parent is not None:
                return self._parent.inject(key, default)
            if default is not _MISSING:
                return default
            raise InjectionError(key)
        if key in self._providers:
            value = self._providers[key]
            if callable(value) and not isinstance(value, type):
                value = value()
                self._providers[key] = value
            return value
        if self._parent is not None:
            return self._parent.inject(key, default)
        if default is not _MISSING:
            return default
        raise InjectionError(key)

    def dispose(self) -> None:
        """Dispose this scope, all child scopes, and its providers.

        After disposal, ``provide`` and ``create_child`` raise
        ``RuntimeError`` and injection falls through to the parent scope.
        """
        self._disposed = True
        for child in self._children:
            child.dispose()
        self._providers.clear()

    def create_child(self) -> DIScope:
        """Create a child scope with this scope as parent.

        Returns:
            The new child ``DIScope`` instance.

        Raises:
            RuntimeError: If the scope has been disposed.

        """
        if self._disposed:
            raise RuntimeError("Cannot create child of a disposed DIScope")
        child = DIScope(parent=self)
        self._children.append(child)
        return child

    def __enter__(self) -> DIScope:
        self._token = _active_di_scope.set(self)
        return self

    def __exit__(self, *args: object) -> None:
        if self._token is not None:
            try:
                _active_di_scope.reset(self._token)
            except (RuntimeError, ValueError):
                _active_di_scope.set(None)  # type: ignore[arg-type]
        self._token = None
