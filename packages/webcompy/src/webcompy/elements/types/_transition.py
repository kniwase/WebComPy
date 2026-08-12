from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import (
    DynamicElement,
    _is_patchable,
    _patch_children,
    _run_refresh_sync,
)
from webcompy.elements.types._element import ElementBase
from webcompy.exception import WebComPyException
from webcompy.signal._computed import Computed


class TransitionElement(DynamicElement):
    def __init__(
        self,
        props: dict[str, Any],
        child_generator: Callable[[], ElementChildren],
    ) -> None:
        name = props.get("name") if isinstance(props, dict) else None
        duration = props.get("duration") if isinstance(props, dict) else None
        if not isinstance(name, str) or not name:
            raise WebComPyException("Transition requires a non-empty string 'name' prop.")
        if duration is not None:
            if isinstance(duration, bool) or not isinstance(duration, (int, float)):
                raise WebComPyException("Transition 'duration' prop must be a non-negative number of milliseconds.")
            if duration < 0:
                raise WebComPyException("Transition 'duration' prop must be a non-negative number of milliseconds.")
        self._name = name
        self._duration: float | None = float(duration) if duration is not None else None
        self._child_generator = child_generator
        self._initial_rendered = False
        self._signal_activated = False
        self._disposed = False
        super().__init__()
        self._child_computed = Computed(child_generator)
        self.__set_signal_member__("_child_computed", self._child_computed)

    def _on_set_parent(self) -> None:
        pass

    def _normalize_child(self, value: ElementChildren) -> ElementAbstract | None:
        if value is None:
            return None
        if isinstance(value, ElementBase) and not isinstance(value, DynamicElement):
            return value
        raise WebComPyException(
            "Transition children must be a single element with one DOM node "
            f"(Element or Component); got {type(value).__name__}."
        )

    def _build_children(self, value: ElementChildren) -> list[ElementAbstract]:
        child = self._normalize_child(value)
        return [child] if child is not None else []

    async def _render(self) -> None:
        if not self._initial_rendered:
            self._children = self._build_children(self._child_computed.value)
            await super()._render()
            self._initial_rendered = True
            self._activate_signal()
            return
        await super()._render()

    def _hydrate_node(self) -> None:
        self._children = self._build_children(self._child_computed.value)
        super()._hydrate_node()
        self._initial_rendered = True
        self._activate_signal()

    def _activate_signal(self) -> None:
        if not self._signal_activated:
            self._signal_activated = True
            self._add_callback_node(self._child_computed.on_after_updating(self._refresh_sync))

    def _refresh_sync(self, *args: Any) -> None:
        _run_refresh_sync(self._refresh, *args)

    async def _refresh(self, *args: Any) -> None:
        if self._disposed or not self._initial_rendered:
            return
        self._cancel_pending_render_tasks()
        desired = self._normalize_child(self._child_computed.value)
        current = self._children[0] if self._children else None
        if desired is None:
            if current is None:
                return
            current._remove_element(True, True)
            self._children = []
            self._parent._re_index_children(False)
            return
        if current is not None and _is_patchable(current, desired):
            desired = self._create_child_element(self._parent, self._node_idx, desired)
            assert desired is not None
            self._children = _patch_children([current], [desired], self._node_idx)
            if desired._mounted is None:
                await desired._render()
            self._parent._re_index_children(False)
            return
        child = self._create_child_element(self._parent, self._node_idx, desired)
        assert child is not None
        self._children = [child]
        if child._mounted is None:
            await child._render()
        self._parent._re_index_children(False)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True) -> None:
        self._disposed = True
        super()._remove_element(recursive, remove_node)


Transition = TransitionElement
