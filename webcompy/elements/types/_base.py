from __future__ import annotations
from typing import Any
from webcompy.reactive._base import ReactiveBase
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.typealias._element_property import (
    ElementChildren,
    AttrValue,
    EventHandler,
)
from webcompy.elements.types._text import TextElement


class ElementWithChildren(ElementAbstract):
    _tag_name: HtmlTags
    _attrs: dict[str, AttrValue] = {}
    _event_handlers: dict[str, EventHandler] = {}
    _children: list[ElementAbstract] = []
    __parent: ElementWithChildren

    def __init__(self) -> None:
        self._node_cache = None
        self._callback_ids: set[int] = set()

    @property
    def _parent(self) -> "ElementWithChildren":
        return self.__parent

    @_parent.setter
    def _parent(self, parent: "ElementWithChildren"):  # type: ignore
        self.__parent = parent

    def _render(self):
        super()._render()
        for child in self._children:
            child._render()
        if (node := self._get_node()) is not None:
            for _ in range(node.childNodes.length - self._children_length):
                node.childNodes[-1].remove()

    def _get_processed_attrs(self):
        attrs = {name: self._proc_attr(value) for name, value in self._attrs.items()}
        if "webcompy-component" not in self._attrs and self._get_belonging_component():
            attrs["webcompy-cid-" + self._get_belonging_component()] = ""
        return attrs

    def _proc_attr(self, value: AttrValue):
        if isinstance(value, ReactiveBase):
            obj = value.value
        else:
            obj = value
        if isinstance(obj, bool):
            return "" if obj else None
        elif isinstance(obj, int):
            return str(obj)
        else:
            return str(obj)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        super()._remove_element(recursive, remove_node)
        if recursive:
            for child in self._children:
                child._remove_element(True, False)

    def _create_child_element(
        self,
        parent: "ElementWithChildren",
        node_idx: int | None,
        child: ElementChildren,
    ):
        if child is None:
            return None
        elif isinstance(child, (str, ReactiveBase)):
            element = TextElement(child)
        else:
            element = child
        if node_idx is not None:
            element._node_idx = node_idx
        element._parent = parent
        return element

    @property
    def _children_length(self) -> int:
        return sum(child._node_count for child in self._children)

    def _re_index_children(self, recursive: bool = False):
        idx = 0
        for c_idx in range(len(self._children)):
            self._children[c_idx]._node_idx = idx
            idx += self._children[c_idx]._node_count
        if recursive:
            for child in self._children:
                if isinstance(child, ElementWithChildren):
                    child._re_index_children(True)

    def _append_child(self, child: ElementChildren):
        if self._children_length == 0:
            node_idx = 0
        else:
            node_idx = self._children[-1]._node_idx + self._children[-1]._node_count
        child_ele = self._create_child_element(self, node_idx, child)
        if child_ele is not None:
            self._children.append(child_ele)

    def _insert_child(self, index: int, child: ElementChildren):
        child_ele = self._create_child_element(self, None, child)
        if child_ele is not None:
            self._children.insert(index, child_ele)
            self._re_index_children(False)

    def _pop_child(self, index: int, re_index: bool = False):
        self._children[index]._remove_element()
        del self._children[index]
        if re_index:
            self._re_index_children(False)

    def _clear_node_cache(self, recursive: bool = True):
        super()._clear_node_cache()
        if recursive:
            for child in self._children:
                child._clear_node_cache(True)

    def _get_belonging_component(self) -> str:
        return self._parent._get_belonging_component()

    def _get_belonging_components(self) -> tuple[Any, ...]:
        return self._parent._get_belonging_components()

    def _render_html(
        self, newline: bool = False, indent: int = 2, count: int = 0
    ) -> str:
        attrs: str = " ".join(
            f'{name}="{value}"' if value else name
            for name, value in self._get_processed_attrs().items()
            if value is not None
        )
        separator = "\n" if newline else ""
        indent_text = (" " * indent * count) if newline else ""
        return separator.join(
            (
                f'{indent_text}<{self._tag_name}{" " + attrs if attrs else ""}>',
                separator.join(
                    child._render_html(newline, indent, count + 1)
                    for child in self._children
                ),
                f"{indent_text}</{self._tag_name}>",
            )
        )
