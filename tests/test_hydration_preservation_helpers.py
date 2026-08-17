from __future__ import annotations

from webcompy.elements.types._element import Element
from webcompy_testing import FakeDOMNode


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def make_prerendered_parent(*children: FakeDOMNode) -> FakeRootElement:
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    for child in children:
        child.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(child)
    return parent


def prerendered_div(text: str = "") -> FakeDOMNode:
    node = FakeDOMNode("div")
    node.__webcompy_prerendered_node__ = True
    if text:
        text_node = FakeDOMNode("#text", text_content=text)
        text_node.__webcompy_prerendered_node__ = True
        node.appendChild(text_node)
    return node


def prerendered_text(text: str) -> FakeDOMNode:
    node = FakeDOMNode("#text", text_content=text)
    node.__webcompy_prerendered_node__ = True
    return node
