from __future__ import annotations

from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement


class FragmentElement(DynamicElement):
    def __init__(self, children: list[ElementAbstract] | None = None) -> None:
        self._pending_children: list[ElementAbstract] = list(children) if children else []
        super().__init__()

    def _on_set_parent(self) -> None:
        for child in self._pending_children:
            child._parent = self._parent
        self._children = self._pending_children
        self._pending_children = []
