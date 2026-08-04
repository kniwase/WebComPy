from __future__ import annotations

from typing import Any

from webcompy import logging
from webcompy.elements._dom_objs import DOMNode
from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
    EventHandler,
)
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._text import TextElement
from webcompy.signal import SignalBase


def _normalize_hydration_text_runs(
    children: list[ElementAbstract],
    parent_node: DOMNode,
    start_idx: int,
) -> None:
    child_count = parent_node.childNodes.length
    runs: list[tuple[int, list[TextElement]]] = []
    dom_idx = start_idx
    i = 0
    n = len(children)
    while i < n:
        child = children[i]
        if isinstance(child, TextElement):
            run: list[TextElement] = []
            j = i
            while j < n and isinstance(children[j], TextElement):
                run.append(children[j])
                j += 1
            if len(run) >= 2 and dom_idx < child_count:
                runs.append((dom_idx, run))
            dom_idx += len(run)
            i = j
        else:
            dom_idx += child._node_count
            i += 1
    for run_start, run in runs:
        node = parent_node.childNodes[run_start]
        if node.nodeName.lower() != "#text":
            continue
        content = node.textContent or ""
        if content == run[0]._get_text():
            continue
        expected = "".join(c._get_text() for c in run)
        if content != expected:
            logging.warning(f"Hydration text-run mismatch: expected {expected!r}, found {content!r}; skipping split")
            continue
        remainder: DOMNode = node
        for c in run[:-1]:
            remainder = remainder.splitText(len(c._get_text()))
            remainder.__webcompy_prerendered_node__ = True


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
        idx = 0
        for child in self._children:
            child._node_idx = idx
            await child._render()
            idx += child._node_count
        if (node := self._get_node()) is not None and not self._preserve_children:
            for _ in range(node.childNodes.length - self._children_length):
                node.childNodes[-1].remove()

    def _hydrate_node(self):
        result = super()._hydrate_node()
        if (node := self._node_cache) is not None and not self._preserve_children:
            _normalize_hydration_text_runs(self._children, node, 0)
        idx = 0
        for child in self._children:
            child._node_idx = idx
            child._hydrate_node()
            idx += child._node_count
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
        from webcompy.elements.types._dynamic import DynamicElement

        idx = getattr(self, "_node_idx", 0) if isinstance(self, DynamicElement) else 0
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
