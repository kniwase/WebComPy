from __future__ import annotations

from typing import Any

from webcompy._browser._modules import browser as _raw_browser
from webcompy.exception import WebComPyException
from webcompy.ports._dom import DOMNode, DOMNodeList, DOMPort
from webcompy.utils._environment import ENVIRONMENT


class BrowserDOMNode:
    def __init__(self, node: Any) -> None:
        if ENVIRONMENT != "pyscript":
            raise WebComPyException("BrowserDOMNode is only available in browser environment")
        assert _raw_browser is not None
        self._browser = _raw_browser
        self._node = node
        self._event_proxies: dict[tuple[str, int, bool], Any] = {}

    def appendChild(self, child: DOMNode) -> None:
        if not isinstance(child, BrowserDOMNode):
            raise TypeError(f"Expected BrowserDOMNode, got {type(child).__name__}")
        self._node.appendChild(child._node)

    def removeChild(self, child: DOMNode) -> None:
        if not isinstance(child, BrowserDOMNode):
            raise TypeError(f"Expected BrowserDOMNode, got {type(child).__name__}")
        self._node.removeChild(child._node)

    def insertBefore(self, new_node: DOMNode, ref_node: DOMNode) -> None:
        if not isinstance(new_node, BrowserDOMNode):
            raise TypeError(f"Expected BrowserDOMNode, got {type(new_node).__name__}")
        if not isinstance(ref_node, BrowserDOMNode):
            raise TypeError(f"Expected BrowserDOMNode, got {type(ref_node).__name__}")
        self._node.insertBefore(new_node._node, ref_node._node)

    def replaceChild(self, new_node: DOMNode, old_node: DOMNode) -> None:
        if not isinstance(new_node, BrowserDOMNode):
            raise TypeError(f"Expected BrowserDOMNode, got {type(new_node).__name__}")
        if not isinstance(old_node, BrowserDOMNode):
            raise TypeError(f"Expected BrowserDOMNode, got {type(old_node).__name__}")
        self._node.replaceChild(new_node._node, old_node._node)

    def remove(self) -> None:
        self._node.remove()

    def setAttribute(self, name: str, value: str) -> None:
        self._node.setAttribute(name, value)

    def getAttribute(self, name: str) -> str | None:
        val = self._node.getAttribute(name)
        return val if val is not None else None

    def removeAttribute(self, name: str) -> None:
        self._node.removeAttribute(name)

    def hasAttribute(self, name: str) -> bool:
        return self._node.hasAttribute(name)

    def getAttributeNames(self) -> list[str]:
        return list(self._node.getAttributeNames())

    def addEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None:
        proxy = self._browser.pyscript.ffi.create_proxy(handler)
        key = (event_type, id(handler), bool(options_or_capture))
        self._event_proxies[key] = proxy
        self._node.addEventListener(event_type, proxy, bool(options_or_capture))

    def removeEventListener(
        self,
        event_type: str,
        handler: Any,
        options_or_capture: Any = False,
    ) -> None:
        key = (event_type, id(handler), bool(options_or_capture))
        proxy = self._event_proxies.get(key)
        if proxy is not None:
            self._node.removeEventListener(event_type, proxy, bool(options_or_capture))
            if hasattr(proxy, "destroy"):
                proxy.destroy()
            del self._event_proxies[key]

    @property
    def textContent(self) -> str | None:
        return self._node.textContent

    @textContent.setter
    def textContent(self, value: str | None) -> None:
        self._node.textContent = value

    @property
    def childNodes(self) -> DOMNodeList:
        return DOMNodeList([BrowserDOMNode(n) for n in self._node.childNodes])

    @property
    def parentNode(self) -> DOMNode | None:
        p = self._node.parentNode
        return BrowserDOMNode(p) if p else None

    @property
    def nodeName(self) -> str:
        return str(self._node.nodeName)

    @property
    def nodeType(self) -> int:
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
        return self._browser.document.createElement(tag)

    def create_text_node(self, text: str) -> DOMNode:
        return self._browser.document.createTextNode(text)

    def query_selector(self, selector: str) -> DOMNode | None:
        el = self._browser.document.querySelector(selector)
        return BrowserDOMNode(el) if el else None

    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        el = self._browser.document.getElementById(element_id)
        return BrowserDOMNode(el) if el else None

    def set_title(self, title: str) -> None:
        self._browser.document.title = title

    def schedule_macro_task(self, callback: Any) -> None:
        self._browser.window.setTimeout(callback, 0)
