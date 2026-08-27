"""Teleport element relocating its children to a remote DOM target."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict, cast
from urllib.parse import quote

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

_BLOCK_START_PREFIX = "wc-teleport-block:"
_BLOCK_END_PREFIX = "wc-teleport-block-end:"


@dataclass
class _PendingTeleportEntry:
    """Server-side pending emission entry for one Teleport instance."""

    ordinal: int
    to: str
    teleport: TeleportElement

    @property
    def children(self) -> list[ElementAbstract]:
        """Return the teleport's child elements."""
        return self.teleport._children


@dataclass
class _BlockSlot:
    """Client-side bookkeeping for one teleported block under a target."""

    ordinal: int
    base: int
    teleport: TeleportElement | None = field(default=None)


class _TeleportTargetRegistry:
    def __init__(self) -> None:
        self._registrations: dict[int, list[TeleportElement]] = {}
        self._pending: list[_PendingTeleportEntry] = []
        self._next_ordinal = 0
        self._consumed: set[int] = set()
        self._slots: dict[int, list[_BlockSlot]] = {}

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

    def enqueue_pending(self, to: str, teleport: TeleportElement) -> int:
        """Record a server-side emission request and return its ordinal.

        Args:
            to: The Teleport's ``to`` selector.
            teleport: The Teleport element whose children are emitted.

        Returns:
            The document-order ordinal assigned to this entry.

        """
        entry = _PendingTeleportEntry(self._next_ordinal, to, teleport)
        self._next_ordinal += 1
        self._pending.append(entry)
        return entry.ordinal

    def take_pending_entries(self) -> list[_PendingTeleportEntry]:
        """Drain and return all pending entries in ordinal order.

        Returns:
            Previously pending entries; the queue is emptied.

        """
        entries = self._pending
        self._pending = []
        return entries

    def reserve_ordinal(self) -> int:
        """Reserve the next hydration ordinal for a client Teleport.

        Returns:
            A monotonically increasing ordinal unique within the context.

        """
        ordinal = self._next_ordinal
        self._next_ordinal += 1
        return ordinal

    def is_consumed(self, ordinal: int) -> bool:
        """Return whether ``ordinal`` has already been claimed.

        Args:
            ordinal: Hydration block ordinal.

        Returns:
            ``True`` when previously claimed via :meth:`mark_consumed`.

        """
        return ordinal in self._consumed

    def mark_consumed(self, ordinal: int) -> None:
        """Mark ``ordinal`` as claimed so it cannot be consumed again.

        Args:
            ordinal: Hydration block ordinal.

        Returns:
            ``None``.

        """
        self._consumed.add(ordinal)

    def slots_for(self, target: DOMNode) -> list[_BlockSlot] | None:
        """Return tracked slot ledger for ``target`` or ``None``.

        Args:
            target: Shared target node.

        Returns:
            Ordered slot ledger when any Teleport under this target has a
            claimed/tracked block; otherwise ``None``.

        """
        return self._slots.get(id(target))

    def ensure_slots(self, target: DOMNode) -> list[_BlockSlot]:
        """Return (creating if absent) the ordered slot ledger for ``target``.

        Args:
            target: Shared target node.

        Returns:
            Ordered slot ledger list.

        """
        return self._slots.setdefault(id(target), [])

    def set_slots(self, target: DOMNode, slots: list[_BlockSlot]) -> None:
        """Replace the slot ledger for ``target``.

        Args:
            target: Shared target node.
            slots: New ordered slot ledger.

        Returns:
            ``None``.

        """
        self._slots[id(target)] = slots

    def drop_slots_if_empty(self, target: DOMNode) -> None:
        """Remove the ledger for ``target`` when it holds no slots.

        Args:
            target: Shared target node.

        Returns:
            ``None``.

        """
        slots = self._slots.get(id(target))
        if slots is not None and not slots:
            del self._slots[id(target)]


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


class _TeleportPropsOptional(TypedDict, total=False):
    ssr: bool


class TeleportProps(_TeleportPropsOptional):
    to: str


