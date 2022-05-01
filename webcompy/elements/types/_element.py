from typing import Any, Iterable, cast
from webcompy.reactive._base import ReactiveBase
from webcompy.brython import browser, DOMNode
from webcompy.elements.types._base import ElementWithChildren
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.typealias._element_property import (
    ElementChildren,
    AttrValue,
    EventHandler,
)
from webcompy.elements.types._refference import DomNodeRef
from webcompy.aio import resolve_async
from webcompy.exception import WebComPyException


class ElementBase(ElementWithChildren):
    _ref: DomNodeRef | None

    def _init_node(self) -> DOMNode:
        if browser:
            node: DOMNode = browser.document.createElement(self._tag_name)
            node.__webcompy_node__ = True
            for name, value in self._get_processed_attrs().items():
                if value is not None:
                    node.setAttribute(name, value)
            for name, value in self._attrs.items():
                if isinstance(value, ReactiveBase):
                    self._set_callback_id(
                        value.on_after_updating(self._generate_attr_updater(name))
                    )
            for name, callback in self._event_handlers.items():
                node.bind(name, lambda ev: resolve_async(callback(ev)))
            if self._ref:
                self._ref.__init_node__(node)
            return node
        else:
            raise WebComPyException("Not in Browser environment.")

    def _generate_attr_updater(self, name: str):
        def update_attr(new_value: Any, name: str = name):
            node = self._get_node()
            if node is not None:
                value = self._proc_attr(new_value)
                if value is None:
                    node.removeAttribute(name)
                else:
                    node.setAttribute(name, value)

        return update_attr

    def _init_children(self, children: Iterable[ElementChildren]):
        for idx in range(self._children_length - 1, -1, -1):
            self._pop_child(idx)
        for child in children:
            if child is not None:
                self._append_child(child)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        if self._ref is not None:
            self._ref.__reset_node__()
        super()._remove_element(recursive, remove_node)


class Element(ElementBase):
    def __init__(
        self,
        tag_name: HtmlTags,
        attrs: dict[str, AttrValue] = {},
        events: dict[str, EventHandler] = {},
        ref: DomNodeRef | None = None,
        children: Iterable[ElementChildren] = [],
    ) -> None:
        self._tag_name = cast(HtmlTags, tag_name.lower())
        self._attrs = attrs if attrs else dict()
        self._event_handlers = events if events else dict()
        self._ref = ref
        self._children = []
        super().__init__()
        self._init_children(children if children else list())
