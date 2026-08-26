from __future__ import annotations

import asyncio

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components import define_component
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.signal import ReactiveList, Signal
from webcompy.template import render_template
from webcompy_testing import TestRenderer


class _FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _element_texts(node):
    return [
        node.childNodes[i].textContent for i in range(node.childNodes.length) if node.childNodes[i].nodeName != "#text"
    ]


def _find_tag(elems, tag):
    for e in elems:
        if getattr(e, "_tag_name", None) == tag:
            return e
    return None


class TestNonZeroOffsetRegularElementRefresh:
    def test_children_indexed_from_zero_and_order_kept_after_refresh(self):
        items = ReactiveList(["x", "y"])

        @define_component()
        def SiblingPage(context):
            return render_template(
                """
                <div>
                    <p>header</p>
                    <section>
                        {% for item in items %}
                        <b>{{ item }}</b>
                        {% endfor %}
                        <span>tail</span>
                    </section>
                </div>
                """,
                {"items": items},
            )

        with TestRenderer.render(SiblingPage) as result:
            section = _find_tag(result._instance._children[0]._children, "section")
            assert section._node_idx == 3
            assert [c._node_idx for c in section._children] == [0, 1, 7, 8, 9]
            rep = next(c for c in section._children if c.__class__.__name__ == "RepeatElement")
            assert rep._node_idx == 1
            assert [c._node_idx for c in rep._children] == [1, 4]
            node = section._get_node()
            assert _element_texts(node) == ["x", "y", "tail"]
            items.append("z")
            assert [c._node_idx for c in rep._children] == [1, 4, 7]
            assert _element_texts(node) == ["x", "y", "z", "tail"]
            items.pop(0)
            assert [c._node_idx for c in rep._children] == [1, 4]
            assert _element_texts(node) == ["y", "z", "tail"]


class TestDynamicContainerNonZeroOffset:
    @pytest.mark.asyncio
    async def test_fragment_children_indexed_from_container_offset(self, fake_browser_full):
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        head = Element("span")
        frag = FragmentElement([Element("b"), Element("b")])
        head._parent = parent
        head._node_idx = 0
        frag._parent = parent
        frag._node_idx = 1
        parent._children = [head, frag]
        await head._render()
        await frag._render()
        assert frag._children[0]._node_idx == 1
        assert frag._children[1]._node_idx == 2
        node = parent._get_node()
        assert [c.nodeName for c in node.childNodes] == ["SPAN", "B", "B"]


class _KeepingDynamicParent(DynamicElement):
    def _on_set_parent(self):
        pass


class TestSwitchInsideDynamicParentAtOffset:
    @pytest.mark.asyncio
    async def test_preceding_sibling_preserved_across_toggles(self, fake_browser_full):
        flag = Signal(True)
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        head = Element("span")
        head._parent = parent
        head._node_idx = 0
        switch = SwitchElement([(flag, lambda: Element("b"))], lambda: Element("i"))
        dp = _KeepingDynamicParent()
        dp._children = [switch]
        dp._parent = parent
        dp._node_idx = 1
        switch._parent = dp
        parent._children = [head, dp]
        await head._render()
        await dp._render()
        node = parent._get_node()

        def assert_head_preserved():
            assert node.childNodes[0] is head._node_cache
            assert switch._node_idx == 1

        assert_head_preserved()
        assert [c.nodeName for c in node.childNodes] == ["SPAN", "B"]
        for expected in ("I", "B", "I"):
            flag.value = not flag.value
            await switch._refresh()
            await asyncio.sleep(0)
            assert_head_preserved()
            assert [c.nodeName for c in node.childNodes] == ["SPAN", expected]


class TestDynamicParentAtOffsetZero:
    def test_reindex_yields_zero_based_indices(self, fake_browser_full):
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        frag = FragmentElement([Element("b"), Element("b")])
        frag._parent = parent
        frag._node_idx = 0
        parent._children = [frag]
        frag._re_index_children(False)
        assert frag._children[0]._node_idx == 0
        assert frag._children[1]._node_idx == 1
