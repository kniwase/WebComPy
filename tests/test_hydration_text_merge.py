from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


class TestFakeDOMNodeSplitText:
    def test_split_text_splits_content(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="ab")
        parent.appendChild(node)
        new_node = node.splitText(1)
        assert node.textContent == "a"
        assert new_node.textContent == "b"
        assert new_node is not node

    def test_split_text_inserts_new_node_after_receiver(self):
        parent = FakeDOMNode("div")
        first = FakeDOMNode("#text", text_content="aa")
        middle = FakeDOMNode("#text", text_content="bb")
        last = FakeDOMNode("#text", text_content="cc")
        parent.appendChild(first)
        parent.appendChild(middle)
        parent.appendChild(last)
        new_middle = middle.splitText(1)
        assert [n.textContent for n in parent.childNodes] == ["aa", "b", "b", "cc"]
        assert new_middle.parentNode is parent
        assert new_middle is parent.childNodes[2]

    def test_split_text_at_end_appends(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="ab")
        parent.appendChild(node)
        new_node = node.splitText(2)
        assert node.textContent == "ab"
        assert new_node.textContent == ""
        assert parent.childNodes.length == 2

    def test_split_text_zero_offset_keeps_all_in_new_node(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="ab")
        parent.appendChild(node)
        new_node = node.splitText(0)
        assert node.textContent == ""
        assert new_node.textContent == "ab"

    def test_split_text_out_of_range_raises(self):
        node = FakeDOMNode("#text", text_content="ab")
        with pytest.raises(IndexError):
            node.splitText(-1)
        with pytest.raises(IndexError):
            node.splitText(3)

    def test_split_text_on_element_node_raises(self):
        node = FakeDOMNode("div")
        with pytest.raises(TypeError):
            node.splitText(0)


class TestHydrationTextMergeSpike:
    def test_merged_text_nodes_are_split_for_1to1_adoption(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()

        prerendered = FakeDOMNode("div")
        prerendered.__webcompy_prerendered_node__ = True
        merged = FakeDOMNode("#text", text_content="ab")
        merged.__webcompy_prerendered_node__ = True
        prerendered.appendChild(merged)
        parent_node.appendChild(prerendered)

        el = Element("div", {}, {}, None, ["a", "b"])
        el._parent = parent
        el._node_idx = 0
        el._hydrate_node()

        assert el._node_cache is prerendered
        assert prerendered.childNodes.length == 2
        assert prerendered.childNodes[0].textContent == "a"
        assert prerendered.childNodes[1].textContent == "b"
