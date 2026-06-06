import asyncio

import pytest

from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._text import TextElement
from webcompy.exception import WebComPyException
from webcompy.signal import ReactiveDict, ReactiveList


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_parent():
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


class TestKeyedReconciliation:
    @pytest.mark.asyncio
    async def test_append_preserves_existing_children(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x, k: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_children = list(rep._children)
        rl.append("d")
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 4
        assert rep._children[0] is original_children[0]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[2]
        assert rep._children_keys == ["a", "b", "c", "d"]

    @pytest.mark.asyncio
    async def test_pop_removes_only_popped_child(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x, k: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[2]
        rl.pop(1)
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 2
        assert rep._children[0] is original_child_a
        assert rep._children[1] is original_child_c
        assert rep._children_keys == ["a", "c"]

    @pytest.mark.asyncio
    async def test_insert_mid_list_preserves_existing(self, fake_browser_full):
        rl = ReactiveList(["a", "c"])
        rep = RepeatElement(rl, lambda x, k: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[1]
        rl.insert(1, "b")
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 3
        assert rep._children[0] is original_child_a
        assert rep._children[2] is original_child_c
        assert rep._children_keys == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_reverse_reuses_all_children(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x, k: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_children = list(rep._children)
        rl.reverse()
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 3
        assert rep._children[0] is original_children[2]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[0]
        assert rep._children_keys == ["c", "b", "a"]

    @pytest.mark.asyncio
    async def test_clear_removes_all_children(self, fake_browser_full):
        rl = ReactiveList(["a", "b", "c"])
        rep = RepeatElement(rl, lambda x, k: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        rl.clear()
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 0
        assert rep._children_keys == []

    @pytest.mark.asyncio
    async def test_duplicate_keys_raise_exception(self, fake_browser_full):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda x, k: TextElement(x), key=lambda x: x)
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        with pytest.raises(WebComPyException, match="Duplicate key"):
            rl.append("a")

    @pytest.mark.asyncio
    async def test_unkeyed_repeat_does_full_rebuild(self, fake_browser_full):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rl.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_children = list(rep._children)
        rl.append("c")
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 3
        assert rep._children[0] is not original_children[0]


class TestDictKeyedReconciliation:
    @pytest.mark.asyncio
    async def test_dict_setitem_preserves_existing_children(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2", "c": "3"})
        rep = RepeatElement(rd, lambda v, k: TextElement(f"{k}:{v}"))
        assert rep._is_dict is True
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rd.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_children = list(rep._children)
        rd["d"] = "4"
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 4
        assert rep._children[0] is original_children[0]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[2]
        assert rep._children_keys == ["a", "b", "c", "d"]

    @pytest.mark.asyncio
    async def test_dict_delitem_removes_only_deleted_child(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2", "c": "3"})
        rep = RepeatElement(rd, lambda v, k: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rd.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[2]
        del rd["b"]
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 2
        assert rep._children[0] is original_child_a
        assert rep._children[1] is original_child_c
        assert rep._children_keys == ["a", "c"]

    @pytest.mark.asyncio
    async def test_dict_clear_removes_all_children(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2"})
        rep = RepeatElement(rd, lambda v, k: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rd.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        rd.clear()
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 0
        assert rep._children_keys == []

    @pytest.mark.asyncio
    async def test_dict_keys_used_as_reconciliation_keys(self, fake_browser_full):
        rd = ReactiveDict({1: "one", 2: "two", 3: "three"})
        rep = RepeatElement(rd, lambda v, k: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rd.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_children = list(rep._children)
        rd[4] = "four"
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 4
        assert rep._children[0] is original_children[0]
        assert rep._children[1] is original_children[1]
        assert rep._children[2] is original_children[2]
        assert rep._children_keys == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_dict_template_receives_key_and_value(self, fake_browser_full):
        rd = ReactiveDict({"x": "hello", "y": "world"})
        received = []
        rep = RepeatElement(rd, lambda v, k: (received.append((k, v)), TextElement(v))[1])
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rd.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        assert ("x", "hello") in received
        assert ("y", "world") in received

    def test_dict_rejects_key_parameter(self):
        rd = ReactiveDict({"a": 1})
        try:
            RepeatElement(rd, lambda v, k: TextElement(str(v)), key=lambda x: x)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "key" in str(e).lower()

    @pytest.mark.asyncio
    async def test_dict_pop_removes_entry(self, fake_browser_full):
        rd = ReactiveDict({"a": "1", "b": "2", "c": "3"})
        rep = RepeatElement(rd, lambda v, k: TextElement(f"{k}:{v}"))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._add_callback_node(rd.on_after_updating(rep._refresh_sync))
        await rep._refresh()
        original_child_a = rep._children[0]
        original_child_c = rep._children[2]
        rd.pop("b")
        # Allow signal callback to execute
        await asyncio.sleep(0)
        assert len(rep._children) == 2
        assert rep._children[0] is original_child_a
        assert rep._children[1] is original_child_c
