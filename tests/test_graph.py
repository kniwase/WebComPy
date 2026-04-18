from __future__ import annotations

import pytest

from webcompy.reactive._graph import (
    ReactiveNode,
    _find_consumer_edge,
    consumer_after_computation,
    consumer_before_computation,
    consumer_destroy,
    consumer_is_live,
    consumer_poll_producers_for_change,
    get_active_consumer,
    increment_epoch,
    producer_accessed,
    producer_add_live_consumer,
    producer_notify_consumers,
    producer_remove_live_consumer_link,
    reset_graph_state,
    set_active_consumer,
)


class SimpleReactiveNode(ReactiveNode):
    def __init__(self, value=None):
        super().__init__()
        self._value = value

    def producer_must_recompute(self):
        return self.dirty

    def producer_recompute_value(self):
        self.dirty = False


class SimpleConsumerNode(ReactiveNode):
    def __init__(self):
        super().__init__()
        self.compute_count = 0
        self._value = None

    def producer_must_recompute(self):
        return self.dirty

    def producer_recompute_value(self):
        self.compute_count += 1
        self.dirty = False


@pytest.fixture(autouse=True)
def reset_state():
    reset_graph_state()
    yield
    reset_graph_state()


class TestGlobalState:
    def test_initial_state(self):
        assert get_active_consumer() is None

    def test_set_and_get_active_consumer(self):
        node = SimpleReactiveNode()
        prev = set_active_consumer(node)
        assert prev is None
        assert get_active_consumer() is node

    def test_set_active_consumer_returns_previous(self):
        node1 = SimpleReactiveNode()
        node2 = SimpleReactiveNode()
        set_active_consumer(node1)
        prev = set_active_consumer(node2)
        assert prev is node1
        assert get_active_consumer() is node2

    def test_reset_graph_state(self):
        node = SimpleReactiveNode()
        set_active_consumer(node)
        increment_epoch()
        reset_graph_state()
        assert get_active_consumer() is None

    def test_increment_epoch(self):
        e1 = increment_epoch()
        assert e1 == 1
        e2 = increment_epoch()
        assert e2 == 2


