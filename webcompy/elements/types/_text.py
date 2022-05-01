from typing import Any, cast
from webcompy.reactive._base import ReactiveBase
from webcompy.brython import browser, DOMNode
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.exception import WebComPyException


class NewLine(ElementAbstract):
    def __init__(self) -> None:
        super().__init__()

    def _init_node(self) -> DOMNode:
        if browser:
            node = browser.html.BR()
            node.__webcompy_node__ = True
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _render_html(self, count: int, indent: int) -> str:
        return (" " * indent * count) + "<br>"


class _HTMLTextElement(DOMNode):
    textContent: str


class TextElement(ElementAbstract):
    _node_cache: _HTMLTextElement | None

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
        return text.replace("\n", " ")

    def _init_node(self) -> DOMNode:
        if browser:
            node = browser.document.createTextNode(self._get_text())
            node.__webcompy_node__ = True
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _update_text(self, new_text: str):
        node = self._get_node()
        if node:
            node.textContent = new_text

    def _get_node(self) -> _HTMLTextElement:
        return cast(_HTMLTextElement, super()._get_node())

    def _render_html(self, count: int, indent: int) -> str:
        return (" " * indent * count) + self._get_text()