def block_start_data(ordinal: int, to: str) -> str:
    """Build the start marker comment data for an emitted block.

    Args:
        ordinal: Document-order ordinal of the teleport.
        to: The ``to`` selector of the teleport.

    Returns:
        Comment data string.

    """
    return f"{_BLOCK_START_PREFIX}{ordinal}:{quote(to, safe='')}"


def block_end_data(ordinal: int) -> str:
    """Build the end marker comment data for an emitted block.

    Args:
        ordinal: Document-order ordinal of the teleport.

    Returns:
        Comment data string.

    """
    return f"{_BLOCK_END_PREFIX}{ordinal}"


def _parse_marker_ordinal(data: str) -> int:
    """Extract the ordinal from a block start marker comment data.

    Args:
        data: Start marker comment data (``wc-teleport-block:<n>:...``).

    Returns:
        The parsed ordinal, or ``-1`` when the data is malformed.

    """
    rest = data[len(_BLOCK_START_PREFIX) :]
    head = rest.split(":", 1)[0]
    try:
        return int(head)
    except ValueError:
        return -1


class TeleportElement(DynamicElement):
    """Element rendering its children inside a remote DOM target.

    The children are mounted into the first element matching the ``to`` CSS
    selector, while an anchor comment node marks the position in the source
    tree (or the children render inline when no target matches). Targets
    shared by multiple teleports interleave their children by registration.

    Args:
        props: Mapping holding the ``to`` CSS selector and the optional
            ``ssr`` flag (default ``True``) controlling server-side
            emission of the children into the resolved target.
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
        self._ssr_emit = props.get("ssr", True) is not False
        self._ssr_ordinal = -1
        self._claimed_slot: int | None = None
        self._claimed_anchor: DOMNode | None = None
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
                if self._ssr_emit:
                    self._ssr_ordinal = registry.reserve_ordinal()

    async def _render(self) -> None:
        if ENVIRONMENT != "pyscript":
            self._mount_node()
            if self._ssr_emit:
                registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
                if registry is not None:
                    registry.enqueue_pending(self._to, self)
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
                anchor = self._claimed_anchor
                if anchor is not None and anchor.parentNode is not target:
                    anchor = None
                if anchor is not None:
                    idx = 0
                    while idx < target.childNodes.length and target.childNodes[idx] is not anchor:
                        idx += 1
                else:
                    idx = target.childNodes.length
                for child in self._children:
                    child._node_idx = idx
                    if child._mounted is None:
                        await child._render()
                    idx += child._node_count
                self._claimed_anchor = None
            self._re_index_shared_target()
        self._parent._re_index_children(False)

    def _early_claim_ssr_block(self) -> None:
        if not self._ssr_emit or self._claimed_slot is not None:
            return
        try:
            target = inject(DOM_PORT_KEY).query_selector(self._to)
        except ValueError:
            return
        if target is None:
            return
        self._target_node = target
        registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
        if registry is None:
            return
        registry.register(target, self)
        if self._ssr_ordinal < 0:
            self._ssr_ordinal = registry.reserve_ordinal()
        slot = self._claim_ssr_block(target, registry)
        if slot is None:
            logging.warning(
                f"Teleport SSR block {self._ssr_ordinal} for '{self._to}' not found; mounting via client render."
            )
            return
        registry.mark_consumed(self._ssr_ordinal)
        self._claimed_slot = slot
        remaining = target.childNodes
        self._claimed_anchor = remaining[slot] if slot < remaining.length else None
        slots = registry.ensure_slots(target)
        slots.append(_BlockSlot(self._ssr_ordinal, slot, self))
        slots.sort(key=lambda entry: entry.base)

    def _block_start_marker_data(self) -> str:
        return f"{_BLOCK_START_PREFIX}{self._ssr_ordinal}:{quote(self._to, safe='')}"

    def _find_ssr_block_range(self, target: DOMNode, registry: _TeleportTargetRegistry) -> tuple[int, int] | None:
        children = target.childNodes
        start_index: int | None = None
        for index in range(children.length):
            node = children[index]
            if getattr(node, "nodeType", 0) != 8:
                continue
            data = str(node.textContent or "")
            if (
                start_index is None
                and data == self._block_start_marker_data()
                and not registry.is_consumed(self._ssr_ordinal)
            ):
                start_index = index
                continue
            if data == f"{_BLOCK_END_PREFIX}{self._ssr_ordinal}" and start_index is not None:
                return start_index, index
        return None

    def _claim_ssr_block(self, target: DOMNode, registry: _TeleportTargetRegistry) -> int | None:
        found = self._find_ssr_block_range(target, registry)
        if found is None:
            return None
        slot, end = found
        for index in range(end, slot - 1, -1):
            target.removeChild(target.childNodes[index])
        return slot

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
            self._early_claim_ssr_block()
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
        slots = registry.slots_for(target)
        measured: dict[int, int] = {id(tp): _mounted_direct_count(target, tp) for tp in teleports}
        if slots is None:
            base = target.childNodes.length - sum(measured.values())
            self._assign_block_indices(target, teleports, measured, base)
            return
        ledger = [slot for slot in slots if slot.teleport is not None and id(slot.teleport) in measured]
        untracked = [tp for tp in teleports if all(slot.teleport is not tp for slot in ledger)]
        for teleport in untracked:
            last_end = max((slot.base + measured.get(id(slot.teleport), 0) for slot in ledger), default=None)
            anchor_base = (
                target.childNodes.length - sum(measured.values())
                if not ledger
                else (last_end if last_end is not None else target.childNodes.length)
            )
            slot = _BlockSlot(-1, anchor_base, teleport)
            ledger.append(slot)
        registry.set_slots(target, ledger)
        ledger.sort(key=lambda entry: entry.base)
        position = ledger[0].base
        ordered = []
        for slot in ledger:
            count = measured.get(id(slot.teleport), 0) if slot.teleport is not None else 0
            slot.base = position
            position += count
            ordered.append(slot)
        for slot in ordered:
            if slot.teleport is None or id(slot.teleport) not in measured:
                continue
            idx = slot.base
            for child in slot.teleport._children:
                child._node_idx = idx
                idx += _mounted_direct_count(target, child)
            for child in slot.teleport._children:
                if isinstance(child, DynamicElement):
                    child._re_index_children(True)

    def _assign_block_indices(
        self,
        target: DOMNode,
        teleports: list[TeleportElement],
        measured: dict[int, int],
        base: int,
    ) -> None:
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
        if self._ssr_emit:
            registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
            if registry is not None:
                self._sweep_unconsumed_block(registry)
        target = self._target_node
        if target is not None:
            registry = cast("_TeleportTargetRegistry", inject(_TELEPORT_REGISTRY_KEY, default=None))
            if registry is not None:
                registry.unregister(target, self)
            self._re_index_shared_target()

    def _sweep_unconsumed_block(self, registry: _TeleportTargetRegistry) -> None:
        if not self._ssr_emit:
            return
        try:
            target = inject(DOM_PORT_KEY).query_selector(self._to)
        except ValueError:
            return
        if target is None:
            target = self._target_node
        if target is None:
            return
        if self._ssr_ordinal >= 0:
            if registry.is_consumed(self._ssr_ordinal):
                return
            found = self._find_ssr_block_range(target, registry)
            if found is not None:
                slot, end = found
                for index in range(end, slot - 1, -1):
                    target.removeChild(target.childNodes[index])
                registry.mark_consumed(self._ssr_ordinal)
            return
        expected_suffix = f":{quote(self._to, safe='')}"
        children = target.childNodes
        start_index: int | None = None
        start_ordinal: int | None = None
        for index in range(children.length):
            node = children[index]
            if getattr(node, "nodeType", 0) != 8:
                continue
            data = str(node.textContent or "")
            if (
                start_index is None
                and data.startswith(_BLOCK_START_PREFIX)
                and data.endswith(expected_suffix)
                and not registry.is_consumed(_parse_marker_ordinal(data))
            ):
                start_index = index
                start_ordinal = _parse_marker_ordinal(data)
                continue
            if start_index is not None and start_ordinal is not None and data == f"{_BLOCK_END_PREFIX}{start_ordinal}":
                for remove_index in range(index, start_index - 1, -1):
                    target.removeChild(children[remove_index])
                registry.mark_consumed(start_ordinal)
                return


Teleport = TeleportElement
