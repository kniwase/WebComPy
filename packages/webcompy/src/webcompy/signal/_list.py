"""Reactive list wrapper: ``ListMutation`` and ``ReactiveList``."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, TypeVar, cast, overload

from webcompy.signal._base import Signal, SignalBase

V = TypeVar("V")


@dataclass
class ListMutation:
    """Record of the most recent mutating operation on a ``ReactiveList``.

    Args:
        op: Operation name (e.g. ``"append"``, ``"pop"``, ``"sort"``).
        index: Index the operation targeted, when applicable.
        value: Value involved in the mutation, when applicable.

    Attributes:
        op: Operation name (e.g. ``"append"``, ``"pop"``, ``"sort"``).
        index: Index the operation targeted, when applicable.
        value: Value involved in the mutation, when applicable.

    """

    op: str
    index: int | None
    value: Any


class ReactiveList(Signal[list[V]]):
    """Reactive wrapper around a ``list`` behaving like ``Signal[list]``.

    Mutation methods (``append``, ``extend``, ``insert``, ``pop``,
    ``remove``, ``sort``, ``reverse``, ``clear``, ``__setitem__``)
    propagate change notifications to consumers; read methods
    (``__getitem__``, ``__len__``, ``__iter__``, ``index``, ``count``)
    record a read dependency. Each mutation stores a ``ListMutation``
    describing it.

    Args:
        init_value: Initial list contents.

    """

    _last_mutation: ListMutation | None

    def __init__(self, init_value: list[V]) -> None:
        super().__init__(init_value)
        self._last_mutation = None

    @SignalBase._change_event
    def append(self, value: V):
        """Append ``value`` to the end, notifying consumers.

        Args:
            value: Item to append.

        """
        self._value.append(value)
        self._last_mutation = ListMutation(op="append", index=len(self._value) - 1, value=value)

    @SignalBase._change_event
    def extend(self, value: Iterable[V]):
        """Extend the list with an iterable, notifying consumers.

        Args:
            value: Iterable of items to append.

        """
        start_index = len(self._value)
        items = list(value)
        self._value.extend(items)
        self._last_mutation = ListMutation(op="extend", index=start_index, value=items)

    @SignalBase._change_event
    def pop(self, index: int | None = None):
        """Remove and return the item at ``index``, notifying consumers.

        Args:
            index: Position to remove; the last item when omitted.

        Returns:
            The removed item.

        """
        actual_index = len(self._value) - 1 if index is None else index
        popped = self._value.pop() if index is None else self._value.pop(index)
        self._last_mutation = ListMutation(op="pop", index=actual_index, value=popped)
        return popped

    @SignalBase._change_event
    def insert(self, index: int, value: V):
        """Insert ``value`` before ``index``, notifying consumers.

        Args:
            index: Position at which to insert.
            value: Item to insert.

        """
        self._value.insert(index, value)
        self._last_mutation = ListMutation(op="insert", index=index, value=value)

    @SignalBase._change_event
    def sort(self, key: Callable[[V], Any] = lambda it: it, reverse: bool = False):
        """Sort the list in place, notifying consumers.

        Args:
            key: Key function applied to each item for comparison.
            reverse: Whether to sort in descending order.

        """
        self._value.sort(key=key, reverse=reverse)
        self._last_mutation = ListMutation(op="sort", index=None, value=None)

    @SignalBase._get_event
    def index(self, value: V):
        """Return the position of ``value``, recording a read dependency.

        Args:
            value: Item to locate.

        Returns:
            The zero-based index of the first match.

        """
        return self._value.index(value)

    @SignalBase._get_event
    def count(self, value: V):
        """Return how many times ``value`` occurs, recording a read dependency.

        Args:
            value: Item to count.

        Returns:
            The number of occurrences.

        """
        return self._value.count(value)

    @SignalBase._change_event
    def remove(self, value: V):
        """Remove the first occurrence of ``value``, notifying consumers.

        Args:
            value: Item to remove.

        """
        idx = self._value.index(value)
        self._value.remove(value)
        self._last_mutation = ListMutation(op="remove", index=idx, value=value)

    @SignalBase._change_event
    def clear(self):
        """Remove all items, notifying consumers."""
        self._value.clear()
        self._last_mutation = ListMutation(op="clear", index=None, value=None)

    @SignalBase._change_event
    def reverse(self):
        """Reverse the order of items in place, notifying consumers."""
        self._value.reverse()
        self._last_mutation = ListMutation(op="reverse", index=None, value=None)

    @overload
    def __getitem__(self, idx: int) -> V: ...

    @overload
    def __getitem__(self, idx: slice) -> list[V]: ...

    @SignalBase._get_event
    def __getitem__(self, idx: int | slice):
        return self._value.__getitem__(idx)

    @overload
    def __setitem__(self, idx: int, value: V) -> None: ...

    @overload
    def __setitem__(self, idx: slice, value: Iterable[V]) -> None: ...

    @SignalBase._change_event
    def __setitem__(self, idx: int | slice, value: V | Iterable[V]):
        if isinstance(idx, int):
            self._value.__setitem__(idx, cast("V", value))
            self._last_mutation = ListMutation(op="setitem", index=idx, value=value)
        else:
            self._value.__setitem__(idx, cast("Iterable[V]", value))
            self._last_mutation = ListMutation(op="setitem", index=None, value=None)

    @SignalBase._get_event
    def __len__(self):
        return len(self._value)

    @SignalBase._get_event
    def __iter__(self):
        return iter(self._value)
