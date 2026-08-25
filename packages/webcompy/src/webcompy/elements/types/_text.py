"""Text, line break, and raw HTML leaf elements."""

from __future__ import annotations

from typing import Any

from webcompy.di import inject
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.signal import SignalBase


class NewLine(ElementAbstract):
    """Element rendering as a ``<br>`` DOM node."""

    def __init__(self) -> None:
        super().__init__()

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == "br"

    def _init_node(self) -> DOMNode:
        existing_node = self._get_existing_node()
        if existing_node:
            if (
                getattr(existing_node, "__webcompy_prerendered_node__", False)
                and existing_node.nodeName.lower() == "br"
            ):
                self._adopt_node(existing_node)
                return existing_node
            elif not getattr(existing_node, "__webcompy_node__", False):
                from webcompy.hydration import record_mismatch

                record_mismatch(
                    "tag",
                    "br",
                    getattr(existing_node, "nodeName", None),
                    self._get_belonging_component(),
                )
                existing_node.remove()
        node = self._create_node()
        self._init_new_node(node)
        return node

    def _create_node(self) -> DOMNode:
        return inject(DOM_PORT_KEY).create_element("br")


class TextElement(ElementAbstract):
    """Text node element whose content may track a reactive value.

    Args:
        text: Static string rendered as a single text node, or a reactive
            value whose changes update the node's text content.

    """

    def __init__(self, text: str | SignalBase[Any]) -> None:
        self._text = text
        super().__init__()
        if isinstance(self._text, SignalBase):
            self._add_callback_node(self._text.on_after_updating(self._update_text))

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        current_text = self._get_text()
        if node.textContent != current_text:
            from webcompy.hydration import record_mismatch

            record_mismatch(
                "text",
                current_text,
                node.textContent,
                self._get_belonging_component(),
            )
            node.textContent = current_text

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == "#text"

    def _get_text(self) -> str:
        if isinstance(self._text, SignalBase):
            value = self._text.value
            if value is None:
                return ""
            text = value if isinstance(value, str) else str(value)
        else:
            text = self._text
        return text

    def _init_node(self) -> DOMNode:
        existing_node = self._get_existing_node()
        if existing_node:
            if (
                getattr(existing_node, "__webcompy_prerendered_node__", False)
                and existing_node.nodeName.lower() == "#text"
            ):
                self._adopt_node(existing_node)
                return existing_node
            # preserve framework-managed sibling nodes at this index
            elif not getattr(existing_node, "__webcompy_node__", False):
                from webcompy.hydration import record_mismatch

                record_mismatch(
                    "tag",
                    "#text",
                    getattr(existing_node, "nodeName", None),
                    self._get_belonging_component(),
                )
                existing_node.remove()
        node = self._create_node()
        self._init_new_node(node)
        return node

    def _create_node(self) -> DOMNode:
        return inject(DOM_PORT_KEY).create_text_node(self._get_text())

    def _update_text(self, new_text: Any):
        node = self._get_node()
        if node:
            if new_text is None:
                node.textContent = ""
            else:
                node.textContent = new_text if isinstance(new_text, str) else str(new_text)


class RawHTMLElement(ElementAbstract):
    def __init__(self, html: str | SignalBase[Any], *, wrapper: str = "span") -> None:
        self._html = html
        self._wrapper = wrapper
        super().__init__()
        if isinstance(self._html, SignalBase):
            self._add_callback_node(self._html.on_after_updating(self._update_html))

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        value = self._get_html()
        current = node.innerHTML if hasattr(node, "innerHTML") else node.textContent
        if current != value and not self._matches_canonical(node, value):
            from webcompy.hydration import record_mismatch

            record_mismatch(
                "raw_html",
                value,
                current,
                self._get_belonging_component(),
            )
            self._apply_html(node)

    def _matches_canonical(self, node: DOMNode, value: str) -> bool:
        if not hasattr(node, "innerHTML"):
            return False
        tmp = inject(DOM_PORT_KEY).create_element(self._wrapper)
        tmp.innerHTML = value
        return node.innerHTML == tmp.innerHTML

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == self._wrapper

    def _init_node(self) -> DOMNode:
        existing_node = self._get_existing_node()
        if existing_node:
            if (
                getattr(existing_node, "__webcompy_prerendered_node__", False)
                and existing_node.nodeName.lower() == self._wrapper
            ):
                self._adopt_node(existing_node)
                return existing_node
            # preserve framework-managed sibling nodes at this index
            elif not getattr(existing_node, "__webcompy_node__", False):
                from webcompy.hydration import record_mismatch

                record_mismatch(
                    "tag",
                    self._wrapper,
                    getattr(existing_node, "nodeName", None),
                    self._get_belonging_component(),
                )
                existing_node.remove()
        node = self._create_node()
        self._init_new_node(node)
        return node

    def _create_node(self) -> DOMNode:
        node = inject(DOM_PORT_KEY).create_element(self._wrapper)
        self._apply_html(node)
        return node

    def _apply_html(self, node: DOMNode) -> None:
        value = self._get_html()
        if hasattr(node, "innerHTML"):
            node.innerHTML = value
        else:
            node.textContent = value

    def _get_html(self) -> str:
        if isinstance(self._html, SignalBase):
            value = self._html.value
            return value if isinstance(value, str) else str(value)
        return self._html

    def _update_html(self, _new_html: Any) -> None:
        node = self._get_node()
        if node:
            self._apply_html(node)
