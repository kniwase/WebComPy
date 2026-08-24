"""Exceptions raised by the dependency injection system."""

from __future__ import annotations


class InjectionError(Exception):
    """Raised when a dependency key has no provider in any scope.

    Args:
        key: Dependency key that could not be resolved. ``InjectKey``
            instances and types are rendered by name in the message.

    """

    def __init__(self, key: object) -> None:
        from webcompy.di._key import InjectKey

        if isinstance(key, InjectKey):
            description = f"InjectKey({key.name!r})"
        elif isinstance(key, type):
            description = key.__name__
        else:
            description = repr(key)
        super().__init__(f"No provider found for {description}")
