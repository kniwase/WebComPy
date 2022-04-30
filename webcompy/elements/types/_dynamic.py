from typing import NoReturn
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._base import ElementWithChildren
from webcompy.exception import WebComPyException


class DynamicElement(ElementWithChildren):
    @property
    def _node_count(self) -> int:
        return sum(child._node_count for child in self._children)

    def _create_child_element(self, parent: ElementWithChildren, child: ElementChildren):
        child_element = super()._create_child_element(parent, child)
        if isinstance(child_element, DynamicElement):
            raise WebComPyException("Nested DynamicElement is not allowed.")
        return child_element

    def _init_node(self) -> NoReturn:
        raise WebComPyException("'DynamicElement' does not have its own node.")

    def _get_node(self) -> NoReturn:
        raise WebComPyException("'DynamicElement' does not have its own node.")

    def _render_html(self, count: int, indent: int) -> str:
        return "\n".join(child._render_html(count, indent) for child in self._children)
