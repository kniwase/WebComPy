from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._browser._raw import browser as _raw_browser
from webcompy.ports._dom import DOMNode, DOMPort
from webcompy.utils._environment import ENVIRONMENT


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
        return self._browser.document.querySelector(selector) or None

    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        return self._browser.document.getElementById(element_id) or None

    def set_title(self, title: str) -> None:
        self._browser.document.title = title

    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        proxy = self._browser.pyscript.ffi.create_proxy(handler)
        self._browser.document.addEventListener(event_type, proxy)

        def _remove() -> None:
            self._browser.document.removeEventListener(event_type, proxy)
            if hasattr(proxy, "destroy"):
                proxy.destroy()

        return _remove
