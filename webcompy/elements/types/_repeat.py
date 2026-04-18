from __future__ import annotations

from collections.abc import Callable
from functools import partial
from itertools import chain
from typing import Any, TypeVar, overload

from webcompy._browser._modules import browser
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _position_element_nodes
from webcompy.elements.types._text import NewLine
from webcompy.exception import WebComPyException
from webcompy.signal import SignalBase, computed

K = TypeVar("K", str, int)
V = TypeVar("V")


class RepeatElement(DynamicElement):
    _key_to_child: dict[str | int, ElementAbstract]
    _children_keys: list[str | int]

    @overload
    def __init__(
        self,
        sequence: SignalBase[dict[K, V]],
        template: Callable[[V], ElementChildren],
    ) -> None: ...

    @overload
    def __init__(
        self,
        sequence: SignalBase[dict[K, V]],
        template: Callable[[V, K], ElementChildren],
    ) -> None: ...

    @overload
    def __init__(
        self,
        sequence: SignalBase[list[V]],
        template: Callable[[V], ElementChildren],
    ) -> None: ...

    @overload
    def __init__(
        self,
        sequence: SignalBase[list[V]],
        template: Callable[[V, int], ElementChildren],
    ) -> None: ...

    @overload
    def __init__(
        self,
        sequence: SignalBase[list[V]],
        template: Callable[[V, K], ElementChildren],
        key: Callable[[V], K],
    ) -> None: ...

    def __init__(
        self,
        sequence: SignalBase[dict[K, V]] | SignalBase[list[V]],
        template: Callable[[V], ElementChildren] | Callable[[V, K], ElementChildren],
        key: Callable[[V], K] | None = None,
    ) -> None:
        if not isinstance(sequence, SignalBase):
            raise ValueError("Argument 'sequence' must be Signal Object.")
        is_dict = isinstance(sequence.value, dict)
        if is_dict and key is not None:
            raise ValueError("Argument 'key' is not allowed when sequence is a ReactiveDict.")

        self._is_dict = is_dict
        self._sequence: SignalBase[Any] = sequence
        self._has_key = is_dict or key is not None
        self._key_fn: Callable[[Any], str | int] | None = key if not is_dict else None

        if is_dict or key is not None:
            self._two_arg_template: Callable[[Any, str | int], ElementChildren] | None = template  # type: ignore[assignment]
            self._single_arg_template: Callable[[Any], ElementChildren] | None = None
        else:
            self._two_arg_template = None
            self._single_arg_template = template  # type: ignore[assignment]

        self._key_to_child = {}
        self._children_keys = []
        self._signal_activated = False
        super().__init__()

    def _call_template(self, v: Any, k: str | int) -> ElementChildren:
        if self._two_arg_template is not None:
            return self._two_arg_template(v, k)
        return self._single_arg_template(v)  # type: ignore[misc]

    def _on_set_parent(self):
        if not browser:
            self._children = self._generate_children()
            if self._has_key:
                self._populate_key_map()

    def _populate_key_map(self):
        self._key_to_child = {}
        self._children_keys = []
        if self._is_dict:
            dict_value = self._sequence.value
            for child, k in zip(self._children, dict_value, strict=True):
                self._key_to_child[k] = child
                self._children_keys.append(k)
        elif self._key_fn is not None:
            for child, item in zip(self._children, self._sequence.value, strict=True):
                k = self._key_fn(item)
                self._key_to_child[k] = child
                self._children_keys.append(k)
        else:
            for child, item in zip(self._children, self._sequence.value, strict=True):
                self._key_to_child[id(item)] = child
                self._children_keys.append(id(item))

    def _iter_items(self) -> list[tuple[Any, str | int]]:
        if self._is_dict:
            return [(v, k) for k, v in self._sequence.value.items()]
        elif self._key_fn is not None:
            return [(item, self._key_fn(item)) for item in self._sequence.value]
        else:
            return [(item, idx) for idx, item in enumerate(self._sequence.value)]

    def _generate_children(self):
        items = self._iter_items()
        return list(
            filter(
                None,
                map(
                    partial(self._create_child_element, self._parent, None),
                    [self._call_template(v, k) for v, k in items],
                ),
            )
        )

    def _render(self):
        self._refresh()
        if not self._signal_activated:
            self._signal_activated = True
            self._set_callback_id(self._sequence.on_after_updating(self._refresh))

    def _refresh(self, *args: Any):
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(f"'{self.__class__.__name__}' does not have its parent.")
        if self._has_key and browser and self._children_keys:
            self._reconcile_children()
        else:
            for _ in range(len(self._children)):
                self._children.pop(-1)._remove_element()
            self._children = self._generate_children()
            for c_idx, child in enumerate(self._children):
                child._node_idx = self._node_idx + c_idx
                child._render()
            if self._has_key:
                self._populate_key_map()
        self._parent._re_index_children(False)

    def _reconcile_children(self):
        items = self._iter_items()
        new_keys: list[str | int] = [k for _, k in items]

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
        newly_created: set[int] = set()

        node_offset = self._node_idx
        for v, k in items:
            if k in self._key_to_child:
                child = self._key_to_child[k]
                new_key_to_child[k] = child
                new_children.append(child)
            else:
                child_element = self._create_child_element(self._parent, None, self._call_template(v, k))
                if child_element is not None:
                    new_key_to_child[k] = child_element
                    new_children.append(child_element)
                    newly_created.add(len(new_children) - 1)

        for c_idx, child in enumerate(new_children):
            child._node_idx = node_offset + c_idx
            if isinstance(child, DynamicElement):
                _position_element_nodes(child, parent_node, child._node_idx)
            else:
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

        for c_idx, child in enumerate(new_children):
            if c_idx in newly_created:
                child._render()
            elif isinstance(child, DynamicElement):
                pass
            elif child._node_cache is None:
                child._render()

        self._children = new_children
        self._children_keys = new_keys
        self._key_to_child = new_key_to_child


class MultiLineTextElement(RepeatElement):
    def __init__(self, text: str | SignalBase[Any]) -> None:
        super().__init__(
            computed(
                lambda: list(
                    chain.from_iterable(
                        map(
                            lambda line: (line, NewLine()),
                            str(text.value if isinstance(text, SignalBase) else text).split("\n"),
                        )
                    )
                )[:-1]
            ),
            lambda s: s,
        )
