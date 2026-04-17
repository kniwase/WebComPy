from typing import Any, TypeVar

from webcompy.reactive._base import Reactive, ReactiveBase

K = TypeVar("K")
V = TypeVar("V")


class ReactiveDict(Reactive[dict[K, V]]):
    def __init__(self, init_value: dict[K, V] | None = None) -> None:
        super().__init__(init_value if init_value is not None else {})

    @ReactiveBase._get_event
    def __getitem__(self, key: K):
        return self._value.__getitem__(key)

    @ReactiveBase._change_event
    def __setitem__(self, key: K, value: V):
        self._value.__setitem__(key, value)

    @ReactiveBase._change_event
    def __delitem__(self, key: K):
        self._value.__delitem__(key)

    @ReactiveBase._change_event
    def pop(self, key: K):
        return self._value.pop(key)

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
