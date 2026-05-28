from __future__ import annotations

import asyncio

from tests.conftest import FakeDOMNode
from webcompy.elements.types._dynamic import _patch_children
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement
from webcompy.ports._server._virtual_dom import VirtualDOMNode


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()

    def __init__(self):
        super().__init__("div", {}, {}, None, None)


def _make_element_with_parent(tag="div"):
    root = FakeRootElement()
    root._node_cache = FakeDOMNode("div")
    root._mounted = True
    parent = FakeRootElement()
    parent._parent = root
    parent._node_idx = 0
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    el = Element(tag, {}, {}, None, None)
    el._parent = parent
    el._node_idx = 0
    el._event_handlers_added = {}
    return el, parent


class TestMountNodeDetachedRecovery:
    def test_mount_node_reinserts_detached_node(self):
        el, parent = _make_element_with_parent("span")
        parent_node = parent._get_node()
        node = FakeDOMNode("span", text_content="hello")
        el._node_cache = node
        el._mounted = True
        assert node.parentNode is None
        assert parent_node.childNodes.length == 0

        asyncio.run(el._render())

        assert el._mounted is True
        assert node.parentNode is parent_node
        assert parent_node.childNodes.length == 1
        assert parent_node.childNodes[0] is node

    def test_mount_node_reinserts_text_node_detached_by_external_code(self):
        parent = FakeRootElement()
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._node_cache

        text_el = TextElement("hello")
        text_el._parent = parent
        text_el._node_idx = 0
        node = FakeDOMNode("#text", text_content="hello")
        parent_node.appendChild(node)
        text_el._node_cache = node
        text_el._mounted = True

        parent_node.removeChild(node)
        assert node.parentNode is None
        assert text_el._mounted is True

        asyncio.run(text_el._render())

        assert node.parentNode is parent_node
        assert parent_node.childNodes.length == 1
        assert parent_node.childNodes[0] is node

    def test_mount_node_does_not_affect_normal_mounted_node(self):
        el, parent = _make_element_with_parent("span")
        parent_node = parent._get_node()
        node = FakeDOMNode("span")
        parent_node.appendChild(node)
        el._node_cache = node
        el._mounted = True
        assert node.parentNode is parent_node

        asyncio.run(el._render())

        assert el._mounted is True
        assert node.parentNode is parent_node
        assert parent_node.childNodes.length == 1

    def test_mount_node_skips_when_not_mounted(self):
        el, parent = _make_element_with_parent("span")
        parent_node = parent._get_node()
        node = FakeDOMNode("span")
        el._node_cache = node
        el._mounted = None
        assert parent_node.childNodes.length == 0

        asyncio.run(el._render())

        assert el._mounted is True
        assert node.parentNode is parent_node
        assert parent_node.childNodes.length == 1


class TestPreserveChildrenRender:
    def _make_element(self, tag="div"):
        el, parent = _make_element_with_parent(tag)
        parent_node = parent._get_node()
        node = FakeDOMNode(tag)
        parent_node.appendChild(node)
        el._node_cache = node
        el._mounted = True
        return el, node

    def test_preserve_children_skips_cleanup(self):
        el, node = self._make_element("code")
        el._preserve_children = True

        for _ in range(3):
            span = VirtualDOMNode("span")
            span.__webcompy_node__ = False
            node.appendChild(span)

        assert node.childNodes.length == 3

        asyncio.run(el._render())

        assert node.childNodes.length == 3

    def test_without_preserve_children_cleans_up(self):
        el, node = self._make_element("code")
        el._preserve_children = False

        for _ in range(3):
            span = VirtualDOMNode("span")
            span.__webcompy_node__ = False
            node.appendChild(span)

        assert node.childNodes.length == 3

        asyncio.run(el._render())

        assert node.childNodes.length == 0

    def test_preserve_children_with_mixed_children(self):
        el, node = self._make_element("code")
        el._preserve_children = True

        webcmpy_span = Element("span", {}, {}, None, None)
        webcmpy_span._parent = el
        webcmpy_span._node_idx = 0
        webcmpy_span._event_handlers_added = {}
        el._children = [webcmpy_span]

        external = VirtualDOMNode("span")
        external.__webcompy_node__ = False
        node.appendChild(external)

        webcmpy_node = FakeDOMNode("span")
        node.appendChild(webcmpy_node)
        webcmpy_span._node_cache = webcmpy_node
        webcmpy_span._mounted = True

        assert node.childNodes.length == 2
        assert el._children_length == 1

        asyncio.run(el._render())

        assert node.childNodes.length == 2
        assert external in [node.childNodes[i] for i in range(node.childNodes.length)]
        assert webcmpy_node in [node.childNodes[i] for i in range(node.childNodes.length)]


