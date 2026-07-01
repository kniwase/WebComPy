from __future__ import annotations

import pytest

from webcompy_server.ports import VirtualDOMNode
from webcompy_server.ports._dom import ServerDOMPort


class TestServerDOMPortRenderHtml:
    def _make_port(self):
        return ServerDOMPort()

    def _render(self, node: VirtualDOMNode) -> str:
        return self._make_port().render_html(node)

    def test_simple_element(self):
        node = VirtualDOMNode("div")
        assert self._render(node) == "<div></div>"

    def test_element_with_text_child(self):
        parent = VirtualDOMNode("p")
        text = VirtualDOMNode("#text", node_type=3, text_content="hello")
        parent.appendChild(text)
        assert self._render(parent) == "<p>hello</p>"

    def test_element_with_attribute(self):
        node = VirtualDOMNode("div")
        node.setAttribute("id", "main")
        assert self._render(node) == '<div id="main"></div>'

    def test_element_with_multiple_attributes(self):
        node = VirtualDOMNode("input")
        node.setAttribute("type", "text")
        node.setAttribute("name", "q")
        result = self._render(node)
        assert 'type="text"' in result
        assert 'name="q"' in result

    def test_void_element(self):
        for tag in ("br", "hr", "img", "input", "meta", "link"):
            node = VirtualDOMNode(tag)
            result = self._render(node)
            assert result == f"<{tag}>"
            assert f"</{tag}>" not in result

    def test_void_element_with_attribute(self):
        node = VirtualDOMNode("img")
        node.setAttribute("src", "photo.png")
        node.setAttribute("alt", "photo")
        result = self._render(node)
        assert result.startswith("<img")
        assert ">" in result
        assert "</img>" not in result

    def test_none_valued_attribute(self):
        node = VirtualDOMNode("input")
        node._attributes["disabled"] = None
        result = self._render(node)
        assert "disabled" in result
        assert 'disabled="' not in result

    def test_text_escaping(self):
        parent = VirtualDOMNode("p")
        text = VirtualDOMNode("#text", node_type=3, text_content="<script>alert('xss')</script>")
        parent.appendChild(text)
        result = self._render(parent)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_attribute_value_escaping(self):
        node = VirtualDOMNode("div")
        node.setAttribute("title", 'a"b')
        result = self._render(node)
        assert "&quot;" in result

    def test_nested_tree(self):
        root = VirtualDOMNode("div")
        child = VirtualDOMNode("span")
        text = VirtualDOMNode("#text", node_type=3, text_content="hi")
        child.appendChild(text)
        root.appendChild(child)
        assert self._render(root) == "<div><span>hi</span></div>"

    def test_siblings(self):
        root = VirtualDOMNode("ul")
        for text in ("a", "b"):
            li = VirtualDOMNode("li")
            t = VirtualDOMNode("#text", node_type=3, text_content=text)
            li.appendChild(t)
            root.appendChild(li)
        result = self._render(root)
        assert result == "<ul><li>a</li><li>b</li></ul>"

    def test_raw_content_element(self):
        node = VirtualDOMNode("script")
        text = VirtualDOMNode("#text", node_type=3, text_content="if (x < 1) { }")
        node.appendChild(text)
        result = self._render(node)
        assert result == "<script>if (x < 1) { }</script>"

    def test_style_element_not_escaped(self):
        node = VirtualDOMNode("style")
        text = VirtualDOMNode("#text", node_type=3, text_content="a > b { color: red; }")
        node.appendChild(text)
        result = self._render(node)
        assert "a > b" in result

    def test_empty_element(self):
        node = VirtualDOMNode("div")
        assert self._render(node) == "<div></div>"

    def test_text_node_only(self):
        node = VirtualDOMNode("#text", node_type=3, text_content="hello")
        assert self._render(node) == "hello"

    def test_deeply_nested(self):
        root = VirtualDOMNode("div")
        mid = VirtualDOMNode("section")
        inner = VirtualDOMNode("p")
        text = VirtualDOMNode("#text", node_type=3, text_content="deep")
        inner.appendChild(text)
        mid.appendChild(inner)
        root.appendChild(mid)
        assert self._render(root) == "<div><section><p>deep</p></section></div>"


class TestServerDOMPortCreateElement:
    def test_creates_element_node(self):
        port = ServerDOMPort()
        node = port.create_element("div")
        assert node.nodeName == "DIV"
        assert node.nodeType == 1

    def test_creates_text_node(self):
        port = ServerDOMPort()
        node = port.create_text_node("hello")
        assert node.nodeType == 3
        assert node.textContent == "hello"

    def test_create_event(self):
        port = ServerDOMPort()
        event = port.create_event("click", bubbles=True, cancelable=False)
        assert event.type == "click"
        assert event.bubbles is True
        assert event.cancelable is False

    def test_query_selector_returns_none(self):
        port = ServerDOMPort()
        assert port.query_selector("div") is None

    def test_get_element_by_id_returns_none(self):
        port = ServerDOMPort()
        assert port.get_element_by_id("main") is None

    def test_set_title_noop(self):
        port = ServerDOMPort()
        port.set_title("test")

    def test_add_document_event_listener(self):
        port = ServerDOMPort()
        cleanup = port.add_document_event_listener("click", lambda e: None)
        cleanup()


class TestVirtualDOMNodeDomProperties:
    def test_set_and_get_value(self):
        node = VirtualDOMNode("input")
        node.value = "hello"
        assert node.value == "hello"

    def test_set_and_get_checked(self):
        node = VirtualDOMNode("input")
        node.checked = True
        assert node.checked is True

    def test_access_unset_property_raises_attribute_error(self):
        node = VirtualDOMNode("div")
        with pytest.raises(AttributeError):
            _ = node.nonexistent_property

    def test_dom_properties_not_serialized_to_html(self):
        from webcompy_server.ports._dom import ServerDOMPort

        node = VirtualDOMNode("input")
        node.setAttribute("type", "text")
        node.value = "testvalue"
        port = ServerDOMPort()
        html = port.render_html(node)
        assert 'value="testvalue"' not in html
        assert 'type="text"' in html

    def test_dom_properties_isolated_between_instances(self):
        node_a = VirtualDOMNode("input")
        node_b = VirtualDOMNode("input")
        node_a.value = "foo"
        node_b.value = "bar"
        assert node_a.value == "foo"
        assert node_b.value == "bar"
