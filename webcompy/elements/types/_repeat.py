from __future__ import annotations

from collections.abc import Callable
from functools import partial
from itertools import chain
from typing import Any, TypeVar

from webcompy._browser._modules import browser
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.elements.types._text import NewLine
from webcompy.exception import WebComPyException
from webcompy.reactive import ReactiveBase, computed

T = TypeVar("T")


class RepeatElement(DynamicElement):
    _key: Callable[[Any], str | int] | None
    _key_to_child: dict[str | int, ElementAbstract]
    _children_keys: list[str | int]

    def __init__(
        self,
        sequence: ReactiveBase[list[T]],
        template: Callable[[T], ElementChildren],
        key: Callable[[T], str | int] | None = None,
    ) -> None:
        self._template = template
        self._sequence = sequence
        self._key = key
        self._key_to_child = {}
        self._children_keys = []
        self._reactive_activated = False

        if not isinstance(self._sequence, ReactiveBase):  # type: ignore
            raise ValueError("Argument 'sequence' must be Reactive Object.")
        super().__init__()

    def _on_set_parent(self):
        if not browser:
            self._children = self._generate_children()
            if self._key is not None:
                self._populate_key_map()

    def _populate_key_map(self):
        self._key_to_child = {}
        self._children_keys = []
        for child, item in zip(self._children, self._sequence.value, strict=True):
            k = self._key(item)  # type: ignore[operator]
            self._key_to_child[k] = child
            self._children_keys.append(k)

    def _generate_children(self):
        return list(
            filter(
                None,
                map(
                    partial(self._create_child_element, self._parent, None),
                    map(self._template, self._sequence.value),
                ),
            )
        )

    def _render(self):
        self._refresh()
        if not self._reactive_activated:
            self._reactive_activated = True
            self._set_callback_id(self._sequence.on_after_updating(self._refresh))

    def _refresh(self, *args: Any):
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(f"'{self.__class__.__name__}' does not have its parent.")
        if self._key is not None and browser and self._children_keys:
            self._reconcile_children()
        else:
            for _ in range(len(self._children)):
                self._children.pop(-1)._remove_element()
            self._children = self._generate_children()
            for c_idx, child in enumerate(self._children):
                child._node_idx = self._node_idx + c_idx
                child._render()
            if self._key is not None:
                self._populate_key_map()
        self._parent._re_index_children(False)

    def _reconcile_children(self):
        new_items = self._sequence.value
        new_keys: list[str | int] = [self._key(item) for item in new_items]  # type: ignore[operator]
        seen_keys: set[str | int] = set()
        for k in new_keys:
            if k in seen_keys:
                raise WebComPyException(f"Duplicate key: {k!r}")
            seen_keys.add(k)

        new_key_set = set(new_keys)
        old_key_set = set(self._children_keys)

        removed_keys = old_key_set - new_key_set
        for k in removed_keys:
            self._key_to_child.pop(k)._remove_element()

        parent_node = self._parent._get_node()
        new_children: list[ElementAbstract] = []
        new_key_to_child: dict[str | int, ElementAbstract] = {}

        node_offset = self._node_idx
        for k, item in zip(new_keys, new_items, strict=True):
            if k in self._key_to_child:
                child = self._key_to_child[k]
                new_key_to_child[k] = child
                new_children.append(child)
            else:
                child_element = self._create_child_element(self._parent, None, self._template(item))
                if child_element is not None:
                    new_key_to_child[k] = child_element
                    new_children.append(child_element)

        for c_idx, child in enumerate(new_children):
            child._node_idx = node_offset + c_idx
            node = child._get_node()
            if node:
                expected_idx = child._node_idx
                if expected_idx < parent_node.childNodes.length:
                    ref_node = parent_node.childNodes[expected_idx]
                    if ref_node is not node:
                        parent_node.insertBefore(node, ref_node)
                elif expected_idx >= parent_node.childNodes.length:
                    parent_node.appendChild(node)
                if not child._mounted:
                    child._mounted = True

        for child in new_children:
            if child._node_cache is None:
                child._render()

        self._children = new_children
        self._children_keys = new_keys
        self._key_to_child = new_key_to_child


class MultiLineTextElement(RepeatElement):
    def __init__(self, text: str | ReactiveBase[Any]) -> None:
        super().__init__(
            computed(
                lambda: list(
                    chain.from_iterable(
                        map(
                            lambda line: (line, NewLine()),
                            str(text.value if isinstance(text, ReactiveBase) else text).split("\n"),
                        )
                    )
                )[:-1]
            ),
            lambda s: s,
        )
