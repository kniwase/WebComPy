from abc import abstractmethod
from typing import NoReturn
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._base import ElementWithChildren
from webcompy.exception import WebComPyException


class DynamicElement(ElementWithChildren):
    __parent: ElementWithChildren

    @property
    def _node_count(self) -> int:
        return sum(child._node_count for child in self._children)

    def _create_child_element(
        self,
        parent: "ElementWithChildren",
        node_idx: int | None,
        child: ElementChildren,
    ):
        child_element = super()._create_child_element(parent, node_idx, child)
        if isinstance(child_element, DynamicElement):
            raise WebComPyException("Nested DynamicElement is not allowed.")
        return child_element

    def _init_node(self) -> NoReturn:
        raise WebComPyException("'DynamicElement' does not have its own node.")

    def _get_node(self) -> NoReturn:
        raise WebComPyException("'DynamicElement' does not have its own node.")

    def _render_html(
        self, newline: bool = False, indent: int = 2, count: int = 0
    ) -> str:
        return ("\n" if newline else "").join(
            child._render_html(newline, indent, count) for child in self._children
        )

    @property
    def _parent(self) -> "ElementWithChildren":
        return self.__parent

    @_parent.setter
    def _parent(self, parent: "ElementWithChildren"):
        self.__parent = parent
        self._on_set_parent()

    @abstractmethod
    def _on_set_parent(self):
        ...