class TestPreserveChildrenHydrate:
    def test_hydrate_respects_preserve_children(self, fake_browser_full):
        from webcompy.elements.generators import create_element

        el = create_element("code", {}, None)

        root = FakeRootElement()
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement()
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        el._parent = parent
        el._node_idx = 0

        parent_node = parent._get_node()

        prerendered = FakeDOMNode("code")
        prerendered.__webcompy_prerendered_node__ = True
        parent_node.appendChild(prerendered)

        el._preserve_children = True

        span = VirtualDOMNode("span")
        span.__webcompy_node__ = False
        span.__webcompy_prerendered_node__ = True
        prerendered.appendChild(span)

        el._hydrate_node()

        assert prerendered.childNodes.length == 1

    def test_hydrate_without_preserve_children_cleans_up(self, fake_browser_full):
        from webcompy.elements.generators import create_element

        el = create_element("code", {}, None)

        root = FakeRootElement()
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement()
        parent._parent = root
        parent._node_idx = 0
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        el._parent = parent
        el._node_idx = 0

        parent_node = parent._get_node()

        prerendered = FakeDOMNode("code")
        prerendered.__webcompy_prerendered_node__ = True
        parent_node.appendChild(prerendered)

        el._preserve_children = False

        span = VirtualDOMNode("span")
        span.__webcompy_node__ = False
        span.__webcompy_prerendered_node__ = True
        prerendered.appendChild(span)

        el._hydrate_node()

        assert prerendered.childNodes.length == 0


class TestSwitchElementPreserveExternalNodes:
    def test_patch_preserves_external_nodes_and_reinserts_text(self):
        old_inner = Element("div", {}, {}, None, None, preserve_children=True)
        old_inner._event_handlers_added = {}

        old_text = TextElement("hello")
        old_text._parent = old_inner
        old_text._node_idx = 0
        old_text_node = FakeDOMNode("#text", text_content="hello")
        old_text._node_cache = old_text_node
        old_text._mounted = True
        old_inner._children = [old_text]

        parent_node = FakeDOMNode("article")

        old_inner_node = FakeDOMNode("div")
        parent_node.appendChild(old_inner_node)
        old_inner._node_cache = old_inner_node
        old_inner._mounted = True

        old_inner_node.appendChild(old_text_node)

        ext_span = VirtualDOMNode("span")
        ext_span.__webcompy_node__ = False
        old_inner_node.appendChild(ext_span)

        assert old_inner_node.childNodes.length == 2

        old_inner_node.removeChild(old_text_node)
        assert old_text_node.parentNode is None
        assert old_text._mounted is True

        new_inner = Element("div", {}, {}, None, None, preserve_children=True)
        new_inner._event_handlers_added = {}
        root = FakeRootElement()
        root._node_cache = FakeDOMNode("div")
        root._mounted = True
        parent = FakeRootElement()
        parent._parent = root
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent._get_node = lambda: parent_node  # type: ignore[method-assign]

        new_inner._parent = parent
        new_inner._node_idx = 0

        new_text = TextElement("new")
        new_text._parent = new_inner
        new_text._node_idx = 0
        new_inner._children = [new_text]

        _patch_children([old_inner], [new_inner])

        asyncio.run(new_inner._render())

        assert old_text_node.parentNode is old_inner_node
        assert ext_span in [old_inner_node.childNodes[i] for i in range(old_inner_node.childNodes.length)]
        assert old_inner_node.childNodes.length == 2
