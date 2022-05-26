from __future__ import annotations
from typing import Any
from webcompy.elements._dom_objs import DOMNode
from webcompy.exception import WebComPyException


class DomNodeRef:
    _node: DOMNode | None

    def __init__(self) -> None:
        self._node = None

    @property
    def element(self) -> DOMNode:
        if self._node is None:
            raise WebComPyException("DomNodeRef is not initialized yet.")
        return self._node

    def __init_node__(self, node: DOMNode):
        self._node = node

    def __reset_node__(self):
        self._node = None

    def __getattr__(self, name: str) -> Any:
        if name in {"element", "__init_node__", "__reset_node__"}:
            return super().__getattribute__(name)
        else:
            return getattr(self._node, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_node":
            super().__setattr__(name, value)
        elif name in {"element", "__init_node__", "__reset_node__"}:
            raise AttributeError(f"'{name}' is readonly attribute.")
        else:
            setattr(self._node, name, value)

    def __dir__(self):
        if self._node is None:
            return super().__dir__()
        else:
            return {
                *dir(self._node),
                "element",
                "__init_node__",
                "__reset_node__",
            }
