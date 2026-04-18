from __future__ import annotations

import warnings
from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, Generic, TypeVar, cast, final

from typing_extensions import ParamSpec

from webcompy.reactive._graph import (
    ReactiveNode,
    _CallbackMixin,
    consumer_destroy,
    increment_epoch,
    producer_accessed,
    producer_add_live_consumer,
    producer_notify_consumers,
    set_active_consumer,
)

V = TypeVar("V")
A = ParamSpec("A")
T = TypeVar("T")

_callback_id_counter: int = 0
_callback_registry: dict[int, CallbackConsumerNode] = {}


class CallbackConsumerNode(ReactiveNode, _CallbackMixin):
    _callback_id: int
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
        global _callback_id_counter
        _callback_id_counter += 1
        self._callback_id = _callback_id_counter
        self._callback = callback
        self._is_before = is_before
        self._producer = producer
        self.consumer_is_always_live = True
        producer_add_live_consumer(producer, self)
        _callback_registry[self._callback_id] = self

    def producer_must_recompute(self) -> bool:
        return self.dirty

    def producer_recompute_value(self) -> None:
        self.dirty = False

    def _on_marked_dirty(self) -> None:
        if self._is_before:
            return
        from webcompy.reactive._computed import Computed
        from webcompy.reactive._graph import producer_update_value_version

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
    def on_after_updating(self, func: Callable[[V], Any]) -> int:
        consumer = CallbackConsumerNode(func, self, is_before=False)
        return consumer._callback_id

    @final
    def on_before_updating(self, func: Callable[[V], Any]) -> int:
        consumer = CallbackConsumerNode(func, self, is_before=True)
        return consumer._callback_id

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


def _find_callback_consumer_by_id(producer: ReactiveNode, callback_id: int) -> CallbackConsumerNode | None:
    edge = producer.consumers
    while edge is not None:
        consumer = edge.consumer
        if isinstance(consumer, CallbackConsumerNode) and consumer._callback_id == callback_id:
            return consumer
        edge = edge.next_consumer
    return None


def remove_callback(producer: ReactiveNode, callback_id: int) -> None:
    cb = _callback_registry.pop(callback_id, None)
    if cb is not None:
        consumer_destroy(cb)


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


def _make_singleton(cls: type[T]) -> T:
    instance = cls()
    cls.__class_getitem__ = classmethod(lambda c, *a, **k: c)  # type: ignore[attr-defined]
    return instance


class _ReactiveStoreShell:
    _deprecated_warned: bool

    def __init__(self) -> None:
        self._deprecated_warned = False

    def _warn_deprecated(self) -> None:
        if not self._deprecated_warned:
            warnings.warn(
                "ReactiveStore is deprecated. Use the reactive graph API directly.",
                DeprecationWarning,
                stacklevel=3,
            )
            self._deprecated_warned = True

    def add_reactive_instance(self, reactive: ReactiveBase[Any]) -> None:
        self._warn_deprecated()

    def add_on_after_updating(self, reactive: ReactiveBase[Any], func: Callable[[Any], Any]) -> int:
        self._warn_deprecated()
        return reactive.on_after_updating(func)

    def add_on_before_updating(self, reactive: ReactiveBase[Any], func: Callable[[Any], Any]) -> int:
        self._warn_deprecated()
        return reactive.on_before_updating(func)

    def callback_after_updating(self, instance: ReactiveBase[Any], value: Any) -> None:
        _notify_after_callbacks(instance, value)

    def callback_before_updating(self, instance: ReactiveBase[Any], value: Any) -> None:
        _notify_before_callbacks(instance, value)

    def register(self, reactive: ReactiveBase[Any]) -> None:
        producer_accessed(reactive)

    def detect_dependency(self, func: Callable[[], Any]) -> tuple[Any, list[ReactiveBase[Any]]]:
        self._warn_deprecated()
        consumer = ReactiveNode()
        prev = set_active_consumer(consumer)
        try:
            value = func()
        finally:
            set_active_consumer(prev)

        deps: list[ReactiveBase[Any]] = []
        seen: set[int] = set()
        edge = consumer.producers
        while edge is not None:
            producer = edge.producer
            if id(producer) not in seen:
                seen.add(id(producer))
                deps.append(producer)  # type: ignore[arg-type]
            edge = edge.next_producer

        consumer_destroy(consumer)

        return value, deps

    def remove_callback(self, callback_id: int) -> None:
        cb = _callback_registry.pop(callback_id, None)
        if cb is not None:
            consumer_destroy(cb)


ReactiveStore = _make_singleton(_ReactiveStoreShell)
