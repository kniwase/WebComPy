from __future__ import annotations

from collections.abc import Callable
from operator import truth
from typing import Any, TypeAlias, cast

from webcompy.components._component import end_defer_after_rendering, start_defer_after_rendering
from webcompy.di import inject
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _patch_children
from webcompy.exception import WebComPyException
from webcompy.ports._keys import HOST_PORT_KEY
from webcompy.signal._base import SignalBase
from webcompy.utils import ENVIRONMENT

NodeGenerator: TypeAlias = Callable[[], ElementChildren]
SwitchCasesSignal: TypeAlias = list[tuple[SignalBase[Any], NodeGenerator]]
SwitchCasesSignalList: TypeAlias = SignalBase[list[tuple[Any, NodeGenerator]]]
SwitchCases: TypeAlias = SwitchCasesSignal | SwitchCasesSignalList


class SwitchElement(DynamicElement):
    _rendered_idx: int | None

    def __init__(
        self,
        cases: SwitchCases,
        default: NodeGenerator | None,
    ) -> None:
        self._cases = cases
        self._default = default
        self._signal_activated = False
        self._rendered_idx = None
        super().__init__()

    def _select_generator(self) -> tuple[int, Callable[[], ElementChildren]]:
        cases = self._cases.value if isinstance(self._cases, SignalBase) else self._cases
        for idx, (cond, generator) in enumerate(cast("list[tuple[SignalBase[Any] | Any, NodeGenerator]]", cases)):
            if truth(cond.value if isinstance(cond, SignalBase) else cond):
                return (idx, generator)
        if self._default:
            return (-1, self._default)
        else:
            return (-1, lambda: None)

    def _generate_children(self, generator: NodeGenerator) -> list[ElementAbstract]:
        ele = self._create_child_element(self._parent, None, generator())
        return [ele] if ele is not None else []

    def _render(self):
        self._refresh()
        if not self._signal_activated:
            self._signal_activated = True
            if isinstance(self._cases, SignalBase):
                self._add_callback_node(self._cases.on_after_updating(self._refresh))
            else:
                for cond, _ in self._cases:
                    if isinstance(cond, SignalBase):  # type: ignore
                        self._add_callback_node(cond.on_after_updating(self._refresh))

    def _refresh(self, *args: Any):
        idx, generator = self._select_generator()
        if idx == self._rendered_idx:
            return
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(f"'{self.__class__.__name__}' does not have its parent.")
        self._rendered_idx = idx
        new_children = self._generate_children(generator)
        old_children = self._children
        self._children = _patch_children(old_children, new_children, self._node_idx)
        should_defer = ENVIRONMENT == "pyscript" and self._signal_activated
        if should_defer:
            start_defer_after_rendering()
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
            child._render()
        if should_defer and ENVIRONMENT == "pyscript":
            deferred = end_defer_after_rendering()
            for callback in deferred:
                inject(HOST_PORT_KEY).schedule_macro_task(callback)
        self._parent._re_index_children(False)

    def _on_set_parent(self):
        if ENVIRONMENT != "pyscript":

            def refresh(*args: Any):
                idx, generator = self._select_generator()
                self._rendered_idx = idx
                self._children = self._generate_children(generator)

            refresh()

            if not self._signal_activated:
                self._signal_activated = True

                if isinstance(self._cases, SignalBase):
                    self._add_callback_node(self._cases.on_after_updating(refresh))
                else:
                    for cond, _ in self._cases:
                        if isinstance(cond, SignalBase):  # type: ignore
                            self._add_callback_node(cond.on_after_updating(refresh))
