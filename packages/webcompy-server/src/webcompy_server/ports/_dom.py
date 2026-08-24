"""Server-side DOM port backed by a virtual DOM."""

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
    """Server-side DOM port that creates virtual nodes and serializes HTML."""

    def create_element(self, tag: str) -> DOMNode:
        """Create an element node for ``tag``.

        Args:
            tag: Tag name.

        Returns:
            New virtual element node.

        """
        return VirtualDOMNode(tag)

    def create_text_node(self, text: str) -> DOMNode:
        """Create a text node.

        Args:
            text: Text content.

        Returns:
            New virtual text node.

        """
        return VirtualDOMNode("#text", node_type=3, text_content=text)

    def create_comment(self, data: str) -> DOMNode:
        """Create a comment node.

        Args:
            data: Comment data.

        Returns:
            New virtual comment node.

        """
        return VirtualDOMNode("#comment", node_type=8, text_content=data)

    def create_event(
        self,
        event_type: str,
        *,
        bubbles: bool = False,
        cancelable: bool = False,
    ) -> DOMEvent:
        """Create a virtual DOM event.

        Args:
            event_type: Event type name.
            bubbles: Whether the event bubbles.
            cancelable: Whether the event is cancelable.

        Returns:
            New virtual event.

        """
        return VirtualDOMEvent(event_type, bubbles=bubbles, cancelable=cancelable)

    def query_selector(self, selector: str) -> DOMNode | None:
        """Query the document for ``selector``.

        Args:
            selector: CSS selector.

        Returns:
            ``None`` on the server.

        """
        return None

    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        """Return the element with ``element_id``.

        Args:
            element_id: Element ID.

        Returns:
            ``None`` on the server.

        """
        return None

    def set_title(self, title: str) -> None:
        """Set the document title.

        Args:
            title: Title to set.

        Returns:
            ``None``.

        """
        pass

    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        """Add a document-level event listener.

        Args:
            event_type: Event type.
            handler: Event handler.

        Returns:
            Callable that removes the listener.

        """
        return lambda: None

    def render_html(self, node: DOMNode) -> str:
        """Serialize ``node`` to HTML.

        Args:
            node: Virtual DOM node to serialize.

        Returns:
            HTML string for ``node``.

        """
        return _serialize_node(node)


def _serialize_node(node: DOMNode) -> str:
    if node.nodeType == 8:
        data = node.textContent or ""
        if "--" in data or data.endswith("-"):
            raise ValueError(f"Comment data must not contain '--' or end with '-': {data!r}")
        return f"<!--{data}-->"
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
