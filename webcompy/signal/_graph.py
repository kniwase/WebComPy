from __future__ import annotations

_active_consumer: SignalNode | None = None
_in_notification_phase: bool = False
_epoch: int = 0


class SignalEdge:
    __slots__ = (
        "consumer",
        "last_read_version",
        "next_consumer",
        "next_producer",
        "prev_consumer",
        "producer",
    )

    def __init__(
        self,
        producer: SignalNode,
        consumer: SignalNode,
    ) -> None:
        self.producer = producer
        self.consumer = consumer
        self.last_read_version: int = producer.version
        self.prev_consumer: SignalEdge | None = None
        self.next_consumer: SignalEdge | None = None
        self.next_producer: SignalEdge | None = None


class SignalNode:
    version: int
    last_clean_epoch: int
    dirty: bool
    recomputing: bool
    producers: SignalEdge | None
    producers_tail: SignalEdge | None
    consumers: SignalEdge | None
    consumers_tail: SignalEdge | None
    consumer_is_always_live: bool

    def __init__(self) -> None:
        self.version = 0
        self.last_clean_epoch = _epoch
        self.dirty = False
        self.recomputing = False
        self.producers = None
        self.producers_tail = None
        self.consumers = None
        self.consumers_tail = None
        self.consumer_is_always_live = False

    def producer_must_recompute(self) -> bool:
        return self.dirty or self._value is _SENTINEL  # type: ignore[attr-defined]

    def producer_recompute_value(self) -> None:
        raise NotImplementedError


class _CallbackMixin:
    def _on_marked_dirty(self) -> None:
        raise NotImplementedError


_SENTINEL = object()


def set_active_consumer(consumer: SignalNode | None) -> SignalNode | None:
    global _active_consumer
    prev = _active_consumer
    _active_consumer = consumer
    return prev


def get_active_consumer() -> SignalNode | None:
    return _active_consumer


def producer_accessed(producer: SignalNode) -> None:
    global _active_consumer
    if _active_consumer is None:
        return
    consumer = _active_consumer
    edge = _find_consumer_edge(producer, consumer)
    if edge is not None:
        edge.last_read_version = producer.version
    else:
        edge = SignalEdge(producer, consumer)
        _append_producer_edge(consumer, edge)
        _append_consumer_edge(producer, edge)
        if _is_valid_link(edge):
            _track_live_consumer(edge)


def producer_notify_consumers(producer: SignalNode) -> None:
    global _in_notification_phase
    _in_notification_phase = True
    try:
        consumers_to_notify: list[SignalNode] = []
        edge = producer.consumers
        while edge is not None:
            consumer = edge.consumer
            if not consumer.dirty:
                consumers_to_notify.append(consumer)
            edge = edge.next_consumer
        for consumer in consumers_to_notify:
            if not consumer.dirty:
                consumer.dirty = True
                consumer_mark_dirty(consumer)
    finally:
        _in_notification_phase = False


def producer_update_value_version(producer: SignalNode) -> None:
    if _epoch == producer.last_clean_epoch:
        return
    if not producer.producer_must_recompute():
        producer.last_clean_epoch = _epoch
        return
    if producer.recomputing:
        return
    producer.recomputing = True
    try:
        producer.producer_recompute_value()
        producer.last_clean_epoch = _epoch
    finally:
        producer.recomputing = False


def producer_mark_clean(producer: SignalNode) -> None:
    producer.dirty = False
    producer.last_clean_epoch = _epoch


def consumer_mark_dirty(consumer: SignalNode) -> None:
    producer_notify_consumers(consumer)
    if isinstance(consumer, _CallbackMixin):
        consumer._on_marked_dirty()


def consumer_poll_producers_for_change(consumer: SignalNode) -> bool:
    edge = consumer.producers
    while edge is not None:
        producer = edge.producer
        if edge.last_read_version < producer.version or producer.dirty:
            producer_update_value_version(producer)
            if edge.last_read_version < producer.version:
                return True
        edge = edge.next_producer
    return False


def consumer_before_computation(consumer: SignalNode) -> SignalNode | None:
    global _active_consumer
    prev = _active_consumer
    _active_consumer = consumer
    return prev


