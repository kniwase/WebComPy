import importlib

import pytest

from tests.conftest import FakeBrowserModule, FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._text import TextElement
from webcompy.exception import WebComPyException
from webcompy.reactive import ReactiveList
from webcompy.reactive._dict import ReactiveDict


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_parent():
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


def _patch_browser(monkeypatch, fake_browser):
    modules_with_browser = [
        "webcompy.elements.types._element",
        "webcompy.elements.types._abstract",
        "webcompy.elements.types._text",
        "webcompy.elements.types._switch",
        "webcompy.elements.types._repeat",
    ]
    for module_name in modules_with_browser:
        mod = importlib.import_module(module_name)
        monkeypatch.setattr(mod, "browser", fake_browser)
    from webcompy._browser import _modules

    monkeypatch.setattr(_modules, "browser", fake_browser)


@pytest.fixture
def fake_browser_full(monkeypatch):
    browser = FakeBrowserModule()
    _patch_browser(monkeypatch, browser)
    return browser


class TestKeyedReconciliation:
    def test_append_preserves_existing_children(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        original_children = list(rep._children)
        rl.append("d")
        assert len(rep._children) == 4
        assert rep._children[0] is original_children[0]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[2]
        assert rep._children_keys == ["a", "b", "c", "d"]

    def test_pop_removes_only_popped_child(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[2]
        rl.pop(1)
        assert len(rep._children) == 2
        assert rep._children[0] is original_child_a
        assert rep._children[1] is original_child_c
        assert rep._children_keys == ["a", "c"]

    def test_insert_mid_list_preserves_existing(self, fake_browser_full):
        rl = ReactiveList(["a", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[1]
        rl.insert(1, "b")
        assert len(rep._children) == 3
        assert rep._children[0] is original_child_a
        assert rep._children[2] is original_child_c
        assert rep._children_keys == ["a", "b", "c"]

    def test_reverse_reuses_all_children(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        original_children = list(rep._children)
        rl.reverse()
        assert len(rep._children) == 3
        assert rep._children[0] is original_children[2]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[0]
        assert rep._children_keys == ["c", "b", "a"]

    def test_clear_removes_all_children(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        rl.clear()
        assert len(rep._children) == 0
        assert rep._children_keys == []

    def test_duplicate_keys_raise_exception(self, fake_browser_full):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda x: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        try:
            rl.append("a")
            raise AssertionError("Should have raised WebComPyException")
        except WebComPyException as e:
            assert "Duplicate key" in str(e)

    def test_unkeyed_repeat_does_full_rebuild(self, fake_browser_full):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rl.on_after_updating(rep._refresh))
        rep._refresh()
        original_children = list(rep._children)
        rl.append("c")
        assert len(rep._children) == 3
        assert rep._children[0] is not original_children[0]


class TestDictKeyedReconciliation:
    def test_dict_setitem_preserves_existing_children(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2", "c": "3"})
        rep = RepeatElement(rd, lambda k, v: TextElement(f"{k}:{v}"))
        assert rep._is_dict is True
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rd.on_after_updating(rep._refresh))
        rep._refresh()
        original_children = list(rep._children)
        rd["d"] = "4"
        assert len(rep._children) == 4
        assert rep._children[0] is original_children[0]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[2]
        assert rep._children_keys == ["a", "b", "c", "d"]

    def test_dict_delitem_removes_only_deleted_child(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2", "c": "3"})
        rep = RepeatElement(rd, lambda k, v: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rd.on_after_updating(rep._refresh))
        rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[2]
        del rd["b"]
        assert len(rep._children) == 2
        assert rep._children[0] is original_child_a
        assert rep._children[1] is original_child_c
        assert rep._children_keys == ["a", "c"]

    def test_dict_clear_removes_all_children(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2"})
        rep = RepeatElement(rd, lambda k, v: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rd.on_after_updating(rep._refresh))
        rep._refresh()
        rd.clear()
        assert len(rep._children) == 0
        assert rep._children_keys == []

    def test_dict_keys_used_as_reconciliation_keys(self, fake_browser_full):
        rd = ReactiveDict({1: "one", 2: "two", 3: "three"})
        rep = RepeatElement(rd, lambda k, v: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rd.on_after_updating(rep._refresh))
        rep._refresh()
        original_children = list(rep._children)
        rd[4] = "four"
        assert len(rep._children) == 4
        assert rep._children[0] is original_children[0]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[2]
        assert rep._children_keys == [1, 2, 3, 4]

    def test_dict_template_receives_key_and_value(self, fake_browser_full):
        rd = ReactiveDict({"x": "hello", "y": "world"})
        received = []
        rep = RepeatElement(rd, lambda k, v: (received.append((k, v)), TextElement(v))[1])
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rd.on_after_updating(rep._refresh))
        rep._refresh()
        assert ("x", "hello") in received
        assert ("y", "world") in received

    def test_dict_rejects_key_parameter(self):
        rd = ReactiveDict({"a": 1})
        try:
            RepeatElement(rd, lambda k, v: TextElement(str(v)), key=lambda x: x)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "key" in str(e).lower()

    def test_dict_pop_removes_entry(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2", "c": "3"})
        rep = RepeatElement(rd, lambda k, v: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._reactive_activated = True
        rep._set_callback_id(rd.on_after_updating(rep._refresh))
        rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[2]
        rd.pop("b")
        assert len(rep._children) == 2
        assert rep._children[0] is original_child_a
        assert rep._children[1] is original_child_c
