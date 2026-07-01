from __future__ import annotations

import html as html_module
from collections.abc import Callable
from typing import Any

from webcompy.ports._dom import DOMEvent, DOMNode, DOMPort
from webcompy_server.ports._virtual_dom import VirtualDOMEvent, VirtualDOMNode

_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


_RAW_CONTENT_ELEMENTS = frozenset({"script", "style"})


class ServerDOMPort(DOMPort):
    def create_element(self, tag: str) -> DOMNode:
        return VirtualDOMNode(tag)

    def create_text_node(self, text: str) -> DOMNode:
        return VirtualDOMNode("#text", node_type=3, text_content=text)

    def create_event(
        self,
        event_type: str,
        *,
        bubbles: bool = False,
        cancelable: bool = False,
    ) -> DOMEvent:
        return VirtualDOMEvent(event_type, bubbles=bubbles, cancelable=cancelable)

    def query_selector(self, selector: str) -> DOMNode | None:
        return None

    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        return None

    def set_title(self, title: str) -> None:
        pass

    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        return lambda: None

    def render_html(self, node: DOMNode) -> str:
        return _serialize_node(node)


def _serialize_node(node: DOMNode) -> str:
    if node.nodeType == 3:
        text = node.textContent or ""
        parent = node.parentNode
        if parent is not None and parent.nodeName.lower() in _RAW_CONTENT_ELEMENTS:
            return text
        return html_module.escape(text)
    tag_lower = node.nodeName.lower()
    attrs_str = _serialize_attrs(node)
    if tag_lower in _VOID_ELEMENTS:
        return f"<{tag_lower}{attrs_str}>"
    inner_html = getattr(node, "innerHTML", None)
    if inner_html is not None:
        return f"<{tag_lower}{attrs_str}>{inner_html}</{tag_lower}>"
    children_html = "".join(_serialize_node(node.childNodes[i]) for i in range(node.childNodes.length))
    return f"<{tag_lower}{attrs_str}>{children_html}</{tag_lower}>"


def _serialize_attrs(node: DOMNode) -> str:
    parts: list[str] = []
    for name in node.getAttributeNames():
        value = node.getAttribute(name)
        if value is None:
            parts.append(name)
        else:
            escaped = html_module.escape(value, quote=True)
            parts.append(f'{name}="{escaped}"')
    if parts:
        return " " + " ".join(parts)
    return ""