def consumer_after_computation(
    consumer: SignalNode,
    prev_consumer: SignalNode | None,
) -> None:
    global _active_consumer
    _active_consumer = prev_consumer
    edge = consumer.producers
    while edge is not None:
        next_edge = edge.next_producer
        if not _is_valid_link(edge):
            _detach_producer_edge(consumer, edge)
            _detach_consumer_edge(edge.producer, edge)
        edge = next_edge


def finalize_consumer_after_computation(consumer: SignalNode) -> None:
    pass


def consumer_destroy(consumer: SignalNode) -> None:
    edge = consumer.producers
    while edge is not None:
        next_edge = edge.next_producer
        producer = edge.producer
        _detach_consumer_edge(producer, edge)
        _detach_producer_edge(consumer, edge)
        edge = next_edge
    consumer.producers = None
    consumer.producers_tail = None
    if consumer_is_live(consumer):
        edge = consumer.consumers
        while edge is not None:
            next_edge = edge.next_consumer
            _untrack_live_consumer(edge)
            _detach_consumer_edge(consumer, edge)
            edge = next_edge
        consumer.consumers = None
        consumer.consumers_tail = None


def producer_add_live_consumer(
    producer: SignalNode,
    consumer: SignalNode,
) -> SignalEdge:
    edge = SignalEdge(producer, consumer)
    _append_producer_edge(consumer, edge)
    _append_consumer_edge(producer, edge)
    producer.version += 1
    edge.last_read_version = producer.version
    _track_live_consumer(edge)
    return edge


def producer_remove_live_consumer_link(edge: SignalEdge) -> None:
    _untrack_live_consumer(edge)
    _detach_consumer_edge(edge.producer, edge)
    _detach_producer_edge(edge.consumer, edge)


def consumer_is_live(consumer: SignalNode) -> bool:
    return consumer.consumer_is_always_live


def _find_consumer_edge(
    producer: SignalNode,
    consumer: SignalNode,
) -> SignalEdge | None:
    edge = producer.consumers
    while edge is not None:
        if edge.consumer is consumer:
            return edge
        edge = edge.next_consumer
    return None


def _append_producer_edge(consumer: SignalNode, edge: SignalEdge) -> None:
    edge.prev_consumer = consumer.producers_tail
    if consumer.producers_tail is not None:
        consumer.producers_tail.next_producer = edge
    else:
        consumer.producers = edge
    consumer.producers_tail = edge


def _append_consumer_edge(producer: SignalNode, edge: SignalEdge) -> None:
    edge.next_consumer = producer.consumers
    if producer.consumers is not None:
        producer.consumers.prev_consumer = edge
    producer.consumers = edge
    if producer.consumers_tail is None:
        producer.consumers_tail = edge


def _detach_producer_edge(consumer: SignalNode, edge: SignalEdge) -> None:
    if edge.prev_consumer is not None:
        edge.prev_consumer.next_producer = edge.next_producer
    elif consumer.producers is edge:
        consumer.producers = edge.next_producer
    if edge.next_producer is not None:
        edge.next_producer.prev_consumer = edge.prev_consumer
    if consumer.producers_tail is edge:
        consumer.producers_tail = edge.prev_consumer
    edge.prev_consumer = None
    edge.next_producer = None


def _detach_consumer_edge(producer: SignalNode, edge: SignalEdge) -> None:
    if edge.prev_consumer is not None:
        edge.prev_consumer.next_consumer = edge.next_consumer
    elif producer.consumers is edge:
        producer.consumers = edge.next_consumer
    if edge.next_consumer is not None:
        edge.next_consumer.prev_consumer = edge.prev_consumer
    if producer.consumers_tail is edge:
        producer.consumers_tail = edge.prev_consumer
    edge.prev_consumer = None
    edge.next_consumer = None


def _is_valid_link(edge: SignalEdge) -> bool:
    consumer = edge.consumer
    if not consumer_is_live(consumer):
        return edge.last_read_version >= edge.producer.version
    return True


def _track_live_consumer(edge: SignalEdge) -> None:
    pass


def _untrack_live_consumer(edge: SignalEdge) -> None:
    pass


def reset_graph_state() -> None:
    global _active_consumer, _in_notification_phase, _epoch
    _active_consumer = None
    _in_notification_phase = False
    _epoch = 0


def increment_epoch() -> int:
    global _epoch
    _epoch += 1
    return _epoch
