from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, Generic, TypeVar, cast, final

from typing_extensions import ParamSpec

from webcompy.reactive._graph import (
    ReactiveNode,
    _CallbackMixin,
    increment_epoch,
    producer_accessed,
    producer_add_live_consumer,
    producer_notify_consumers,
    producer_update_value_version,
)

V = TypeVar("V")
A = ParamSpec("A")
T = TypeVar("T")


class CallbackConsumerNode(ReactiveNode, _CallbackMixin):
    _callback: Callable[[Any], Any]
    _is_before: bool
    _producer: ReactiveNode

    def __init__(
        self,
        callback: Callable[[Any], Any],
        producer: ReactiveNode,
        is_before: bool = False,
    ) -> None:
        super().__init__()
        self._callback = callback
        self._is_before = is_before
        self._producer = producer
        self.consumer_is_always_live = True
        producer_add_live_consumer(producer, self)

    def producer_must_recompute(self) -> bool:
        return self.dirty

    def producer_recompute_value(self) -> None:
        self.dirty = False

    def _on_marked_dirty(self) -> None:
        if self._is_before:
            return
        from webcompy.reactive._computed import Computed

        old_version = self._producer.version
        producer_update_value_version(self._producer)
        self.dirty = False
        if isinstance(self._producer, Computed) and self._producer.version <= old_version:
            return
        self._callback(self._producer._value)

    def notify(self, value: Any) -> None:
        self._callback(value)


class ReactiveBase(ReactiveNode, Generic[V]):
    _value: V

    def __init__(self, init_value: V) -> None:
        super().__init__()
        self._value = init_value

    @property
    @abstractmethod
    def value(self) -> V: ...

    @final
    def on_after_updating(self, func: Callable[[V], Any]) -> CallbackConsumerNode:
        consumer = CallbackConsumerNode(func, self, is_before=False)
        return consumer

    @final
    def on_before_updating(self, func: Callable[[V], Any]) -> CallbackConsumerNode:
        consumer = CallbackConsumerNode(func, self, is_before=True)
        return consumer

    @final
    @staticmethod
    def _change_event(reactive_obj_method: Callable[A, V]) -> Callable[A, V]:
        @wraps(reactive_obj_method)
        def method(*args: A.args, **kwargs: A.kwargs) -> V:
            instance = cast("ReactiveBase[V]", args[0])
            _notify_before_callbacks(instance, instance._value)
            increment_epoch()
            ret = reactive_obj_method(*args, **kwargs)
            instance.version += 1
            producer_notify_consumers(instance)
            return ret

        return method

    @final
    @staticmethod
    def _get_event(reactive_obj_method: Callable[A, V]) -> Callable[A, V]:
        @wraps(reactive_obj_method)
        def method(*args: A.args, **kwargs: A.kwargs) -> V:
            instance = cast("ReactiveBase[V]", args[0])
            producer_accessed(instance)
            return reactive_obj_method(*args, **kwargs)

        return method


def _find_callback_consumer_nodes(producer: ReactiveNode) -> list[CallbackConsumerNode]:
    nodes: list[CallbackConsumerNode] = []
    edge = producer.consumers
    while edge is not None:
        consumer = edge.consumer
        if isinstance(consumer, CallbackConsumerNode):
            nodes.append(consumer)
        edge = edge.next_consumer
    return nodes


def _notify_before_callbacks(producer: ReactiveNode, value: Any) -> None:
    for cb in _find_callback_consumer_nodes(producer):
        if cb._is_before:
            cb.notify(value)


def _notify_after_callbacks(producer: ReactiveNode, value: Any) -> None:
    for cb in _find_callback_consumer_nodes(producer):
        if not cb._is_before:
            cb.notify(value)


class Reactive(ReactiveBase[V]):
    @final
    def set_value(self, new_value: V) -> V:
        old_value = self._value
        if old_value is new_value or old_value == new_value:
            return self._value
        _notify_before_callbacks(self, old_value)
        increment_epoch()
        self._value = new_value
        self.version += 1
        producer_notify_consumers(self)
        return self._value

    @final
    @property
    def value(self) -> V:
        producer_accessed(self)
        return self._value

    @final
    @value.setter
    def value(self, new_value: V):
        self.set_value(new_value)
