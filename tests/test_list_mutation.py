from webcompy.reactive._list import ReactiveList


class TestListMutationMetadata:
    def test_append(self):
        rl = ReactiveList([1, 2])
        rl.append(3)
        m = rl._last_mutation
        assert m is not None
        assert m.op == "append"
        assert m.index == 2
        assert m.value == 3

    def test_extend(self):
        rl = ReactiveList([1])
        rl.extend([2, 3])
        m = rl._last_mutation
        assert m is not None
        assert m.op == "extend"
        assert m.index == 1
        assert m.value == [2, 3]

    def test_pop_no_index(self):
        rl = ReactiveList([1, 2, 3])
        rl.pop()
        m = rl._last_mutation
        assert m is not None
        assert m.op == "pop"
        assert m.index == 2
        assert m.value == 3

    def test_pop_with_index(self):
        rl = ReactiveList([1, 2, 3])
        rl.pop(1)
        m = rl._last_mutation
        assert m is not None
        assert m.op == "pop"
        assert m.index == 1
        assert m.value == 2

    def test_insert(self):
        rl = ReactiveList([1, 3])
        rl.insert(1, 2)
        m = rl._last_mutation
        assert m is not None
        assert m.op == "insert"
        assert m.index == 1
        assert m.value == 2

    def test_sort(self):
        rl = ReactiveList([3, 1, 2])
        rl.sort()
        m = rl._last_mutation
        assert m is not None
        assert m.op == "sort"
        assert m.index is None
        assert m.value is None

    def test_remove(self):
        rl = ReactiveList([1, 2, 3])
        rl.remove(2)
        m = rl._last_mutation
        assert m is not None
        assert m.op == "remove"
        assert m.index == 1
        assert m.value == 2

    def test_clear(self):
        rl = ReactiveList([1, 2, 3])
        rl.clear()
        m = rl._last_mutation
        assert m is not None
        assert m.op == "clear"
        assert m.index is None
        assert m.value is None

    def test_reverse(self):
        rl = ReactiveList([1, 2, 3])
        rl.reverse()
        m = rl._last_mutation
        assert m is not None
        assert m.op == "reverse"
        assert m.index is None
        assert m.value is None

    def test_setitem_int(self):
        rl = ReactiveList([1, 2, 3])
        rl[1] = 99
        m = rl._last_mutation
        assert m is not None
        assert m.op == "setitem"
        assert m.index == 1
        assert m.value == 99

    def test_setitem_slice(self):
        rl = ReactiveList([1, 2, 3])
        rl[0:2] = [10, 20]
        m = rl._last_mutation
        assert m is not None
        assert m.op == "setitem"
        assert m.index is None
        assert m.value is None


class TestListMutationInitialState:
    def test_fresh_list_has_no_mutation(self):
        rl = ReactiveList([1, 2])
        assert rl._last_mutation is None


class TestListMutationCallbackContract:
    def test_on_after_updating_receives_return_value(self):
        rl = ReactiveList([1, 2])
        received = []
        rl.on_after_updating(lambda val: received.append(val))
        rl.append(3)
        assert len(received) == 1

    def test_on_before_updating_receives_old_value_reference(self):
        rl = ReactiveList([1, 2])
        received = []
        rl.on_before_updating(lambda val: received.append(val))
        rl.append(3)
        assert len(received) == 1

    def test_pop_on_after_receives_popped_value(self):
        rl = ReactiveList([1, 2, 3])
        received = []
        rl.on_after_updating(lambda val: received.append(val))
        rl.pop(1)
        assert len(received) == 1
        assert received[0] == [1, 3]
