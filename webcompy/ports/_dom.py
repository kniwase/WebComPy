from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DOMNode(ABC):
    @abstractmethod
    def append_child(self, child: DOMNode) -> None: ...
    @abstractmethod
    def remove_child(self, child: DOMNode) -> None: ...
    @abstractmethod
    def insert_before(self, new_node: DOMNode, ref_node: DOMNode) -> None: ...
    @abstractmethod
    def replace_child(self, new_node: DOMNode, old_node: DOMNode) -> None: ...
    @abstractmethod
    def remove(self) -> None: ...

    @abstractmethod
    def set_attribute(self, name: str, value: str) -> None: ...
    @abstractmethod
    def get_attribute(self, name: str) -> str | None: ...
    @abstractmethod
    def remove_attribute(self, name: str) -> None: ...
    @abstractmethod
    def has_attribute(self, name: str) -> bool: ...
    @abstractmethod
    def get_attribute_names(self) -> list[str]: ...

    @abstractmethod
    def add_event_listener(
        self,
        event_type: str,
        handler: Any,
        *,
        capture: bool = False,
    ) -> None: ...
    @abstractmethod
    def remove_event_listener(
        self,
        event_type: str,
        handler: Any,
        *,
        capture: bool = False,
    ) -> None: ...

    @property
    @abstractmethod
    def text_content(self) -> str | None: ...

    @text_content.setter
    @abstractmethod
    def text_content(self, value: str | None) -> None: ...

    @property
    @abstractmethod
    def child_nodes(self) -> DOMNodeList: ...

    @property
    @abstractmethod
    def node_name(self) -> str: ...

    @property
    @abstractmethod
    def node_type(self) -> int: ...

    @property
    @abstractmethod
    def __webcompy_node__(self) -> bool: ...

    @__webcompy_node__.setter
    @abstractmethod
    def __webcompy_node__(self, value: bool) -> None: ...

    @property
    @abstractmethod
    def __webcompy_prerendered_node__(self) -> bool: ...

    @__webcompy_prerendered_node__.setter
    @abstractmethod
    def __webcompy_prerendered_node__(self, value: bool) -> None: ...


class DOMNodeList:
    def __init__(self, nodes: list[DOMNode]) -> None:
        self._nodes = nodes

    @property
    def length(self) -> int:
        return len(self._nodes)

    def __getitem__(self, index: int) -> DOMNode:
        return self._nodes[index]


class DOMPort(ABC):
    @abstractmethod
    def create_element(self, tag: str) -> DOMNode: ...
    @abstractmethod
    def create_text_node(self, text: str) -> DOMNode: ...
    @abstractmethod
    def query_selector(self, selector: str) -> DOMNode | None: ...
    @abstractmethod
    def get_element_by_id(self, element_id: str) -> DOMNode | None: ...
    @abstractmethod
    def set_title(self, title: str) -> None: ...
    @abstractmethod
    def schedule_macro_task(self, callback: Any) -> None: ...
