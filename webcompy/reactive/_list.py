from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, TypeVar, cast, overload

from webcompy.reactive._base import Reactive, ReactiveBase

V = TypeVar("V")


class ReactiveList(Reactive[list[V]]):
    def __init__(self, init_value: list[V]) -> None:
        super().__init__(init_value)

    @ReactiveBase._change_event
    def append(self, value: V):
        self._value.append(value)

    @ReactiveBase._change_event
    def extend(self, value: Iterable[V]):
        self._value.extend(value)

    @ReactiveBase._change_event
    def pop(self, index: int | None = None):
        return self._value.pop() if index is None else self._value.pop(index)

    @ReactiveBase._change_event
    def insert(self, index: int, value: V):
        self._value.insert(index, value)

    @ReactiveBase._change_event
    def sort(self, key: Callable[[V], Any] = lambda it: it, reverse: bool = False):
        self._value.sort(key=key, reverse=reverse)

    @ReactiveBase._get_event
    def index(self, value: V):
        return self._value.index(value)

    @ReactiveBase._get_event
    def count(self, value: V):
        return self._value.count(value)

    @ReactiveBase._change_event
    def remove(self, value: V):
        self._value.remove(value)

    @ReactiveBase._change_event
    def clear(self):
        self._value.clear()

    @ReactiveBase._change_event
    def reverse(self):
        self._value.reverse()

    @overload
    def __getitem__(self, idx: int) -> V: ...

    @overload
    def __getitem__(self, idx: slice) -> list[V]: ...

    @ReactiveBase._get_event
    def __getitem__(self, idx: int | slice):
        return self._value.__getitem__(idx)

    @overload
    def __setitem__(self, idx: int, value: V) -> None: ...

    @overload
    def __setitem__(self, idx: slice, value: Iterable[V]) -> None: ...

    @ReactiveBase._change_event
    def __setitem__(self, idx: int | slice, value: V | Iterable[V]):
        if isinstance(idx, int):
            self._value.__setitem__(idx, cast("V", value))
        else:
            self._value.__setitem__(idx, cast("Iterable[V]", value))

    @ReactiveBase._get_event
    def __len__(self):
        return len(self._value)

    @ReactiveBase._get_event
    def __iter__(self):
        return iter(self._value)
