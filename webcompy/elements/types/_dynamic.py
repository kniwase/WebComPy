from __future__ import annotations

from abc import abstractmethod

from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._base import ElementWithChildren
from webcompy.signal._graph import consumer_destroy


class DynamicElement(ElementWithChildren):
    __parent: ElementWithChildren

    @property
    def _node_count(self) -> int:
        return sum(child._node_count for child in self._children)

    def _get_node(self) -> DOMNode:
        return self._parent._get_node()

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        for callback_node in self._callback_nodes:
            consumer_destroy(callback_node)
        self._clear_node_cache(False)
        self.__purge_signal_members__()
        if recursive:
            for child in self._children:
                child._remove_element(True, True)

    def _render_html(self, newline: bool = False, indent: int = 2, count: int = 0) -> str:
        return ("\n" if newline else "").join(child._render_html(newline, indent, count) for child in self._children)

    @property
    def _parent(self) -> ElementWithChildren:
        return self.__parent

    @_parent.setter
    def _parent(self, parent: ElementWithChildren):
        self.__parent = parent
        self._on_set_parent()

    @abstractmethod
    def _on_set_parent(self): ...


def _position_element_nodes(
    element: ElementAbstract,
    parent_node: DOMNode,
    start_idx: int,
) -> int:
    if isinstance(element, DynamicElement):
        idx = start_idx
        for child in element._children:
            idx = _position_element_nodes(child, parent_node, idx)
        return idx
    node = element._get_node()
    if node:
        if start_idx < parent_node.childNodes.length:
            ref_node = parent_node.childNodes[start_idx]
            if ref_node is not node:
                parent_node.insertBefore(node, ref_node)
        else:
            parent_node.appendChild(node)
        if not element._mounted:
            element._mounted = True
        return start_idx + element._node_count
    return start_idx + element._node_count
