"""Identity-based dependency key types: ``InjectKey``."""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class InjectKey(Generic[T]):
    """Typed, identity-based key for dependency injection lookups.

    Keys compare and hash by identity rather than by name, so two keys
    created with the same name remain distinct. The type parameter
    documents the value type provided under the key.

    Args:
        name: Human-readable name used in messages and ``repr``.

    Attributes:
        name: Human-readable name of the key, set at construction.

    """

    __slots__ = ("_identity", "_name")

    def __init__(self, name: str) -> None:
        self._name = name
        self._identity = object()

    @property
    def name(self) -> str:
        """Human-readable name of the key, set at construction."""
        return self._name

    def __repr__(self) -> str:
        return f"InjectKey({self._name!r})"

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)
