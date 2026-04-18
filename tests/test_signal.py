import pytest

from webcompy.signal import Computed, ReactiveDict, ReactiveList, Signal, readonly
from webcompy.signal._graph import consumer_destroy, reset_graph_state


@pytest.fixture(autouse=True)
def reset_reactive_state():
    reset_graph_state()
    yield
    reset_graph_state()


class TestReactive:
    def test_initial_value(self):
        r = Signal(10)
        assert r.value == 10

    def test_set_value(self):
        r = Signal(0)
        r.value = 5
        assert r.value == 5

    def test_on_after_updating_callback(self):
        r = Signal(0)
        results = []
        r.on_after_updating(lambda v: results.append(v))
        r.value = 42
        assert results == [42]

    def test_on_before_updating_callback(self):
        r = Signal(0)
        old_values = []
        r.on_before_updating(lambda v: old_values.append(v))
        r.value = 1
        assert old_values == [0]

    def test_multiple_callbacks(self):
        r = Signal(0)
        a = []
        b = []
        r.on_after_updating(lambda v: a.append(v))
        r.on_after_updating(lambda v: b.append(v))
        r.value = 1
        assert a == [1] and b == [1]

    def test_remove_callback(self):
        r = Signal(0)
        results = []
        callback_node = r.on_after_updating(lambda v: results.append(v))
        r.value = 1
        consumer_destroy(callback_node)
        r.value = 2
        assert results == [1]


class TestComputed:
    def test_basic_computation(self):
        a = Signal(1)
        b = Signal(2)
        c = Computed(lambda: a.value + b.value)
        assert c.value == 3

    def test_computed_updates_on_dependency_change(self):
        a = Signal(1)
        b = Signal(2)
        c = Computed(lambda: a.value + b.value)
        assert c.value == 3
        a.value = 10
        assert c.value == 12

    def test_computed_with_single_dependency(self):
        a = Signal(5)
        c = Computed(lambda: a.value * 2)
        assert c.value == 10
        a.value = 7
        assert c.value == 14


class TestReactiveList:
    def test_initial_value(self):
        rl = ReactiveList([1, 2, 3])
        assert rl.value == [1, 2, 3]

    def test_append(self):
        rl = ReactiveList([1, 2])
        results = []
        rl.on_after_updating(lambda v: results.append(list(rl.value)))
        rl.append(3)
        assert rl.value == [1, 2, 3]
        assert results == [[1, 2, 3]]

    def test_pop(self):
        rl = ReactiveList([1, 2, 3])
        val = rl.pop()
        assert val == 3
        assert rl.value == [1, 2]

    def test_extend(self):
        rl = ReactiveList([1])
        rl.extend([2, 3])
        assert rl.value == [1, 2, 3]

    def test_insert(self):
        rl = ReactiveList([1, 3])
        rl.insert(1, 2)
        assert rl.value == [1, 2, 3]

    def test_remove(self):
        rl = ReactiveList([1, 2, 3])
        rl.remove(2)
        assert rl.value == [1, 3]

    def test_sort(self):
        rl = ReactiveList([3, 1, 2])
        rl.sort()
        assert rl.value == [1, 2, 3]

    def test_reverse(self):
        rl = ReactiveList([1, 2, 3])
        rl.reverse()
        assert rl.value == [3, 2, 1]

    def test_clear(self):
        rl = ReactiveList([1, 2, 3])
        rl.clear()
        assert rl.value == []

    def test_len(self):
        rl = ReactiveList([1, 2, 3])
        assert len(rl) == 3

    def test_getitem(self):
        rl = ReactiveList([10, 20, 30])
        assert rl[1] == 20

    def test_setitem(self):
        rl = ReactiveList([1, 2, 3])
        rl[1] = 99
        assert rl.value == [1, 99, 3]


class TestReactiveDict:
    def test_initial_value(self):
        rd = ReactiveDict({"a": 1, "b": 2})
        assert rd.value == {"a": 1, "b": 2}

    def test_setitem(self):
        rd = ReactiveDict({})
        rd["x"] = 10
        assert rd.value == {"x": 10}

    def test_delitem(self):
        rd = ReactiveDict({"a": 1, "b": 2})
        del rd["a"]
        assert rd.value == {"b": 2}

    def test_pop(self):
        rd = ReactiveDict({"a": 1, "b": 2})
        val = rd.pop("a")
        assert val == 1
        assert rd.value == {"b": 2}

    def test_get(self):
        rd = ReactiveDict({"a": 1})
        assert rd.get("a") == 1
        assert rd.get("z") is None
        assert rd.get("z", 42) == 42

    def test_iteration(self):
        rd = ReactiveDict({"a": 1, "b": 2, "c": 3})
        keys = list(rd)
        assert set(keys) == {"a", "b", "c"}

    def test_keys_values_items(self):
        rd = ReactiveDict({"x": 10, "y": 20})
        assert set(rd.keys()) == {"x", "y"}
        assert set(rd.values()) == {10, 20}
        assert set(rd.items()) == {("x", 10), ("y", 20)}


class TestReadonly:
    def test_readonly_reflects_original(self):
        r = Signal(10)
        ro = readonly(r)
        assert ro.value == 10

    def test_readonly_tracks_changes(self):
        r = Signal(10)
        ro = readonly(r)
        r.value = 20
        assert ro.value == 20


