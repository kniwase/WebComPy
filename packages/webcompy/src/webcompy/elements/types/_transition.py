from __future__ import annotations

from collections.abc import Callable
from typing import Any

from webcompy import logging
from webcompy.di import inject
from webcompy.elements._dom_objs import DOMNode
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
from webcompy.ports._keys import FFI_PORT_KEY, MEDIA_QUERY_PORT_KEY, TRANSITION_PORT_KEY
from webcompy.ports._transition import TransitionStyle
from webcompy.signal._computed import Computed

_ENTER_PHASES = ("enter-from", "enter-active", "enter-to")
_LEAVE_PHASES = ("leave-from", "leave-active", "leave-to")
_INVALID_TIMES = frozenset({"none", "initial", "inherit", "unset", "revert", "revert-layer"})


def _parse_time(value: str) -> float | None:
    value = value.strip().lower()
    if not value or value in _INVALID_TIMES:
        return None
    if value.endswith("ms"):
        try:
            return float(value[:-2])
        except ValueError:
            return None
    if value.endswith("s"):
        try:
            return float(value[:-1]) * 1000
        except ValueError:
            return None
    return None


def _parse_style_duration(style: TransitionStyle) -> float:
    total = 0.0
    for duration_prop, delay_prop in (
        ("transition-duration", "transition-delay"),
        ("animation-duration", "animation-delay"),
    ):
        durations = style.get_property_value(duration_prop).split(",")
        delays = style.get_property_value(delay_prop).split(",")
        for index, raw in enumerate(durations):
            ms = _parse_time(raw)
            if ms is None:
                continue
            if index < len(delays):
                delay_ms = _parse_time(delays[index])
                if delay_ms is None:
                    delay_ms = 0.0
            else:
                delay_ms = 0.0
            total = max(total, ms + delay_ms)
    return total


