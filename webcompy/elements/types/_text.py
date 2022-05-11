from typing import Any, cast
from webcompy.reactive._base import ReactiveBase
from webcompy._browser._modules import browser
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements._dom_objs import DOMNode
from webcompy.exception import WebComPyException


class NewLine(ElementAbstract):
    def __init__(self) -> None:
        super().__init__()

    def _init_node(self) -> DOMNode:
        if browser:
            node: DOMNode | None = None
            existing_node = self._get_existing_node()
            if existing_node:
                if (
                    getattr(existing_node, "__webcompy_prerendered_node__", False)
                    and existing_node.nodeName.lower() == "br"
                ):
                    node = existing_node
                    self._mounted = True
                else:
                    existing_node.remove()
            if not node:
                node = cast(DOMNode, browser.document.createElement("br"))
            node.__webcompy_node__ = True
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _render_html(
        self, newline: bool = False, indent: int = 2, count: int = 0
    ) -> str:
        if newline:
            return (" " * indent * count) + "<br>"
        else:
            return "<br>"


class TextElement(ElementAbstract):
    def __init__(self, text: str | ReactiveBase[Any]) -> None:
        self._text = text
        super().__init__()
        if isinstance(self._text, ReactiveBase):
            self._set_callback_id(self._text.on_after_updating(self._update_text))

    def _get_text(self) -> str:
        if isinstance(self._text, ReactiveBase):
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
                    existing_node.remove()
            node = browser.document.createTextNode(self._get_text())
            node.__webcompy_node__ = True
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _update_text(self, new_text: str):
        node = self._get_node()
        if node:
            node.textContent = new_text

    def _render_html(
        self, newline: bool = False, indent: int = 2, count: int = 0
    ) -> str:
        if newline:
            return (" " * indent * count) + self._get_text()
        else:
            return self._get_text()
