from __future__ import annotations

from typing import Any

from webcompy._browser._modules import browser as _raw_browser
from webcompy.exception import WebComPyException
from webcompy.ports._dom import DOMNode, DOMNodeList, DOMPort
from webcompy.utils._environment import ENVIRONMENT


class BrowserDOMNode(DOMNode):
    def __init__(self, node: Any) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserDOMNode is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        self._node = node

    def append_child(self, child: DOMNode) -> None:
        if isinstance(child, BrowserDOMNode):
            self._node.appendChild(child._node)

    def remove_child(self, child: DOMNode) -> None:
        if isinstance(child, BrowserDOMNode):
            self._node.removeChild(child._node)

    def insert_before(self, new_node: DOMNode, ref_node: DOMNode) -> None:
        if isinstance(new_node, BrowserDOMNode) and isinstance(ref_node, BrowserDOMNode):
            self._node.insertBefore(new_node._node, ref_node._node)

    def replace_child(self, new_node: DOMNode, old_node: DOMNode) -> None:
        if isinstance(new_node, BrowserDOMNode) and isinstance(old_node, BrowserDOMNode):
            self._node.replaceChild(new_node._node, old_node._node)

    def remove(self) -> None:
        self._node.remove()

    def set_attribute(self, name: str, value: str) -> None:
        self._node.setAttribute(name, value)

    def get_attribute(self, name: str) -> str | None:
        val = self._node.getAttribute(name)
        return val if val is not None else None

    def remove_attribute(self, name: str) -> None:
        self._node.removeAttribute(name)

    def has_attribute(self, name: str) -> bool:
        return self._node.hasAttribute(name)

    def get_attribute_names(self) -> list[str]:
        return list(self._node.getAttributeNames())

    def add_event_listener(
        self,
        event_type: str,
        handler: Any,
        *,
        capture: bool = False,
    ) -> None:
        handler = self._browser.pyscript.ffi.create_proxy(handler)
        self._node.addEventListener(event_type, handler, capture)

    def remove_event_listener(
        self,
        event_type: str,
        handler: Any,
        *,
        capture: bool = False,
    ) -> None:
        self._node.removeEventListener(event_type, handler, capture)

    @property
    def text_content(self) -> str | None:
        return self._node.textContent

    @text_content.setter
    def text_content(self, value: str | None) -> None:
        self._node.textContent = value

    @property
    def child_nodes(self) -> DOMNodeList:
        return DOMNodeList([BrowserDOMNode(n) for n in self._node.childNodes])

    @property
    def node_name(self) -> str:
        return str(self._node.nodeName)

    @property
    def node_type(self) -> int:
        return int(self._node.nodeType)

    @property
    def __webcompy_node__(self) -> bool:
        return self._node.__webcompy_node__

    @__webcompy_node__.setter
    def __webcompy_node__(self, value: bool) -> None:
        self._node.__webcompy_node__ = value

    @property
    def __webcompy_prerendered_node__(self) -> bool:
        return self._node.__webcompy_prerendered_node__

    @__webcompy_prerendered_node__.setter
    def __webcompy_prerendered_node__(self, value: bool) -> None:
        self._node.__webcompy_prerendered_node__ = value


class BrowserDOMPort(DOMPort):
    def __init__(self) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserDOMPort is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser

    def create_element(self, tag: str) -> DOMNode:
        return BrowserDOMNode(self._browser.document.createElement(tag))

    def create_text_node(self, text: str) -> DOMNode:
        return BrowserDOMNode(self._browser.document.createTextNode(text))

    def query_selector(self, selector: str) -> DOMNode | None:
        el = self._browser.document.querySelector(selector)
        return BrowserDOMNode(el) if el else None

    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        el = self._browser.document.getElementById(element_id)
        return BrowserDOMNode(el) if el else None

    def set_title(self, title: str) -> None:
        self._browser.document.title = title

    def schedule_macro_task(self, callback: Any) -> None:
        callback = self._browser.pyscript.ffi.create_proxy(callback)
        self._browser.window.setTimeout(callback, 0)
