from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, TypeVar, cast, overload

from webcompy.reactive._base import Reactive, ReactiveBase

V = TypeVar("V")


@dataclass
class ListMutation:
    op: str
    index: int | None
    value: Any


class ReactiveList(Reactive[list[V]]):
    _last_mutation: ListMutation | None

    def __init__(self, init_value: list[V]) -> None:
        super().__init__(init_value)
        self._last_mutation = None

    @ReactiveBase._change_event
    def append(self, value: V):
        self._value.append(value)
        self._last_mutation = ListMutation(op="append", index=len(self._value) - 1, value=value)

    @ReactiveBase._change_event
    def extend(self, value: Iterable[V]):
        start_index = len(self._value)
        items = list(value)
        self._value.extend(items)
        self._last_mutation = ListMutation(op="extend", index=start_index, value=items)

    @ReactiveBase._change_event
    def pop(self, index: int | None = None):
        actual_index = len(self._value) - 1 if index is None else index
        popped = self._value.pop() if index is None else self._value.pop(index)
        self._last_mutation = ListMutation(op="pop", index=actual_index, value=popped)
        return popped

    @ReactiveBase._change_event
    def insert(self, index: int, value: V):
        self._value.insert(index, value)
        self._last_mutation = ListMutation(op="insert", index=index, value=value)

    @ReactiveBase._change_event
    def sort(self, key: Callable[[V], Any] = lambda it: it, reverse: bool = False):
        self._value.sort(key=key, reverse=reverse)
        self._last_mutation = ListMutation(op="sort", index=None, value=None)

    @ReactiveBase._get_event
    def index(self, value: V):
        return self._value.index(value)

    @ReactiveBase._get_event
    def count(self, value: V):
        return self._value.count(value)

    @ReactiveBase._change_event
    def remove(self, value: V):
        idx = self._value.index(value)
        self._value.remove(value)
        self._last_mutation = ListMutation(op="remove", index=idx, value=value)

    @ReactiveBase._change_event
    def clear(self):
        self._value.clear()
        self._last_mutation = ListMutation(op="clear", index=None, value=None)

    @ReactiveBase._change_event
    def reverse(self):
        self._value.reverse()
        self._last_mutation = ListMutation(op="reverse", index=None, value=None)

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
            self._last_mutation = ListMutation(op="setitem", index=idx, value=value)
        else:
            self._value.__setitem__(idx, cast("Iterable[V]", value))
            self._last_mutation = ListMutation(op="setitem", index=None, value=None)

    @ReactiveBase._get_event
    def __len__(self):
        return len(self._value)

    @ReactiveBase._get_event
    def __iter__(self):
        return iter(self._value)
