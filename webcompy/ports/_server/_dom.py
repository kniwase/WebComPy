from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.ports._dom import DOMNode, DOMPort


class ServerDOMPort(DOMPort):
    def create_element(self, tag: str) -> DOMNode:
        raise WebComPyException("DOM element creation is not available outside the browser")

    def create_text_node(self, text: str) -> DOMNode:
        raise WebComPyException("DOM text node creation is not available outside the browser")

    def query_selector(self, selector: str) -> DOMNode | None:
        return None

    def get_element_by_id(self, element_id: str) -> DOMNode | None:
        return None

    def set_title(self, title: str) -> None:
        pass

    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        return lambda: None
