from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class InjectKey(Generic[T]):
    __slots__ = ("_identity", "_name")

    def __init__(self, name: str) -> None:
        self._name = name
        self._identity = object()

    def __repr__(self) -> str:
        return f"InjectKey({self._name!r})"

    def __hash__(self) -> int:
        return id(self._identity)

    def __eq__(self, other: object) -> bool:
        return self is other