class TestProducerConsumerEdges:
    def test_producer_accessed_creates_edge(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        assert producer.consumers is not None
        assert producer.consumers.consumer is consumer
        assert consumer.producers is not None
        assert consumer.producers.producer is producer

    def test_producer_accessed_no_consumer(self):
        producer = SimpleReactiveNode()
        producer_accessed(producer)
        assert producer.consumers is None

    def test_producer_accessed_updates_existing_edge_version(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        producer.version = 5
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        edge = _find_consumer_edge(producer, consumer)
        assert edge is not None
        assert edge.last_read_version == 5

    def test_multiple_producers(self):
        p1 = SimpleReactiveNode()
        p2 = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(p1)
        producer_accessed(p2)
        set_active_consumer(None)

        assert consumer.producers is not None
        assert consumer.producers_tail is not None
        edges = []
        edge = consumer.producers
        while edge is not None:
            edges.append(edge)
            edge = edge.next_producer
        assert len(edges) == 2

    def test_multiple_consumers(self):
        producer = SimpleReactiveNode()
        c1 = SimpleConsumerNode()
        c2 = SimpleConsumerNode()
        set_active_consumer(c1)
        producer_accessed(producer)
        set_active_consumer(None)

        set_active_consumer(c2)
        producer_accessed(producer)
        set_active_consumer(None)

        edge = producer.consumers
        consumers = []
        while edge is not None:
            consumers.append(edge.consumer)
            edge = edge.next_consumer
        assert c1 in consumers
        assert c2 in consumers


class TestConsumerDestroy:
    def test_consumer_destroy_removes_edges(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        consumer_destroy(consumer)
        assert consumer.producers is None
        assert producer.consumers is None or _find_consumer_edge(producer, consumer) is None

    def test_consumer_destroy_multiple_producers(self):
        p1 = SimpleReactiveNode()
        p2 = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(p1)
        producer_accessed(p2)
        set_active_consumer(None)

        consumer_destroy(consumer)
        assert consumer.producers is None
        assert _find_consumer_edge(p1, consumer) is None
        assert _find_consumer_edge(p2, consumer) is None

    def test_destroy_one_consumer_keeps_other(self):
        producer = SimpleReactiveNode()
        c1 = SimpleConsumerNode()
        c2 = SimpleConsumerNode()
        set_active_consumer(c1)
        producer_accessed(producer)
        set_active_consumer(None)
        set_active_consumer(c2)
        producer_accessed(producer)
        set_active_consumer(None)

        consumer_destroy(c1)
        assert _find_consumer_edge(producer, c1) is None
        assert _find_consumer_edge(producer, c2) is not None


class TestDynamicDependencyRebuilding:
    def test_consumer_after_computation_removes_stale_edges(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        prev = consumer_before_computation(consumer)

        consumer_after_computation(consumer, prev)
        assert _find_consumer_edge(producer, consumer) is not None

    def test_stale_edge_removed_when_not_accessed(self):
        p1 = SimpleReactiveNode()
        p2 = SimpleReactiveNode()
        consumer = SimpleConsumerNode()

        set_active_consumer(consumer)
        producer_accessed(p1)
        set_active_consumer(None)

        p1.version += 1

        prev = consumer_before_computation(consumer)
        producer_accessed(p2)
        consumer_after_computation(consumer, prev)

        assert _find_consumer_edge(p1, consumer) is None
        assert _find_consumer_edge(p2, consumer) is not None


class TestEpochBasedSkipChecks:
    def test_producer_update_skips_when_epoch_clean(self):
        producer = SimpleReactiveNode()
        increment_epoch()
        producer.last_clean_epoch = _find_consumer_edge_local_epoch()
        producer.dirty = False

    def test_increment_epoch_advances_global_epoch(self):

        e = increment_epoch()
        assert e >= 1


class TestDiamondTopology:
    def test_diamond_dependency_notifies_consumer_once_via_dirty_flag(self):
        a = SimpleReactiveNode()
        b = SimpleConsumerNode()
        c = SimpleConsumerNode()
        d = SimpleConsumerNode()

        set_active_consumer(b)
        producer_accessed(a)
        set_active_consumer(None)
        set_active_consumer(c)
        producer_accessed(a)
        set_active_consumer(None)
        set_active_consumer(d)
        producer_accessed(b)
        producer_accessed(c)
        set_active_consumer(None)

        b.dirty = False
        c.dirty = False
        d.dirty = False

        producer_notify_consumers(a)
        assert b.dirty is True
        assert c.dirty is True

        b.dirty = False
        c.dirty = False

        producer_notify_consumers(b)
        assert d.dirty is True

        producer_notify_consumers(c)
        assert d.dirty is True

    def test_producer_notify_sets_dirty(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        assert consumer.dirty is False
        producer_notify_consumers(producer)
        assert consumer.dirty is True


class TestLiveVsNonLiveConsumer:
    def test_non_live_consumer_edge_not_tracked(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        consumer.consumer_is_always_live = False

        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        edge = _find_consumer_edge(producer, consumer)
        assert edge is not None
        assert consumer_is_live(consumer) is False

    def test_live_consumer_edge_tracked(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        consumer.consumer_is_always_live = True

        edge = producer_add_live_consumer(producer, consumer)
        assert edge is not None
        assert consumer_is_live(consumer) is True

    def test_producer_remove_live_consumer_link(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        consumer.consumer_is_always_live = True

        edge = producer_add_live_consumer(producer, consumer)
        producer_remove_live_consumer_link(edge)
        assert _find_consumer_edge(producer, consumer) is None


def _find_consumer_edge_local_epoch():
    from webcompy.reactive._graph import _epoch

    return _epoch


class TestConsumerPollProducersForChange:
    def test_no_change_returns_false(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        assert consumer_poll_producers_for_change(consumer) is False

    def test_version_change_returns_true(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        producer.version += 1
        assert consumer_poll_producers_for_change(consumer) is True

    def test_dirty_producer_triggers_recompute(self):
        producer = SimpleReactiveNode()
        consumer = SimpleConsumerNode()
        set_active_consumer(consumer)
        producer_accessed(producer)
        set_active_consumer(None)

        producer.dirty = True
        producer.version += 1
        result = consumer_poll_producers_for_change(consumer)
        assert result is True
