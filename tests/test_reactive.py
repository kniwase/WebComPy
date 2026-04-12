from webcompy.reactive import Computed, Reactive, ReactiveDict, ReactiveList, readonly
from webcompy.reactive._base import ReactiveStore


class TestReactive:
    def test_initial_value(self):
        r = Reactive(10)
        assert r.value == 10

    def test_set_value(self):
        r = Reactive(0)
        r.value = 5
        assert r.value == 5

    def test_on_after_updating_callback(self):
        r = Reactive(0)
        results = []
        r.on_after_updating(lambda v: results.append(v))
        r.value = 42
        assert results == [42]

    def test_on_before_updating_callback(self):
        r = Reactive(0)
        old_values = []
        r.on_before_updating(lambda v: old_values.append(v))
        r.value = 1
        assert old_values == [0]

    def test_multiple_callbacks(self):
        r = Reactive(0)
        a = []
        b = []
        r.on_after_updating(lambda v: a.append(v))
        r.on_after_updating(lambda v: b.append(v))
        r.value = 1
        assert a == [1] and b == [1]

    def test_remove_callback(self):
        r = Reactive(0)
        results = []
        callback_id = r.on_after_updating(lambda v: results.append(v))
        r.value = 1
        ReactiveStore.remove_callback(callback_id)
        r.value = 2
        assert results == [1]


class TestComputed:
    def test_basic_computation(self):
        a = Reactive(1)
        b = Reactive(2)
        c = Computed(lambda: a.value + b.value)
        assert c.value == 3

    def test_computed_updates_on_dependency_change(self):
        a = Reactive(1)
        b = Reactive(2)
        c = Computed(lambda: a.value + b.value)
        assert c.value == 3
        a.value = 10
        assert c.value == 12

    def test_computed_with_single_dependency(self):
        a = Reactive(5)
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
        r = Reactive(10)
        ro = readonly(r)
        assert ro.value == 10

    def test_readonly_tracks_changes(self):
        r = Reactive(10)
        ro = readonly(r)
        r.value = 20
        assert ro.value == 20
