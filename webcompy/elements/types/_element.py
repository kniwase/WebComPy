from inspect import iscoroutinefunction
from typing import Any, Callable, Iterable, cast
from webcompy.reactive._base import ReactiveBase
from webcompy._browser._modules import browser
from webcompy.elements.types._base import ElementWithChildren
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.typealias._element_property import (
    ElementChildren,
    AttrValue,
    EventHandler,
)
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements._dom_objs import DOMNode, DOMEvent
from webcompy.aio import resolve_async
from webcompy.exception import WebComPyException
from webcompy._browser._modules import browser_pyscript


def _generate_event_handler(_event_handler: EventHandler) -> Callable[[DOMEvent], Any]:
    def event_handler(ev: Any):
        if iscoroutinefunction(_event_handler):
            resolve_async(_event_handler(ev))
        else:
            _event_handler(ev)

    if browser_pyscript:
        return browser_pyscript.pyodide.create_proxy(event_handler)
    else:
        return event_handler


class ElementBase(ElementWithChildren):
    _ref: DomNodeRef | None
    _event_handlers_added: dict[str, Any]

    def _init_node(self) -> DOMNode:
        if browser:
            node: DOMNode | None = None
            existing_node = self._get_existing_node()
            if existing_node:
                if (
                    getattr(existing_node, "__webcompy_prerendered_node__", False)
                    and existing_node.nodeName.lower() == self._tag_name
                ):
                    node = existing_node
                    self._mounted = True
                    attr_names_to_remove = set(
                        name
                        for name, value in self._get_processed_attrs().items()
                        if value is None and name in tuple(node.getAttributeNames())
                    )
                    attr_names_to_remove.update(
                        name
                        for name in tuple(node.getAttributeNames())
                        if name not in self._get_processed_attrs().keys()
                    )
                    for name in attr_names_to_remove:
                        node.removeAttribute(name)
                else:
                    existing_node.remove()
            if not node:
                node = cast(DOMNode, browser.document.createElement(self._tag_name))
            node.__webcompy_node__ = True
            for name, value in self._get_processed_attrs().items():
                if value is not None:
                    node.setAttribute(name, value)
            for name, value in self._attrs.items():
                if isinstance(value, ReactiveBase):
                    self._set_callback_id(
                        value.on_after_updating(self._generate_attr_updater(name))
                    )
            self._event_handlers_added = {}
            for name, func in self._event_handlers.items():
                event_handler = _generate_event_handler(func)
                node.addEventListener(name, event_handler, False)
                self._event_handlers_added[name] = event_handler
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
        node = self._get_node()
        for name, event_handler in self._event_handlers_added.items():
            node.removeEventListener(name, event_handler)
            if browser_pyscript:
                event_handler.destroy()
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
