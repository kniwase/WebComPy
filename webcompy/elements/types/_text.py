from __future__ import annotations

from typing import Any, cast

from webcompy._browser._modules import browser
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.exception import WebComPyException
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
        if browser:
            existing_node = self._get_existing_node()
            if existing_node:
                if (
                    getattr(existing_node, "__webcompy_prerendered_node__", False)
                    and existing_node.nodeName.lower() == "br"
                ):
                    self._adopt_node(existing_node)
                    return existing_node
                else:
                    existing_node.remove()
            node = self._create_node()
            self._init_new_node(node)
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _create_node(self) -> DOMNode:
        if browser:
            return cast("DOMNode", browser.document.createElement("br"))
        else:
            raise WebComPyException("Not in Browser environment.")

    def _render_html(self, newline: bool = False, indent: int = 2, count: int = 0) -> str:
        if newline:
            return (" " * indent * count) + "<br>"
        else:
            return "<br>"


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
        if browser:
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
        else:
            raise WebComPyException("Not in Browser environment.")

    def _create_node(self) -> DOMNode:
        if browser:
            return cast("DOMNode", browser.document.createTextNode(self._get_text()))
        else:
            raise WebComPyException("Not in Browser environment.")

    def _update_text(self, new_text: str):
        if browser:
            node = self._get_node()
            if node:
                node.textContent = new_text
        else:
            self._text = new_text

    def _render_html(self, newline: bool = False, indent: int = 2, count: int = 0) -> str:
        if newline:
            return (" " * indent * count) + self._get_text()
        else:
            return self._get_text()
