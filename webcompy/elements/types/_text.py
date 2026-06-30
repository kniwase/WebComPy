from __future__ import annotations

from typing import Any

from webcompy.di import inject
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.signal._base import SignalBase


class NewLine(ElementAbstract):
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
                existing_node.remove()
        node = self._create_node()
        self._init_new_node(node)
        return node

    def _create_node(self) -> DOMNode:
        return inject(DOM_PORT_KEY).create_element("br")


class TextElement(ElementAbstract):
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
            node.textContent = current_text

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == "#text"

    def _get_text(self) -> str:
        if isinstance(self._text, SignalBase):
            value = self._text.value
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
            else:
                existing_node.remove()
        node = self._create_node()
        self._init_new_node(node)
        return node

    def _create_node(self) -> DOMNode:
        return inject(DOM_PORT_KEY).create_text_node(self._get_text())

    def _update_text(self, new_text: Any):
        node = self._get_node()
        if node:
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
        self._apply_html(node)

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
            else:
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
