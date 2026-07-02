from __future__ import annotations

from collections.abc import Callable

from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement
from webcompy.elements.types._text import TextElement
from webcompy.utils._environment import ENVIRONMENT


class ClientOnlyElement(DynamicElement):
    def __init__(
        self,
        children: Callable[[], ElementChildren],
        fallback: Callable[[], ElementChildren] | None = None,
    ) -> None:
        self._children_generator = children
        self._fallback_generator = fallback
        self._is_client = ENVIRONMENT == "pyscript"
        super().__init__()

    def _on_set_parent(self):
        pass

    def _generate_children(self, generator: Callable[[], ElementChildren]) -> list[ElementAbstract]:
        ele = self._create_child_element(self._parent, None, generator())
        return [ele] if ele is not None else []

    def _generate_fallback(self) -> list[ElementAbstract]:
        if self._fallback_generator is not None:
            return self._generate_children(self._fallback_generator)
        ele = self._create_child_element(self._parent, None, TextElement(""))
        return [ele] if ele is not None else []

    async def _render(self):
        if not self._children:
            children = (
                self._generate_children(self._children_generator) if self._is_client else self._generate_fallback()
            )
            self._children = children
        await super()._render()

    def _hydrate_node(self):
        children = self._generate_children(self._children_generator) if self._is_client else self._generate_fallback()
        self._children = children
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
        super()._hydrate_node()
