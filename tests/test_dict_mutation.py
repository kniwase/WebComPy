from webcompy.reactive._dict import ReactiveDict


class TestDictMutationMetadata:
    def test_setitem(self):
        rd = ReactiveDict({"a": 1})
        rd["b"] = 2
        m = rd._last_mutation
        assert m is not None
        assert m.op == "set"
        assert m.key == "b"
        assert m.value == 2

    def test_delitem(self):
        rd = ReactiveDict({"a": 1, "b": 2})
        del rd["a"]
        m = rd._last_mutation
        assert m is not None
        assert m.op == "delete"
        assert m.key == "a"
        assert m.value == 1

    def test_pop(self):
        rd = ReactiveDict({"a": 1, "b": 2})
        val = rd.pop("b")
        m = rd._last_mutation
        assert m is not None
        assert m.op == "pop"
        assert m.key == "b"
        assert m.value == 2
        assert val == 2

    def test_clear(self):
        rd = ReactiveDict({"a": 1, "b": 2})
        rd.clear()
        m = rd._last_mutation
        assert m is not None
        assert m.op == "clear"
        assert m.key is None
        assert m.value is None


class TestDictMutationInitialState:
    def test_fresh_dict_has_no_mutation(self):
        rd = ReactiveDict({"a": 1})
        assert rd._last_mutation is None

    def test_none_init_has_no_mutation(self):
        rd = ReactiveDict()
        assert rd._last_mutation is None


class TestDictMutationCallbackContract:
    def test_on_after_updating_is_called_on_setitem(self):
        rd = ReactiveDict({"a": 1})
        received = []
        rd.on_after_updating(lambda val: received.append(val))
        rd["b"] = 2
        assert len(received) == 1

    def test_on_before_updating_is_called_on_setitem(self):
        rd = ReactiveDict({"a": 1})
        received = []
        rd.on_before_updating(lambda val: received.append(val))
        rd["a"] = 10
        assert len(received) == 1
