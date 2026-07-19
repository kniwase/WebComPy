from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import TextElement
from webcompy.signal import ReactiveList, Signal


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_parent():
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


class TestFragmentElementConstruction:
    def test_empty_children_default(self):
        frag = FragmentElement()
        assert frag._pending_children == []
        assert frag._children == []

    def test_empty_children_explicit(self):
        frag = FragmentElement([])
        assert frag._pending_children == []

    def test_with_single_child(self):
        child = TextElement("only")
        frag = FragmentElement([child])
        assert frag._pending_children == [child]

    def test_with_multiple_children(self):
        c1 = TextElement("a")
        c2 = TextElement("b")
        c3 = TextElement("c")
        frag = FragmentElement([c1, c2, c3])
        assert frag._pending_children == [c1, c2, c3]


class TestFragmentElementOnSetParent:
    def test_set_parent_reparents_children(self):
        c1 = TextElement("a")
        c2 = TextElement("b")
        frag = FragmentElement([c1, c2])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        assert c1._parent is parent
        assert c2._parent is parent
        assert frag._children is c1 or frag._children[0] is c1
        assert frag._pending_children == []

    def test_set_parent_zero_children(self):
        frag = FragmentElement([])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        assert frag._children == []
        assert frag._pending_children == []

    def test_set_parent_node_count_sums_children(self):
        c1 = TextElement("a")
        c2 = TextElement("b")
        frag = FragmentElement([c1, c2])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        assert frag._node_count == 2


class TestFragmentElementRendering:
    @pytest.mark.asyncio
    async def test_render_with_no_children(self, fake_browser_full):
        frag = FragmentElement([])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        await frag._render()
        assert frag._children == []

    @pytest.mark.asyncio
    async def test_render_single_child(self, fake_browser_full):
        child = TextElement("hi")
        frag = FragmentElement([child])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        await frag._render()
        assert len(frag._children) == 1
        assert frag._children[0] is child

    @pytest.mark.asyncio
    async def test_render_multiple_children(self, fake_browser_full):
        c1 = TextElement("a")
        c2 = TextElement("b")
        c3 = TextElement("c")
        frag = FragmentElement([c1, c2, c3])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        await frag._render()
        assert frag._children[0]._node_idx == 0
        assert frag._children[1]._node_idx == 1
        assert frag._children[2]._node_idx == 2

    @pytest.mark.asyncio
    async def test_render_nested_in_repeat(self, fake_browser_full):
        rl = ReactiveList(["x", "y"])
        rep = RepeatElement(rl, lambda v: FragmentElement([TextElement(f"a:{v}"), TextElement(f"b:{v}")]))
        parent = _make_parent()
        rep._parent = parent
        rep._node_idx = 0
        rep._on_set_parent()
        await rep._render()
        assert len(rep._children) == 2
        for child in rep._children:
            assert isinstance(child, FragmentElement)
            assert len(child._children) == 2

    @pytest.mark.asyncio
    async def test_render_nested_in_switch(self, fake_browser_full):
        cond = Signal(True)
        cases = [(cond, lambda: FragmentElement([TextElement("a"), TextElement("b")]))]
        sw = SwitchElement(cases, None)
        parent = _make_parent()
        sw._parent = parent
        sw._node_idx = 0
        sw._on_set_parent()
        await sw._render()
        assert len(sw._children) == 1
        assert isinstance(sw._children[0], FragmentElement)
        assert len(sw._children[0]._children) == 2


class TestFragmentElementHydration:
    def test_hydrate_zero_children(self, fake_browser_full):
        frag = FragmentElement([])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        frag._hydrate_node()
        assert frag._hydrated is True

    @pytest.mark.asyncio
    async def test_hydrate_single_child(self, fake_browser_full):
        child = TextElement("only")
        frag = FragmentElement([child])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        frag._hydrate_node()
        assert frag._hydrated is True

    @pytest.mark.asyncio
    async def test_hydrate_multiple_children(self, fake_browser_full):
        c1 = TextElement("a")
        c2 = TextElement("b")
        frag = FragmentElement([c1, c2])
        parent = _make_parent()
        frag._parent = parent
        frag._node_idx = 0
        frag._hydrate_node()
        assert frag._hydrated is True
