"""Teleport element relocating its children to a remote DOM target."""

from __future__ import annotations

from typing import TypedDict, cast

from webcompy import logging
from webcompy.di import inject
from webcompy.di._keys import _TELEPORT_REGISTRY_KEY
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _position_element_nodes
from webcompy.elements.types._text import TextElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, DOM_PORT_KEY
from webcompy.signal import SignalBase
from webcompy.signal._graph import consumer_destroy
from webcompy.utils._environment import ENVIRONMENT


class _TeleportTargetRegistry:
    def __init__(self) -> None:
        self._registrations: dict[int, list[TeleportElement]] = {}

    def register(self, target: DOMNode, teleport: TeleportElement) -> None:
        registrations = self._registrations.setdefault(id(target), [])
        if teleport not in registrations:
            registrations.append(teleport)

    def unregister(self, target: DOMNode, teleport: TeleportElement) -> None:
        registrations = self._registrations.get(id(target))
        if registrations is None:
            return
        if teleport in registrations:
            registrations.remove(teleport)
        if not registrations:
            del self._registrations[id(target)]

    def shared_target_teleports(self, target: DOMNode) -> list[TeleportElement]:
        return list(self._registrations.get(id(target), ()))


def _mounted_direct_count(target: DOMNode, element: ElementAbstract) -> int:
    if isinstance(element, TeleportElement):
        if element._inline:
            return sum(_mounted_direct_count(target, child) for child in element._children)
        if element._target_node is not target:
            node = element._node_cache
            if node is None or node.parentNode is not target:
                return 0
            return 1
        return sum(_mounted_direct_count(target, child) for child in element._children)
    if isinstance(element, DynamicElement):
        return sum(_mounted_direct_count(target, child) for child in element._children)
    node = element._node_cache
    if node is None or node.parentNode is not target:
        return 0
    return 1


class TeleportProps(TypedDict):
    to: str


class TeleportElement(DynamicElement):
    """Element rendering its children inside a remote DOM target.

    The children are mounted into the first element matching the ``to`` CSS
    selector, while an anchor comment node marks the position in the source
    tree (or the children render inline when no target matches). Targets
    shared by multiple teleports interleave their children by registration.

    Args:
        props: Mapping holding the ``to`` CSS selector.
        *children: Child elements, strings, or reactive values moved to the
            target container.

    Raises:
        ValueError: When the ``to`` selector is not a non-empty static string.

    """

    _ANCHOR_DATA = "webcompy-teleport-anchor"

    def __init__(self, props: TeleportProps, *children: ElementChildren) -> None:
        to: object = props.get("to") if isinstance(props, dict) else None
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
        node = inject(DOM_PORT_KEY).create_comment(self._ANCHOR_DATA)
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
            registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
            if registry is not None:
                registry.register(target, self)

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
            self._mounted = True
        else:
            self._mount_node()
            if not self._children_rendered:
                target = self._target_node
                if target is None:
                    return
                self._children_rendered = True
                idx = target.childNodes.length
                for child in self._children:
                    child._node_idx = idx
                    if child._mounted is None:
                        await child._render()
                    idx += child._node_count
            self._re_index_shared_target()
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
            if existing and not getattr(existing, "__webcompy_node__", False):
                existing.remove()
            self._node_cache = self._create_node()
        if not self._children_rendered:
            # The adopted anchor schedules its own render; the post-hydration
            # pass re-renders the tree again, but that second run is a no-op
            # thanks to the _children_rendered/_mounted guards below.
            # Scheduling unconditionally also makes the fresh-anchor path
            # (parser-merged anchors) self-contained instead of relying on the
            # app-level post-hydration render pass.
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            task = scheduler.schedule(self._render(), render=True)
            self._pending_render_tasks.append((self, task))
            task.add_done_callback(self._on_hydrate_render_done)

    def _node_matches_existing(self, existing: DOMNode) -> bool:
        return existing.nodeName.lower() == "#comment" and (existing.textContent or "") == self._ANCHOR_DATA

    def _adopt_node(self, node: DOMNode) -> None:
        self._node_cache = node
        self._mounted = True
        node.__webcompy_node__ = True

    def _re_index_children(self, recursive: bool = False) -> None:
        if self._inline:
            super()._re_index_children(recursive)
            self._parent._re_index_children(False)
            return
        if self._target_node is None:
            super()._re_index_children(recursive)
            return
        self._re_index_shared_target()

    def _re_index_shared_target(self) -> None:
        target = self._target_node
        if target is None:
            return
        registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
        if registry is None:
            return
        teleports = registry.shared_target_teleports(target)
        if not teleports:
            return
        base = target.childNodes.length - sum(_mounted_direct_count(target, teleport) for teleport in teleports)
        for teleport in teleports:
            idx = base
            for child in teleport._children:
                child._node_idx = idx
                idx += _mounted_direct_count(target, child)
            for child in teleport._children:
                if isinstance(child, DynamicElement):
                    child._re_index_children(True)
            base = idx

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
        target = self._target_node
        if target is not None:
            registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
            if registry is not None:
                registry.unregister(target, self)
            self._re_index_shared_target()


Teleport = TeleportElement