class _ChildComputed(Computed[ElementChildren]):
    """Computed that routes child-generator evaluation errors to the boundary.

    Computeds re-evaluate eagerly during signal dispatch, so an error raised
    by the child generator would otherwise be swallowed by the signal layer
    before ``TransitionElement._refresh`` runs. The error is routed to the
    error-boundary pipeline at capture time instead.
    """

    def __init__(
        self,
        func: Callable[[], ElementChildren],
        on_error: Callable[[Exception], None],
    ) -> None:
        self._on_error = on_error
        super().__init__(func)

    def producer_recompute_value(self) -> None:
        try:
            super().producer_recompute_value()
        except WebComPyException:
            raise
        except Exception as err:
            self._on_error(err)


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
        self._sequence: str | None = None
        self._generation = 0
        self._reindex_pending = False
        self._pending_child: ElementAbstract | None = None
        self._cancel_next_frame: Callable[[], None] | None = None
        self._cancel_timeout: Callable[[], None] | None = None
        self._end_event_node: DOMNode | None = None
        self._end_event_proxy: Any = None
        super().__init__()
        self._child_computed = _ChildComputed(child_generator, self._route_child_error)
        self.__set_signal_member__("_child_computed", self._child_computed)

    def _route_child_error(self, err: Exception) -> None:
        from webcompy.elements.types._error_boundary import route_error_deferred

        route_error_deferred(self, err)

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
        if child is None:
            return []
        child = self._create_child_element(self._parent, None, child)
        assert child is not None
        return [child]

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
        try:
            if self._disposed or not self._initial_rendered:
                return
            self._cancel_pending_render_tasks()
            desired = self._normalize_child(self._child_computed.value)
            current = self._children[0] if self._children else None

            if desired is None:
                if self._sequence == "leave":
                    self._discard_pending_child_if_not(None)
                    return
                if current is not None:
                    self._cancel_sequence_handles()
                    self._start_leave(current)
                    return
                if self._reindex_pending:
                    self._reindex_pending = False
                    self._parent._re_index_children(False)
                return

            if self._sequence == "leave":
                if current is not None and _is_patchable(current, desired):
                    self._replace_pending_child(desired)
                    return
                self._finalize_leave_now()
                current = None
            elif self._sequence == "enter":
                self._cancel_sequence_handles()
                current = self._children[0] if self._children else None

            if current is not None and _is_patchable(current, desired):
                self._discard_pending_child_if_not(desired)
                desired = self._create_child_element(self._parent, self._node_idx, desired)
                assert desired is not None
                self._children = _patch_children([current], [desired], self._node_idx)
                if desired._mounted is None:
                    await desired._render()
                self._reindex_parent()
                return

            if current is not None:
                self._replace_pending_child(desired)
                self._start_leave(current)
                return

            self._discard_pending_child_if_not(desired)
            child = self._create_child_element(self._parent, self._node_idx, desired)
            assert child is not None
            self._children = [child]
            if child._mounted is None:
                await child._render()
            self._reindex_parent()
            self._start_enter_sequence(child)
        except WebComPyException:
            raise
        except Exception as err:
            from webcompy.elements.types._error_boundary import route_error_deferred

            route_error_deferred(self, err)

    def _class_name(self, phase: str) -> str:
        return f"{self._name}-{phase}"

    def _should_animate(self) -> bool:
        port = inject(TRANSITION_PORT_KEY, default=None)
        if port is None or not port.enabled:
            return False
        media = inject(MEDIA_QUERY_PORT_KEY, default=None)
        return not (media is not None and media.prefers_reduced_motion())

    @staticmethod
    def _add_classes(node: DOMNode, classes: list[str]) -> None:
        tokens = (node.getAttribute("class") or "").split()
        existing = set(tokens)
        added = [cls for cls in classes if cls not in existing]
        if added:
            node.setAttribute("class", " ".join([*tokens, *added]))

    @staticmethod
    def _remove_classes(node: DOMNode, classes: list[str]) -> None:
        tokens = (node.getAttribute("class") or "").split()
        removed = set(classes)
        remaining = [token for token in tokens if token not in removed]
        if remaining:
            node.setAttribute("class", " ".join(remaining))
        else:
            node.removeAttribute("class")

    def _start_enter_sequence(self, child: ElementAbstract) -> None:
        if not self._should_animate():
            return
        if self._sequence == "enter":
            return
        self._sequence = "enter"
        self._generation += 1
        gen = self._generation
        node = child._node_cache
        if node is None:
            self._finalize_enter(gen)
            return
        self._add_classes(node, [self._class_name("enter-from")])
        self._cancel_next_frame = inject(TRANSITION_PORT_KEY).schedule_next_frame(lambda: self._enter_swap(gen, child))

    def _enter_swap(self, gen: int, child: ElementAbstract) -> None:
        if gen != self._generation or self._sequence != "enter":
            return
        node = child._node_cache
        if node is None:
            self._finalize_enter(gen)
            return
        self._remove_classes(node, [self._class_name("enter-from")])
        self._add_classes(node, [self._class_name("enter-active"), self._class_name("enter-to")])
        self._resolve_duration(gen, child, is_enter=True)

    def _start_leave(self, child: ElementAbstract) -> None:
        if not self._should_animate():
            self._finalize_leave_now()
            if not self._disposed:
                _run_refresh_sync(self._refresh)
            return
        if self._sequence == "leave":
            return
        self._sequence = "leave"
        self._generation += 1
        gen = self._generation
        node = child._node_cache
        if node is None:
            self._finalize_leave(gen)
            return
        self._add_classes(node, [self._class_name("leave-from")])
        self._cancel_next_frame = inject(TRANSITION_PORT_KEY).schedule_next_frame(lambda: self._leave_swap(gen, child))

    def _leave_swap(self, gen: int, child: ElementAbstract) -> None:
        if gen != self._generation or self._sequence != "leave":
            return
        node = child._node_cache
        if node is None:
            self._finalize_leave(gen)
            return
        self._remove_classes(node, [self._class_name("leave-from")])
        self._add_classes(node, [self._class_name("leave-active"), self._class_name("leave-to")])
        self._resolve_duration(gen, child, is_enter=False)

    def _resolve_duration(self, gen: int, child: ElementAbstract, is_enter: bool) -> None:
        duration = self._duration
        if duration is None:
            node = child._node_cache
            duration = 0.0
            if node is not None:
                style = inject(TRANSITION_PORT_KEY).get_computed_style(node)
                duration = _parse_style_duration(style)
            if duration <= 0:
                logging.warning(
                    f"Transition '{self._name}': no transition or animation duration is defined; finishing immediately."
                )
                self._finalize_sequence(gen, is_enter)
                return
        elif duration <= 0:
            self._finalize_sequence(gen, is_enter)
            return
        self._arm_end_listeners(gen, child, is_enter, duration)

    def _arm_end_listeners(
        self,
        gen: int,
        child: ElementAbstract,
        is_enter: bool,
        duration: float,
    ) -> None:
        node = child._node_cache
        if node is None:
            self._finalize_sequence(gen, is_enter)
            return
        proxy = inject(FFI_PORT_KEY).create_proxy(lambda ev: self._on_end_event(gen, child, is_enter, ev))
        node.addEventListener("transitionend", proxy, False)
        node.addEventListener("animationend", proxy, False)
        self._end_event_node = node
        self._end_event_proxy = proxy
        self._cancel_timeout = inject(TRANSITION_PORT_KEY).schedule_timeout(
            lambda: self._finalize_sequence(gen, is_enter),
            duration,
        )

    def _on_end_event(self, gen: int, child: ElementAbstract, is_enter: bool, ev: Any) -> None:
        node = child._node_cache
        if node is None:
            return
        target = getattr(ev, "target", None)
        if target != node:
            return
        self._finalize_sequence(gen, is_enter)

    def _finalize_sequence(self, gen: int, is_enter: bool) -> None:
        if is_enter:
            self._finalize_enter(gen)
        else:
            self._finalize_leave(gen)

    def _finalize_enter(self, gen: int) -> None:
        if gen != self._generation or self._sequence != "enter":
            return
        self._cancel_sequence_handles()
        child = self._children[0] if self._children else None
        if child is not None and (node := child._node_cache) is not None:
            self._remove_classes(node, [self._class_name(phase) for phase in _ENTER_PHASES])
        self._sequence = None

    def _finalize_leave(self, gen: int) -> None:
        if gen != self._generation or self._sequence != "leave":
            return
        self._cancel_sequence_handles()
        child = self._children[0] if self._children else None
        if child is not None:
            if (node := child._node_cache) is not None:
                self._remove_classes(node, [self._class_name(phase) for phase in _LEAVE_PHASES])
            child._remove_element(True, True)
        self._children = []
        self._sequence = None
        self._reindex_pending = True
        if not self._disposed:
            _run_refresh_sync(self._refresh)

    def _finalize_leave_now(self) -> None:
        self._generation += 1
        self._cancel_sequence_handles()
        child = self._children[0] if self._children else None
        if child is not None:
            if (node := child._node_cache) is not None:
                self._remove_classes(node, [self._class_name(phase) for phase in _LEAVE_PHASES])
            child._remove_element(True, True)
        self._children = []
        self._sequence = None
        self._reindex_pending = True

    def _reindex_parent(self) -> None:
        self._reindex_pending = False
        self._parent._re_index_children(False)

    def _cancel_sequence_handles(self) -> None:
        self._generation += 1
        if self._cancel_next_frame is not None:
            self._cancel_next_frame()
            self._cancel_next_frame = None
        if self._cancel_timeout is not None:
            self._cancel_timeout()
            self._cancel_timeout = None
        node, proxy = self._end_event_node, self._end_event_proxy
        self._end_event_node = None
        self._end_event_proxy = None
        if node is not None and proxy is not None:
            node.removeEventListener("transitionend", proxy)
            node.removeEventListener("animationend", proxy)
            if hasattr(proxy, "destroy"):
                proxy.destroy()
        child = self._children[0] if self._children else None
        if child is not None and (node := child._node_cache) is not None:
            self._remove_classes(
                node,
                [self._class_name(phase) for phase in (*_ENTER_PHASES, *_LEAVE_PHASES)],
            )
        self._sequence = None

    def _replace_pending_child(self, desired: ElementAbstract) -> None:
        self._discard_pending_child_if_not(desired)
        self._pending_child = desired

    def _discard_pending_child_if_not(self, keep: ElementAbstract | None) -> None:
        child = self._pending_child
        self._pending_child = None
        if child is not None and child is not keep and child._mounted is None:
            child._remove_element(True, True)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True) -> None:
        self._disposed = True
        self._cancel_sequence_handles()
        self._discard_pending_child_if_not(None)
        super()._remove_element(recursive, remove_node)


Transition = TransitionElement
