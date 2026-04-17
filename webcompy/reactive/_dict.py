from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from webcompy.reactive._base import Reactive, ReactiveBase

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class DictMutation:
    op: str
    key: str | int | None
    value: Any


class ReactiveDict(Reactive[dict[K, V]]):
    _last_mutation: DictMutation | None

    def __init__(self, init_value: dict[K, V] | None = None) -> None:
        super().__init__(init_value if init_value is not None else {})
        self._last_mutation = None

    @ReactiveBase._get_event
    def __getitem__(self, key: K):
        return self._value.__getitem__(key)

    @ReactiveBase._change_event
    def __setitem__(self, key: K, value: V):
        self._value.__setitem__(key, value)
        self._last_mutation = DictMutation(op="set", key=key, value=value)  # type: ignore[arg-type]

    @ReactiveBase._change_event
    def __delitem__(self, key: K):
        val = self._value[key]
        self._value.__delitem__(key)
        self._last_mutation = DictMutation(op="delete", key=key, value=val)  # type: ignore[arg-type]

    @ReactiveBase._change_event
    def pop(self, key: K):
        val = self._value.pop(key)
        self._last_mutation = DictMutation(op="pop", key=key, value=val)  # type: ignore[arg-type]
        return val

    @ReactiveBase._change_event
    def clear(self):
        self._value.clear()
        self._last_mutation = DictMutation(op="clear", key=None, value=None)

    @ReactiveBase._get_event
    def __len__(self):
        return len(self._value)

    @ReactiveBase._get_event
    def __iter__(self):
        return iter(self._value)

    @ReactiveBase._get_event
    def get(self, key: K, default: Any = None):
        return self._value.get(key, default)

    @ReactiveBase._get_event
    def keys(self):
        return self._value.keys()

    @ReactiveBase._get_event
    def values(self):
        return self._value.values()

    @ReactiveBase._get_event
    def items(self):
        return self._value.items()
