from __future__ import annotations

import re
from typing import Any
from unittest.mock import MagicMock

from webcompy.ports._fetch import FetchPort, Response
from webcompy.ports._ffi import FFIPort
from webcompy.ports._host import HostPort
from webcompy.ports._server._dom import ServerDOMPort
from webcompy.testing._dom import FakeDOMNode


class FakeBrowserDOMPort(ServerDOMPort):
    def __init__(self) -> None:
        super().__init__()
        self._html = FakeDOMNode("html")
        self._head = FakeDOMNode("head")
        self._body = FakeDOMNode("body")
        self._html.appendChild(self._head)
        self._html.appendChild(self._body)

    def create_element(self, tag: str) -> FakeDOMNode:
        return FakeDOMNode(tag)

    def create_text_node(self, text: str) -> FakeDOMNode:
        return FakeDOMNode("#text", text_content=text)

    def query_selector(self, selector: str) -> FakeDOMNode | None:
        if ">" in selector:
            return None
        tag_match = re.match(r"([a-zA-Z][a-zA-Z0-9]*)", selector)
        id_match = re.match(r"#([a-zA-Z][a-zA-Z0-9_-]*)", selector)
        attr_match = re.match(r'([a-zA-Z][a-zA-Z0-9]*)\[([a-zA-Z_-]+)="([^"]*)"\]', selector)

        if id_match:
            return _find_by_id(self._html, id_match.group(1))
        if attr_match:
            return _find_by_tag_attr(self._html, attr_match.group(1), attr_match.group(2), attr_match.group(3))
        if tag_match:
            return _find_by_tag(self._html, tag_match.group(1))
        return None

    def get_element_by_id(self, element_id: str) -> FakeDOMNode | None:
        return _find_by_id(self._html, element_id)


def _find_by_tag(node: FakeDOMNode, tag: str) -> FakeDOMNode | None:
    if node.nodeName == tag.upper():
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, FakeDOMNode):
            result = _find_by_tag(child, tag)
            if result is not None:
                return result
    return None


def _find_by_id(node: FakeDOMNode, element_id: str) -> FakeDOMNode | None:
    if node.getAttribute("id") == element_id:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, FakeDOMNode):
            result = _find_by_id(child, element_id)
            if result is not None:
                return result
    return None


def _find_by_tag_attr(node: FakeDOMNode, tag: str, attr_name: str, attr_value: str) -> FakeDOMNode | None:
    if node.nodeName == tag.upper() and node.getAttribute(attr_name) == attr_value:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, FakeDOMNode):
            result = _find_by_tag_attr(child, tag, attr_name, attr_value)
            if result is not None:
                return result
    return None


class FakeBrowserHostPort(HostPort):
    def schedule_macro_task(self, callback: Any) -> None:
        callback()

    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Any = None,
        default: Any = None,
    ) -> Any:
        def _getter() -> Any:
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter


class FakeBrowserFFIPort(FFIPort):
    def create_proxy(self, func: Any) -> Any:
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy

    def destroy_proxy(self, proxy: Any) -> None:
        if hasattr(proxy, "destroy"):
            proxy.destroy()

    def is_none(self, value: Any) -> bool:
        return value is None

    def to_js(self, value: Any, **kwargs: Any) -> Any:
        return value

    def assign(self, target: Any, source: Any) -> None:
        target.update(source)


class FakeFetchPort(FetchPort):
    def __init__(self, responses: dict[tuple[str, str], Response] | None = None) -> None:
        self._responses = responses or {}

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        key = (method, url)
        if key in self._responses:
            return self._responses[key]
        raise KeyError(
            f"No canned response registered for {method} {url}. Registered keys: {list(self._responses.keys())}"
        )
