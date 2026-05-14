from __future__ import annotations

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

    def schedule_macro_task(self, callback: Any) -> None:
        pass
