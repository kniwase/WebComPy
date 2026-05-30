from __future__ import annotations

import asyncio
from typing import Any

from webcompy import logging
from webcompy.di._scope import _active_di_scope
from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
    EventHandler,
)
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._text import TextElement
from webcompy.signal._base import SignalBase
from webcompy.signal._graph import get_active_consumer, set_active_consumer
from webcompy.utils._environment import ENVIRONMENT


def _handle_gather_results(children: list[ElementAbstract], results: list[Any]) -> None:
    """Process asyncio.gather return_exceptions=True results.

    Log secondary errors, clean up successful siblings, and raise the first error.
    """
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        for err in errors[1:]:
            logging.error(err)
        for i, r in enumerate(results):
            if not isinstance(r, Exception):
                try:
                    children[i]._remove_element()
                except Exception as cleanup_err:
                    logging.error(cleanup_err)
        raise errors[0]


class ElementWithChildren(ElementAbstract):
    _tag_name: HtmlTags
    _attrs: dict[str, AttrValue] = {}  # noqa: RUF012
    _event_handlers: dict[str, EventHandler] = {}  # noqa: RUF012
    _children: list[ElementAbstract] = []  # noqa: RUF012
    _preserve_children: bool = False
    __parent: ElementWithChildren

    def __init__(self) -> None:
        self._node_cache = None
        self._callback_nodes: list[Any] = []

    @property
    def _parent(self) -> ElementWithChildren:
        return self.__parent

    @_parent.setter
    def _parent(self, parent: ElementWithChildren):  # type: ignore
        self.__parent = parent

    async def _render(self):
        await super()._render()
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx

        if ENVIRONMENT == "pyscript":
            _snap_consumer = get_active_consumer()
            _snap_di_scope = _active_di_scope.get(None)

            async def _child_render(child):
                set_active_consumer(_snap_consumer)
                if _snap_di_scope is not None:
                    _active_di_scope.set(_snap_di_scope)
                return await child._render()

            results = await asyncio.gather(
                *(_child_render(child) for child in self._children),
                return_exceptions=True,
            )
        else:
            results = await asyncio.gather(
                *(child._render() for child in self._children),
                return_exceptions=True,
            )
        _handle_gather_results(self._children, results)
        if (node := self._get_node()) is not None and not self._preserve_children:
            for _ in range(node.childNodes.length - self._children_length):
                node.childNodes[-1].remove()

    async def _hydrate_node(self):
        result = await super()._hydrate_node()
        self._re_index_children()
        for child in self._children:
            await child._hydrate_node()
        if (node := self._get_node()) is not None and not self._preserve_children:
            for _ in range(node.childNodes.length - self._children_length):
                node.childNodes[-1].remove()
        return result

    def _get_processed_attrs(self):
        attrs = {name: self._proc_attr(value) for name, value in self._attrs.items()}
        if "webcompy-component" not in self._attrs and self._get_belonging_component():
            attrs["webcompy-cid-" + self._get_belonging_component()] = ""
        return attrs

    def _proc_attr(self, value: AttrValue):
        obj = value.value if isinstance(value, SignalBase) else value
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
        parent: ElementWithChildren,
        node_idx: int | None,
        child: ElementChildren,
    ):
        if child is None:
            return None
        elif isinstance(child, (str, SignalBase)):
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
        node_idx = 0 if self._children_length == 0 else self._children[-1]._node_idx + self._children[-1]._node_count
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
