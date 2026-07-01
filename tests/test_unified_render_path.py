from __future__ import annotations

import pytest

from tests.conftest import (
    FakeBrowserDOMPort,
    FakeBrowserFFIPort,
    FakeBrowserHostPort,
    FakeDOMNode,
)
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.types._element import Element
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._text import TextElement
from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
from webcompy_server.ports import VirtualDOMNode
from webcompy_server.ports._dom import ServerDOMPort


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


async def _render_with_fake_browser(element):

    scope = DIScope()
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    try:
        root_node = FakeDOMNode("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True

        class _DummyParent:
            def __init__(self, node):
                self._node = node

            def _get_node(self):
                return self._node

            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

            def _re_index_children(self, recursive):
                pass

        element._parent = _DummyParent(root_node)
        element._node_idx = 0
        await element._render()
        if root_node.childNodes.length > 0:
            return root_node.childNodes[0]
        return None
    finally:
        _active_di_scope.reset(token)


async def _render_with_server(element):

    port = ServerDOMPort()
    scope = DIScope()
    scope.provide(DOM_PORT_KEY, port)
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    try:
        root_node = VirtualDOMNode("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True

        class _DummyParent:
            def __init__(self, node):
                self._node = node

            def _get_node(self):
                return self._node

            def _get_belonging_component(self):
                return ""

            def _get_belonging_components(self):
                return ()

            def _re_index_children(self, recursive):
                pass

        element._parent = _DummyParent(root_node)
        element._node_idx = 0
        await element._render()
        if root_node.childNodes.length > 0:
            return root_node.childNodes[0]
        return None
    finally:
        _active_di_scope.reset(token)


def _extract_node_info(node, *, is_virtual=False):
    if node is None:
        return None
    info: dict = {"nodeName": node.nodeName, "nodeType": node.nodeType}
    if node.nodeType == 3:
        info["textContent"] = node.textContent
    else:
        attrs = {}
        for name in node.getAttributeNames():
            attrs[name] = node.getAttribute(name)
        info["attributes"] = attrs
        children = []
        for i in range(node.childNodes.length):
            children.append(_extract_node_info(node.childNodes[i], is_virtual=is_virtual))
        info["children"] = children
    return info


class TestUnifiedRenderPath:
    @pytest.mark.asyncio
    async def test_simple_div(self):
        el = FakeRootElement("div", {"class": "test"}, {}, None, None)
        fake_node = await _render_with_fake_browser(el)
        server_el = FakeRootElement("div", {"class": "test"}, {}, None, None)
        virtual_node = await _render_with_server(server_el)
        fake_info = _extract_node_info(fake_node)
        virtual_info = _extract_node_info(virtual_node, is_virtual=True)
        assert fake_info["nodeName"] == virtual_info["nodeName"]
        assert fake_info["attributes"] == virtual_info["attributes"]

    @pytest.mark.asyncio
    async def test_text_child(self):
        el = FakeRootElement("p", {}, {}, None, [TextElement("hello")])
        fake_node = await _render_with_fake_browser(el)
        server_el = FakeRootElement("p", {}, {}, None, [TextElement("hello")])
        virtual_node = await _render_with_server(server_el)
        fake_info = _extract_node_info(fake_node)
        virtual_info = _extract_node_info(virtual_node, is_virtual=True)
        assert fake_info["nodeName"] == virtual_info["nodeName"]
        assert len(fake_info["children"]) == len(virtual_info["children"])
        assert fake_info["children"][0]["textContent"] == virtual_info["children"][0]["textContent"]

    @pytest.mark.asyncio
    async def test_nested_elements(self):
        child = FakeRootElement("span", {"id": "inner"}, {}, None, None)
        el = FakeRootElement("div", {"class": "outer"}, {}, None, [child])
        fake_node = await _render_with_fake_browser(el)
        server_child = FakeRootElement("span", {"id": "inner"}, {}, None, None)
        server_el = FakeRootElement("div", {"class": "outer"}, {}, None, [server_child])
        virtual_node = await _render_with_server(server_el)
        fake_info = _extract_node_info(fake_node)
        virtual_info = _extract_node_info(virtual_node, is_virtual=True)
        assert fake_info["nodeName"] == virtual_info["nodeName"]
        assert fake_info["attributes"]["class"] == virtual_info["attributes"]["class"]
        assert len(fake_info["children"]) == len(virtual_info["children"])
        assert fake_info["children"][0]["nodeName"] == virtual_info["children"][0]["nodeName"]
        assert fake_info["children"][0]["attributes"]["id"] == virtual_info["children"][0]["attributes"]["id"]

    @pytest.mark.asyncio
    async def test_element_with_event_handler(self):
        el = FakeRootElement("button", {}, {"click": lambda e: None}, None, None)
        fake_node = await _render_with_fake_browser(el)
        server_el = FakeRootElement("button", {}, {"click": lambda e: None}, None, None)
        virtual_node = await _render_with_server(server_el)
        fake_info = _extract_node_info(fake_node)
        virtual_info = _extract_node_info(virtual_node, is_virtual=True)
        assert fake_info["nodeName"] == virtual_info["nodeName"]
        assert any(et == "click" for et, _ in fake_node._event_listeners)
        assert any(et == "click" for et, _ in virtual_node._event_listeners)

    @pytest.mark.asyncio
    async def test_server_render_produces_valid_html(self):
        server_el = FakeRootElement("div", {"class": "container"}, {}, None, [TextElement("hello")])
        virtual_node = await _render_with_server(server_el)
        port = ServerDOMPort()
        html = port.render_html(virtual_node)
        assert html == '<div class="container">hello</div>'


class TestFakeDOMNodeDomNodeRefPassthrough:
    def test_set_value_via_ref(self):
        node = FakeDOMNode("input")
        ref = DomNodeRef()
        ref.__init_node__(node)
        ref.value = "hello"
        assert ref.value == "hello"
        assert node.value == "hello"

    def test_set_checked_via_ref(self):
        node = FakeDOMNode("input")
        ref = DomNodeRef()
        ref.__init_node__(node)
        ref.checked = True
        assert ref.checked is True
        assert node.checked is True

    def test_access_unset_property_via_ref_raises_attribute_error(self):
        node = FakeDOMNode("div")
        ref = DomNodeRef()
        ref.__init_node__(node)
        with pytest.raises(AttributeError):
            _ = ref.nonexistent_property

    def test_ref_property_isolation(self):
        node_a = FakeDOMNode("input")
        node_b = FakeDOMNode("input")
        ref_a = DomNodeRef()
        ref_b = DomNodeRef()
        ref_a.__init_node__(node_a)
        ref_b.__init_node__(node_b)
        ref_a.value = "foo"
        ref_b.value = "bar"
        assert ref_a.value == "foo"
        assert ref_b.value == "bar"