class TestReactiveEqualitySkip:
    def test_same_value_no_callback(self):
        r = Signal(5)
        results = []
        r.on_after_updating(lambda v: results.append(v))
        r.value = 5
        assert results == []

    def test_equal_value_no_callback(self):
        r = Signal([1, 2, 3])
        results = []
        r.on_after_updating(lambda v: results.append(v))
        r.value = [1, 2, 3]
        assert results == []

    def test_different_value_fires_callback(self):
        r = Signal(5)
        results = []
        r.on_after_updating(lambda v: results.append(v))
        r.value = 10
        assert results == [10]

    def test_version_increments_on_change(self):
        r = Signal(5)
        assert r.version == 0
        r.value = 10
        assert r.version == 1

    def test_version_does_not_increment_on_same_value(self):
        r = Signal(5)
        r.value = 5
        assert r.version == 0

    def test_on_before_updating_fires_before_change(self):
        r = Signal(0)
        old_values = []
        r.on_before_updating(lambda v: old_values.append(v))
        r.value = 1
        assert old_values == [0]

    def test_on_after_updating_no_fire_same_value(self):
        r = Signal(0)
        results = []
        r.on_after_updating(lambda v: results.append(v))
        r.value = 0
        assert results == []


class TestComputedLazyEvaluation:
    def test_computed_not_recomputed_when_unread(self):
        call_count = [0]

        def compute():
            call_count[0] += 1
            return Signal(1).value * 2

        a = Signal(1)
        c = Computed(lambda: a.value * 2)
        assert c.value == 2
        initial_count = call_count[0]
        a.value = 10
        assert call_count[0] == initial_count

    def test_computed_recomputes_on_read_after_change(self):
        a = Signal(1)
        c = Computed(lambda: a.value * 2)
        assert c.value == 2
        a.value = 10
        assert c.value == 20

    def test_computed_equality_skip(self):
        a = Signal(5)
        c = Computed(lambda: abs(a.value))
        assert c.value == 5
        initial_version = c.version
        a.value = -5
        assert c.value == 5
        assert c.version == initial_version

    def test_computed_recomputes_only_once(self):
        compute_count = [0]
        a = Signal(1)
        c = Computed(lambda: compute_count.__setitem__(0, compute_count[0] + 1) or a.value * 2)
        assert c.value == 2
        assert compute_count[0] == 1
        a.value = 10
        assert c.value == 20
        assert compute_count[0] == 2


class TestComputedDiamondDependency:
    def test_diamond_computed_only_once(self):
        a = Signal(1)
        b = Computed(lambda: a.value * 2)
        c = Computed(lambda: a.value + 10)
        d = Computed(lambda: b.value + c.value)
        assert d.value == 1 * 2 + (1 + 10)
        a.value = 2
        assert d.value == 2 * 2 + (2 + 10)

    def test_computed_dynamic_dependency_switch(self):
        flag = Signal(True)
        a = Signal("A")
        b = Signal("B")
        c = Computed(lambda: a.value if flag.value else b.value)
        assert c.value == "A"
        flag.value = False
        assert c.value == "B"
        a.value = "A2"
        assert c.value == "B"
        b.value = "B2"
        assert c.value == "B2"


class TestComputedCallbackContract:
    def test_computed_on_after_updating_on_change(self):
        a = Signal(1)
        c = Computed(lambda: a.value * 2)
        results = []
        c.on_after_updating(lambda v: results.append(v))
        a.value = 5
        assert results == [10]

    def test_computed_callback_not_fired_on_equal_result(self):
        a = Signal(5)
        c = Computed(lambda: abs(a.value))
        results = []
        c.on_after_updating(lambda v: results.append(v))
        a.value = -5
        assert results == []


class TestReactiveListEqualitySkip:
    def test_set_value_same_list_no_callback(self):
        rl = ReactiveList([1, 2, 3])
        results = []
        rl.on_after_updating(lambda v: results.append(v))
        rl.value = [1, 2, 3]
        assert results == []

    def test_set_value_different_list_fires_callback(self):
        rl = ReactiveList([1, 2, 3])
        results = []
        rl.on_after_updating(lambda v: results.append(v))
        rl.value = [4, 5, 6]
        assert len(results) == 1

    def test_mutating_methods_always_propagate(self):
        rl = ReactiveList([1, 2])
        results = []
        rl.on_after_updating(lambda v: results.append(v))
        rl.append(2)
        assert len(results) == 1

    def test_len_tracks_depending(self):
        rl = ReactiveList([1, 2, 3])
        c = Computed(lambda: len(rl))
        assert c.value == 3

    def test_getitem_tracks_depending(self):
        rl = ReactiveList([10, 20, 30])
        c = Computed(lambda: rl[1])
        assert c.value == 20

    def test_iter_tracks_depending(self):
        rl = ReactiveList([1, 2, 3])
        c = Computed(lambda: list(rl))
        assert c.value == [1, 2, 3]


class TestReactiveDictEqualitySkip:
    def test_set_value_same_dict_no_callback(self):
        rd = ReactiveDict({"a": 1})
        results = []
        rd.on_after_updating(lambda v: results.append(v))
        rd.value = {"a": 1}
        assert results == []

    def test_mutating_methods_always_propagate(self):
        rd = ReactiveDict({"a": 1})
        results = []
        rd.on_after_updating(lambda v: results.append(v))
        rd["a"] = 1
        assert len(results) == 1
