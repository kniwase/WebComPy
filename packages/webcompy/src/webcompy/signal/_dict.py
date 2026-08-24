"""Reactive dictionary wrapper: ``DictMutation`` and ``ReactiveDict``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from webcompy.signal._base import Signal, SignalBase

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class DictMutation:
    """Record of the most recent mutating operation on a ``ReactiveDict``.

    Args:
        op: Operation name (e.g. ``"set"``, ``"delete"``, ``"clear"``).
        key: Key the operation targeted, when applicable.
        value: Value set by the mutation, when applicable.

    Attributes:
        op: Operation name (e.g. ``"set"``, ``"delete"``, ``"clear"``).
        key: Key the operation targeted, when applicable.
        value: Value set by the mutation, when applicable.

    """

    op: str
    key: str | int | None
    value: Any


class ReactiveDict(Signal[dict[K, V]]):
    """Reactive wrapper around a ``dict`` behaving like ``Signal[dict]``.

    Mutation methods (``__setitem__``, ``__delitem__``, ``pop``,
    ``clear``) propagate change notifications to consumers; read methods
    (``__getitem__``, ``get``, ``keys``, ``values``, ``items``,
    ``__len__``, ``__iter__``) record a read dependency. Each mutation
    stores a ``DictMutation`` describing it.

    Args:
        init_value: Initial dictionary contents. Defaults to an empty
            dictionary.

    """

    _last_mutation: DictMutation | None

    def __init__(self, init_value: dict[K, V] | None = None) -> None:
        super().__init__(init_value if init_value is not None else {})
        self._last_mutation = None

    @SignalBase._get_event
    def __getitem__(self, key: K):
        return self._value.__getitem__(key)

    @SignalBase._change_event
    def __setitem__(self, key: K, value: V):
        self._value.__setitem__(key, value)
        self._last_mutation = DictMutation(op="set", key=key, value=value)  # type: ignore[arg-type]

    @SignalBase._change_event
    def __delitem__(self, key: K):
        val = self._value[key]
        self._value.__delitem__(key)
        self._last_mutation = DictMutation(op="delete", key=key, value=val)  # type: ignore[arg-type]

    @SignalBase._change_event
    def pop(self, key: K):
        """Remove ``key`` and return its value, notifying consumers.

        Args:
            key: Key to remove.

        Returns:
            The removed value.

        """
        val = self._value.pop(key)
        self._last_mutation = DictMutation(op="pop", key=key, value=val)  # type: ignore[arg-type]
        return val

    @SignalBase._change_event
    def clear(self):
        """Remove all entries, notifying consumers."""
        self._value.clear()
        self._last_mutation = DictMutation(op="clear", key=None, value=None)

    @SignalBase._get_event
    def __len__(self):
        return len(self._value)

    @SignalBase._get_event
    def __iter__(self):
        return iter(self._value)

    @SignalBase._get_event
    def get(self, key: K, default: Any = None):
        """Return the value for ``key``, recording a read dependency.

        Args:
            key: Key to look up.
            default: Value returned when ``key`` is absent.

        Returns:
            The mapped value or ``default``.

        """
        return self._value.get(key, default)

    @SignalBase._get_event
    def keys(self):
        """Return the dictionary keys, recording a read dependency."""
        return self._value.keys()

    @SignalBase._get_event
    def values(self):
        """Return the dictionary values, recording a read dependency."""
        return self._value.values()

    @SignalBase._get_event
    def items(self):
        """Return the dictionary items, recording a read dependency."""
        return self._value.items()
