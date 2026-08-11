from __future__ import annotations

from typing import TypedDict

from webcompy import logging
from webcompy.di import inject
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _position_element_nodes
from webcompy.elements.types._text import TextElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY
from webcompy.signal import SignalBase
from webcompy.signal._graph import consumer_destroy
from webcompy.utils._environment import ENVIRONMENT


class TeleportProps(TypedDict):
    to: str


class TeleportElement(DynamicElement):
    def __init__(self, props: TeleportProps, *children: ElementChildren) -> None:
        to: object = props.get("to") if props else None
        if not isinstance(to, str) or not to:
            raise ValueError("Teleport requires 'to' to be a non-empty static string selector.")
        self._to = to
        self._target_node: DOMNode | None = None
        self._inline = False
        self._resolved = False
        self._children_rendered = False
        normalized: list[ElementAbstract] = []
        for child in children:
            if child is None:
                continue
            if isinstance(child, (str, SignalBase)):
                normalized.append(TextElement(child))
            else:
                normalized.append(child)
        self._pending_children = normalized
        super().__init__()

    @property
    def _node_count(self) -> int:
        if self._inline:
            return sum(child._node_count for child in self._children)
        return 1

    def _on_set_parent(self) -> None:
        if self._pending_children:
            for child in self._pending_children:
                child._parent = self
            self._children = self._pending_children
            self._pending_children = []
        else:
            for child in self._children:
                child._parent = self

    def _get_node(self) -> DOMNode:
        if self._target_node is not None:
            return self._target_node
        return self._parent._get_node()

    def _get_anchor_node(self) -> DOMNode:
        if self._node_cache is None:
            self._node_cache = self._init_node()
        return self._node_cache

    def _init_node(self) -> DOMNode:
        return self._create_node()

    def _create_node(self) -> DOMNode:
        node = inject(DOM_PORT_KEY).create_text_node("")
        self._init_new_node(node)
        return node

    def _mount_node(self) -> None:
        node = self._get_anchor_node()
        if not self._mounted:
            parent_node = self._parent._get_node()
            if self._mounted is None:
                if parent_node.childNodes.length <= self._node_idx:
                    parent_node.appendChild(node)
                else:
                    parent_node.insertBefore(node, parent_node.childNodes[self._node_idx])
            elif self._remount_to:
                parent_node.replaceChild(node, self._remount_to)
                self._remount_to = None
            self._mounted = True
        elif node.parentNode is None:
            parent_node = self._parent._get_node()
            if parent_node.childNodes.length <= self._node_idx:
                parent_node.appendChild(node)
            else:
                parent_node.insertBefore(node, parent_node.childNodes[self._node_idx])

    def _resolve_target(self) -> None:
        self._resolved = True
        target = inject(DOM_PORT_KEY).query_selector(self._to)
        if target is None:
            logging.warning(f"Teleport target '{self._to}' not found; rendering children inline.")
            self._inline = True
        else:
            self._target_node = target

    async def _render(self) -> None:
        if ENVIRONMENT != "pyscript":
            self._mount_node()
            return
        if not self._resolved:
            self._resolve_target()
        if self._inline:
            if self._node_cache is not None and self._node_cache.parentNode is not None:
                self._node_cache.remove()
            if not self._children_rendered:
                self._children_rendered = True
                idx = self._node_idx
                for child in self._children:
                    child._node_idx = idx
                    if child._mounted is None:
                        await child._render()
                    idx += child._node_count
            parent_node = self._parent._get_node()
            idx = self._node_idx
            for child in self._children:
                idx = _position_element_nodes(child, parent_node, idx)
        else:
            self._mount_node()
            if not self._children_rendered:
                self._children_rendered = True
                target = self._target_node
                if target is None:
                    return
                idx = target.childNodes.length
                for child in self._children:
                    child._node_idx = idx
                    if child._mounted is None:
                        await child._render()
                    idx += child._node_count
        self._parent._re_index_children(False)

    def _hydrate_node(self) -> None:
        existing = self._get_existing_node()
        if (
            existing
            and getattr(existing, "__webcompy_prerendered_node__", False)
            and self._node_matches_existing(existing)
        ):
            self._adopt_node(existing)
        else:
            self._node_cache = self._create_node()
        if self._mounted:
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            task = scheduler.schedule(self._render())
            self._pending_render_tasks.append((self, task))
            task.add_done_callback(self._on_hydrate_render_done)

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == "#text"

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True
        if node.textContent:
            node.textContent = ""

    def _re_index_children(self, recursive: bool = False) -> None:
        if not self._inline and self._target_node is not None:
            return
        super()._re_index_children(recursive)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True) -> None:
        self._cancel_pending_render_tasks()
        for callback_node in self._callback_nodes:
            consumer_destroy(callback_node)
        if remove_node and self._node_cache is not None:
            self._node_cache.remove()
        self._clear_node_cache(False)
        self.__purge_signal_members__()
        if recursive:
            for child in self._children:
                child._remove_element(True, True)


Teleport = TeleportElement
