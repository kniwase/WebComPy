from __future__ import annotations

from tests.conftest import FakeDOMNode
from webcompy.elements.types._element import Element


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


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
