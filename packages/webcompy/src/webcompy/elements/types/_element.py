from __future__ import annotations

from collections.abc import Callable, Iterable
from inspect import iscoroutinefunction
from typing import Any, cast

from webcompy.aio import resolve_async
from webcompy.di import inject
from webcompy.elements._bind import expand_bind_attr
from webcompy.elements._dom_objs import DOMEvent, DOMNode
from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
    EventHandler,
)
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._base import ElementWithChildren
from webcompy.elements.types._refference import DomNodeRef
from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY
from webcompy.signal import SignalBase
from webcompy.signal._graph import consumer_destroy


def _generate_event_handler(_event_handler: EventHandler, element: ElementBase) -> Callable[[DOMEvent], Any]:
    def _route_error(err: Exception) -> None:
        from webcompy.elements.types._error_boundary import route_error_sync

        route_error_sync(element, err, is_event_error=True)

    def event_handler(ev: Any):
        if iscoroutinefunction(_event_handler):
            resolve_async(_event_handler(ev), on_error=_route_error)
        else:
            try:
                _event_handler(ev)
            except Exception as err:
                _route_error(err)

    return inject(FFI_PORT_KEY).create_proxy(event_handler)


_WEBCOMPY_INTERNAL_ATTRS = {"id", "webcompy-component"}
for _i in range(100):
    _WEBCOMPY_INTERNAL_ATTRS.add(f"webcompy-cid-{_i}")
_WEBCOMPY_INTERNAL_ATTRS = frozenset(_WEBCOMPY_INTERNAL_ATTRS)


