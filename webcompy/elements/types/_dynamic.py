from __future__ import annotations

from abc import abstractmethod
from contextlib import suppress

from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._base import ElementWithChildren
from webcompy.elements.types._element import ElementBase
from webcompy.elements.types._text import TextElement
from webcompy.signal._graph import consumer_destroy


class DynamicElement(ElementWithChildren):
    __parent: ElementWithChildren

    @property
    def _node_count(self) -> int:
        return sum(child._node_count for child in self._children)

    def _get_node(self) -> DOMNode:
        return self._parent._get_node()

    async def _render(self):
        parent_node = self._parent._get_node()
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
            if child._mounted is None:
                await child._render()
        _position_element_nodes(self, parent_node, self._node_idx)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        for callback_node in self._callback_nodes:
            consumer_destroy(callback_node)
        self._clear_node_cache(False)
        self.__purge_signal_members__()
        if recursive:
            for child in self._children:
                child._remove_element(True, True)

    def _hydrate_node(self) -> None:
        for child in self._children:
            child._hydrate_node()
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            idx += child._node_count
            if not child._mounted:
                # TODO: child._render() is async but _hydrate_node() is sync.
                # This is intentional per feat-async-rendering-pipeline spec:
                # "_hydrate_node() SHALL remain synchronous in this change".
                # Downstream changes (feat-client-only-component, feat-suspense-component)
                # will make hydration async via asyncio.ensure_future(child._render()).
                child._render()  # type: ignore[unused-coroutine]

    @property
    def _parent(self) -> ElementWithChildren:
        return self.__parent

    @_parent.setter
    def _parent(self, parent: ElementWithChildren):
        self.__parent = parent
        self._on_set_parent()

    @abstractmethod
    def _on_set_parent(self): ...


def _is_patchable(old: ElementAbstract, new: ElementAbstract) -> bool:
    if isinstance(old, TextElement) and isinstance(new, TextElement):
        return True
    if isinstance(old, DynamicElement) or isinstance(new, DynamicElement):
        return False
    if isinstance(old, ElementBase) and isinstance(new, ElementBase):
        return old._tag_name == new._tag_name
    return False


def _reposition_node(element: ElementAbstract, new_index: int) -> None:
    node = element._node_cache
    if node is None:
        return
    parent = node.parentNode
    if not parent and not isinstance(element, DynamicElement):
        with suppress(AttributeError):
            parent = element._parent._get_node()
    if not parent:
        return
    if new_index < parent.childNodes.length:
        target = parent.childNodes[new_index]
        if node != target:
            parent.insertBefore(node, target)
    else:
        parent.appendChild(node)


def _patch_children(
    old_children: list[ElementAbstract],
    new_children: list[ElementAbstract],
    node_idx_offset: int = 0,
) -> list[ElementAbstract]:
    matched_old_indices: set[int] = set()

    for new_idx, new_child in enumerate(new_children):
        if (
            new_idx < len(old_children)
            and new_idx not in matched_old_indices
            and _is_patchable(old_children[new_idx], new_child)
            and old_children[new_idx]._node_cache is not None
        ):
            matched_old_indices.add(new_idx)
            old_child = old_children[new_idx]
            old_node = old_child._node_cache
            assert old_node is not None
            if isinstance(new_child, TextElement) and isinstance(old_child, TextElement):
                new_child._adopt_node(old_node)
            elif isinstance(new_child, ElementBase) and isinstance(old_child, ElementBase):
                new_child._adopt_node(old_node)
                _patch_children(old_child._children, new_child._children)
            _reposition_node(new_child, node_idx_offset + new_idx)
        else:
            for old_idx, old_child in enumerate(old_children):
                if old_idx in matched_old_indices:
                    continue
                if _is_patchable(old_child, new_child) and old_child._node_cache is not None:
                    matched_old_indices.add(old_idx)
                    old_node = old_child._node_cache
                    assert old_node is not None
                    if isinstance(new_child, TextElement) and isinstance(old_child, TextElement):
                        new_child._adopt_node(old_node)
                    elif isinstance(new_child, ElementBase) and isinstance(old_child, ElementBase):
                        new_child._adopt_node(old_node)
                        _patch_children(old_child._children, new_child._children)
                    _reposition_node(new_child, node_idx_offset + new_idx)
                    break

    for old_idx, old_child in enumerate(old_children):
        if old_idx in matched_old_indices:
            old_child._detach_from_node()
        else:
            old_child._remove_element(recursive=True, remove_node=True)

    return new_children


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
