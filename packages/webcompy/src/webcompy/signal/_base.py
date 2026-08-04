from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Generic, ParamSpec, TypeVar, cast, final

from webcompy.signal._graph import (
    SignalEdge,
    SignalNode,
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


class CallbackConsumerNode(SignalNode, _CallbackMixin):
    _callback: Callable[[Any], Any]
    _is_before: bool
    _is_async: bool
    _producer: SignalBase[Any]
    _last_notified_value: Any

    def __init__(
        self,
        callback: Callable[[Any], Any],
        producer: SignalBase[Any],
        is_before: bool = False,
    ) -> None:
        super().__init__()
        self._callback = callback
        self._is_before = is_before
        self._is_async = iscoroutinefunction(callback)
        self._producer = producer
        self.consumer_is_always_live = True
        self._last_notified_value = None
        if not is_before:
            from webcompy.signal._computed import Computed

            if isinstance(producer, Computed):
                producer_update_value_version(producer)
                self._last_notified_value = producer._value
        producer_add_live_consumer(producer, self)

    def producer_must_recompute(self) -> bool:
        return self.dirty

    def producer_recompute_value(self) -> None:
        self.dirty = False

    def _dispatch(self) -> None:
        if self._is_before:
            return
        from webcompy.signal._computed import Computed

        producer_update_value_version(self._producer)
        self.dirty = False
        if isinstance(self._producer, Computed):
            current = self._producer._value
            if current is self._last_notified_value or current == self._last_notified_value:
                return
            self._last_notified_value = current
        if self._is_async:
            from webcompy.aio._aio import _resolve_async_callback

            _resolve_async_callback(self._callback, self._producer._value)
        else:
            self._callback(self._producer._value)

    def notify(self, value: Any) -> None:
        self._callback(value)


class SignalBase(SignalNode, Generic[V]):
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
            instance = cast("SignalBase[V]", args[0])
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
            instance = cast("SignalBase[V]", args[0])
            producer_accessed(instance)
            return reactive_obj_method(*args, **kwargs)

        return method


def _notify_before_callbacks(producer: SignalNode, value: Any) -> None:
    edges: list[SignalEdge] = []
    edge = producer.consumers
    while edge is not None:
        if edge.active and isinstance(edge.consumer, CallbackConsumerNode) and edge.consumer._is_before:
            edges.append(edge)
        edge = edge.next_consumer
    for edge in edges:
        if not edge.active:
            continue
        cast("CallbackConsumerNode", edge.consumer).notify(value)


class Signal(SignalBase[V]):
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