class ElementBase(ElementWithChildren):
    _ref: DomNodeRef | None
    _event_handlers_added: dict[str, Any]
    _bind_property_attrs: set[str]
    _bind_property_callbacks: list[tuple[SignalBase, str]]

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        current_attrs = self._get_processed_attrs()
        existing_attr_names = set(node.getAttributeNames())
        preserve_all = self._preserves_all_node_attributes()
        for name in existing_attr_names - set(current_attrs.keys()) - _WEBCOMPY_INTERNAL_ATTRS:
            if preserve_all and not name.startswith("webcompy-"):
                continue
            from webcompy.hydration import record_mismatch

            record_mismatch("attribute", None, node.getAttribute(name), self._get_belonging_component())
            node.removeAttribute(name)
        for name, value in current_attrs.items():
            if value is not None:
                existing = node.getAttribute(name)
                if existing != value:
                    from webcompy.hydration import record_mismatch

                    record_mismatch("attribute", value, existing, self._get_belonging_component())
                    node.setAttribute(name, value)
            elif node.hasAttribute(name):
                from webcompy.hydration import record_mismatch

                record_mismatch("attribute", None, node.getAttribute(name), self._get_belonging_component())
                node.removeAttribute(name)
        for name, value in self._attrs.items():
            if isinstance(value, SignalBase):
                self._add_callback_node(value.on_after_updating(self._generate_attr_updater(name)))
        self._register_bind_property_callbacks()
        self._event_handlers_added = {}
        for name, func in self._event_handlers.items():
            event_handler = _generate_event_handler(func, self)
            node.addEventListener(name, event_handler, False)
            self._event_handlers_added[name] = event_handler
        if self._ref:
            self._ref.__init_node__(node)

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == self._tag_name

    def _preserves_all_node_attributes(self) -> bool:
        return False

    def _init_node(self) -> DOMNode:
        existing_node = self._get_existing_node()
        if existing_node:
            if (
                getattr(existing_node, "__webcompy_prerendered_node__", False)
                and existing_node.nodeName.lower() == self._tag_name
            ):
                self._adopt_node(existing_node)
                return existing_node
            # preserve framework-managed sibling nodes at this index
            elif not getattr(existing_node, "__webcompy_node__", False):
                from webcompy.hydration import record_mismatch

                record_mismatch(
                    "tag",
                    self._tag_name,
                    getattr(existing_node, "nodeName", None),
                    self._get_belonging_component(),
                )
                existing_node.remove()
        node = self._create_node()
        self._init_new_node(node)
        return node

    def _create_node(self) -> DOMNode:
        return inject(DOM_PORT_KEY).create_element(self._tag_name)

    def _init_new_node(self, node: DOMNode) -> None:
        node.__webcompy_node__ = True
        for name, value in self._get_processed_attrs().items():
            if value is not None:
                node.setAttribute(name, value)
        for name, value in self._attrs.items():
            if isinstance(value, SignalBase):
                self._add_callback_node(value.on_after_updating(self._generate_attr_updater(name)))
        self._register_bind_property_callbacks()
        self._event_handlers_added = {}
        for name, func in self._event_handlers.items():
            event_handler = _generate_event_handler(func, self)
            node.addEventListener(name, event_handler, False)
            self._event_handlers_added[name] = event_handler
        if self._ref:
            self._ref.__init_node__(node)

    def _generate_attr_updater(self, name: str):
        bind_property_attrs = getattr(self, "_bind_property_attrs", set())

        def update_attr(new_value: Any, name: str = name):
            node = self._get_node()
            if node is not None:
                value = self._proc_attr(new_value)
                if value is None:
                    node.removeAttribute(name)
                else:
                    node.setAttribute(name, value)
                if name in bind_property_attrs:
                    if name == "checked":
                        node.checked = bool(new_value)
                    else:
                        node.value = value or ""

        return update_attr

    def _register_bind_property_callbacks(self) -> None:
        for signal, prop_name in getattr(self, "_bind_property_callbacks", ()):
            self._add_callback_node(signal.on_after_updating(self._generate_property_updater(prop_name)))

    def _generate_property_updater(self, name: str):
        def update_property(new_value: Any, name: str = name):
            node = self._get_node()
            if node is not None:
                if name == "checked":
                    node.checked = bool(new_value)
                else:
                    node.value = self._proc_attr(new_value) or ""

        return update_property

    def _init_children(self, children: Iterable[ElementChildren]):
        for idx in range(self._children_length - 1, -1, -1):
            self._pop_child(idx)
        for child in children:
            if child is not None:
                self._append_child(child)

    def _detach_from_node(self) -> None:
        node = self._node_cache
        if node:
            for name, handler in self._event_handlers_added.items():
                node.removeEventListener(name, handler)
                if hasattr(handler, "destroy"):
                    handler.destroy()
            self._event_handlers_added.clear()
        for cb in self._callback_nodes:
            consumer_destroy(cb)
        self._callback_nodes.clear()
        if self._ref:
            self._ref.__reset_node__()
        self._node_cache = None
        self._mounted = None
        self.__purge_signal_members__()

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        node = self._node_cache
        for name, event_handler in self._event_handlers_added.items():
            if node is not None:
                node.removeEventListener(name, event_handler)
            if hasattr(event_handler, "destroy"):
                event_handler.destroy()
        if self._ref is not None:
            self._ref.__reset_node__()
        super()._remove_element(recursive, remove_node)


class Element(ElementBase):
    def __init__(
        self,
        tag_name: HtmlTags,
        attrs: dict[str, AttrValue] | None = None,
        events: dict[str, EventHandler] | None = None,
        ref: DomNodeRef | None = None,
        children: Iterable[ElementChildren] | None = None,
        *,
        preserve_children: bool = False,
    ) -> None:
        self._tag_name = cast("HtmlTags", tag_name.lower())
        attrs = attrs if attrs else dict()
        events = events if events else dict()
        children = list(children) if children else list()
        self._bind_property_attrs: set[str] = set()
        self._bind_property_callbacks: list[tuple[SignalBase, str]] = []
        if ":bind" in attrs:
            self._bind_property_attrs, self._bind_property_callbacks = expand_bind_attr(
                self._tag_name, attrs, events, children
            )
        self._attrs = attrs
        self._event_handlers = events
        self._ref = ref
        self._preserve_children = preserve_children
        self._children = []
        super().__init__()
        self._init_children(children)
