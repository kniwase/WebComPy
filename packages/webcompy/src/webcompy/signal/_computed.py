from collections.abc import Callable
from typing import Any, TypeVar

from webcompy.signal._base import SignalBase
from webcompy.signal._composable import _validate_factory
from webcompy.signal._container import SignalReceivable
from webcompy.signal._graph import (
    _SENTINEL,
    consumer_after_computation,
    consumer_before_computation,
    consumer_poll_producers_for_change,
    producer_accessed,
    producer_update_value_version,
)

V = TypeVar("V")
T = TypeVar("T")


class Computed(SignalBase[V]):
    def __init__(
        self,
        func: Callable[[], V],
    ) -> None:
        self.__calc = func
        self._value: Any = _SENTINEL
        super().__init__(_SENTINEL)  # type: ignore[arg-type]
        prev_consumer = consumer_before_computation(self)
        try:
            self._value = self.__calc()
        finally:
            consumer_after_computation(self, prev_consumer)
        self.last_clean_epoch = 0
        self._mark_producer_versions()

    def _mark_producer_versions(self) -> None:
        edge = self.producers
        while edge is not None:
            edge.last_read_version = edge.producer.version
            edge = edge.next_producer

    def producer_must_recompute(self) -> bool:
        if self.dirty:
            return True
        if self._value is _SENTINEL:
            return True
        return consumer_poll_producers_for_change(self)

    def producer_recompute_value(self) -> None:
        prev_consumer = consumer_before_computation(self)
        old_value = self._value
        try:
            new_value = self.__calc()
        finally:
            consumer_after_computation(self, prev_consumer)
        self._mark_producer_versions()
        if (
            old_value is not _SENTINEL and not (new_value is old_value or new_value == old_value)
        ) or old_value is _SENTINEL:
            self.version += 1
        self._value = new_value

    @property
    def value(self) -> V:
        producer_update_value_version(self)
        producer_accessed(self)
        return self._value


class _OwnedComputed(Computed[V]):
    """A ``Computed`` created by the framework (template binder).

    Owning elements (``SwitchElement``, ``Component`` root, template-bound
    elements) register ``_OwnedComputed`` instances as signal members so
    teardown destroys them. Computeds and Signals supplied by the caller
    are never instances of this type and must not be claimed as owned.
    """


def use_computed(factory: Callable[[], T]) -> Computed[T]:
    """Create a reactive Computed value.

    ``use_computed()`` accepts a zero-argument factory callable and returns
    a ``Computed[T]``.  Computed values are not included in the SSR transfer
    payload and always recompute from their source signals on the client.

    Args:
        factory: A zero-argument factory callable.

    Returns:
        A ``Computed[T]`` whose value tracks the factory result.

    Raises:
        TypeError: If ``factory`` is not callable.

    """
    if not callable(factory):
        raise TypeError(f"use_computed() requires a zero-argument factory callable, got {type(factory).__name__}")
    _validate_factory(factory)
    return Computed(factory)


def computed_property(method: Callable[[Any], V]) -> Computed[V]:
    name = method.__name__

    def getter(instance: Any) -> Computed[V]:
        if name not in instance.__dict__:
            _computed = Computed(lambda: method(instance))
            if isinstance(instance, SignalReceivable):
                instance.__set_signal_member__(name, _computed)
            instance.__dict__[name] = _computed
        return instance.__dict__[name]

    return property(getter)  # type: ignore
