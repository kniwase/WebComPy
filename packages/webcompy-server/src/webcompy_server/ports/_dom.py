"""Server-side DOM port backed by a virtual DOM."""

from __future__ import annotations

import html as html_module
from collections.abc import Callable
from typing import Any

from webcompy.ports._dom import DOMEvent, DOMNode, DOMPort
from webcompy_server.ports._selector import parse_selector, resolve_parsed
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

    def __init__(self) -> None:
        self._document_root: DOMNode | None = None

    def _attach_document_root(self, root: DOMNode) -> None:
        """Attach the completed document tree node for selector resolution.

        Args:
            root: Rendered document root node (typically the ``<html>``
                element produced by HTML assembly).

        Returns:
            ``None``.

        """
        self._document_root = root

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
        """Query the attached document tree for ``selector``.

        Resolution supports a documented CSS subset (type/class/id
        selectors, compounds, descendant and child combinators, comma
        groups) and returns the first depth-first match. Unsupported
        syntax raises ``ValueError``.

        Args:
            selector: CSS selector from the supported subset.

        Returns:
            First matching node, or ``None`` when nothing matches or no
            document tree has been attached yet.

        Raises:
            ValueError: When the selector uses unsupported syntax.

        """
        try:
            parsed = parse_selector(selector)
        except ValueError:
            raise
        if self._document_root is None:
            return None
        return resolve_parsed(self._document_root, parsed)

    def query_selector_all(
        self,
        selector: str,
        *,
        root: DOMNode | None = None,
    ) -> list[DOMNode]:
        """Query for all matching nodes, scoped to ``root`` when given.

        Args:
            selector: CSS selector string.
            root: Optional subtree root.

        Returns:
            Matching element nodes in document order.

        """
        scope = root if root is not None else self._document_root
        if scope is None:
            return []
        nodes = _collect_all(selector, scope)
        return nodes

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

    def add_document_event_listener(
        self, event_type: str, handler: Any, *, capture: bool = False
    ) -> Callable[[], None]:
        """Add a document-level event listener.

        Args:
            event_type: Event type.
            handler: Event handler.
            capture: Ignored on the server; accepted for interface parity
                with the browser port.

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


def _collect_all(selector: str, scope: DOMNode) -> list[DOMNode]:
    """Collect all nodes matching ``selector`` within ``scope``."""
    try:
        parsed = parse_selector(selector)
    except ValueError:
        return _collect_by_attribute_fallback(selector, scope)
    collected: list[DOMNode] = []
    stack: list[DOMNode] = [scope]
    while stack:
        node = stack.pop()
        if node.nodeType != 1:
            continue
        from webcompy_server.ports._selector import _matches_chain  # type: ignore[attr-defined]

        if any(_matches_chain(node, chain, scope) for chain in parsed):  # type: ignore[arg-type]
            collected.append(node)
        children = node.childNodes
        for index in range(children.length - 1, -1, -1):
            stack.append(children[index])
    return _sort_document_order(collected, scope)


def _sort_document_order(nodes: list[DOMNode], scope: DOMNode) -> list[DOMNode]:
    order: list[DOMNode] = []
    stack: list[DOMNode] = [scope]
    while stack:
        current = stack.pop()
        order.append(current)
        children = current.childNodes
        for index in range(children.length - 1, -1, -1):
            stack.append(children[index])
    index_map = {id(n): i for i, n in enumerate(order)}
    return sorted(nodes, key=lambda n: index_map.get(id(n), len(order)))


def _collect_by_attribute_fallback(selector: str, scope: DOMNode) -> list[DOMNode]:
    """Fallback for attribute-containing selectors on the server virtual DOM."""

    results: list[DOMNode] = []
    stack: list[DOMNode] = [scope]
    while stack:
        node = stack.pop()
        if node.nodeType == 1 and _node_matches_any_group(node, selector):
            results.append(node)
        children = node.childNodes
        for index in range(children.length - 1, -1, -1):
            stack.append(children[index])
    return _sort_document_order(results, scope)


def _node_matches_any_group(node: DOMNode, selector: str) -> bool:
    for group in selector.split(","):
        group = group.strip()
        if group and _matches_attr_group(node, group):
            return True
    return False


def _matches_attr_group(node: DOMNode, group: str) -> bool:

    if ":not(" in group:
        outer, _, inner = group.partition(":not(")
        inner = inner.rstrip(")")
        outer = outer.strip()
        if not _attr_match(node, outer):
            return False
        return not _attr_match(node, inner.strip())
    return _attr_match(node, group)


def _attr_match(node: DOMNode, expr: str) -> bool:
    import re as _re

    expr = expr.strip()
    if not expr:
        return False
    tag: str | None = None
    tag_m = _re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", expr)
    rest = expr
    if tag_m:
        tag = tag_m.group(1).lower()
        rest = expr[len(tag_m.group(1)) :]
        if not rest.strip():
            return node.nodeName.lower() == tag
    rest = rest.strip()
    if tag is not None and not rest:
        return node.nodeName.lower() == tag
    attr_re = _re.compile(r'^\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]')
    has_attr = False
    while rest:
        rest = rest.strip()
        if not rest:
            break
        m = attr_re.match(rest)
        if m is None:
            return False
        has_attr = True
        attr_name = m.group(1)
        attr_value = m.group(2)
        actual = node.getAttribute(attr_name)
        if attr_value is None:
            if actual is None:
                return False
        else:
            if actual != attr_value:
                return False
        rest = rest[m.end() :]
    if has_attr:
        return not (tag is not None and node.nodeName.lower() != tag)
    if tag is not None:
        return node.nodeName.lower() == tag
    return False


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
