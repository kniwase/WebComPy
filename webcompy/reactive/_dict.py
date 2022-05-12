from typing import Any, Dict, TypeVar
from webcompy.reactive._base import Reactive, ReactiveBase


K = TypeVar("K")
V = TypeVar("V")


class ReactiveDict(Reactive[Dict[K, V]]):
    def __init__(self, init_value: dict[K, V] = {}) -> None:
        super().__init__(init_value)

    @ReactiveBase._get_evnet
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

    @ReactiveBase._get_evnet
    def __len__(self):
        return len(self._value)

    @ReactiveBase._get_evnet
    def __iter__(self):
        return iter(self._value)

    @ReactiveBase._get_evnet
    def get(self, key: K, default: Any = None):
        return self._value.get(key, default)

    @ReactiveBase._get_evnet
    def keys(self):
        return self._value.keys()

    @ReactiveBase._get_evnet
    def values(self):
        return self._value.values()

    @ReactiveBase._get_evnet
    def items(self):
        return self._value.items()
