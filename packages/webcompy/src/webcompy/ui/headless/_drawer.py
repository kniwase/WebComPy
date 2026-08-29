"""Headless Drawer component reusing the modal accessibility contract."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any, Literal, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.components._libs import generate_id
from webcompy.di import inject
from webcompy.elements import Teleport, Transition, create_element
from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.signal import use_computed
from webcompy.signal._base import SignalBase
from webcompy.ui.headless._overlay_utils import (
    capture_active_element,
    focus_initial,
    get_focusable_elements,
    restore_focus,
)


class DrawerProps(TypedDict, total=False):
    """Props for the headless ``Drawer`` component."""

    open: bool
    on_close: Callable[[], None]
    edge: Literal["left", "right", "top", "bottom"]
    aria_label: str
    aria_labelledby: str
    close_on_backdrop: bool
    close_on_escape: bool
    transition_name: str | None
    class_name: str
    class_backdrop: str
    class_panel: str


_FRAMEWORK_CLASS = "webcompy-headless-drawer"
_BACKDROP_CLASS = "webcompy-headless-drawer-backdrop"
_PANEL_CLASS = "webcompy-headless-drawer-panel"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-drawer")
def Drawer(context: ComponentContext[DrawerProps]) -> Any:
    """Render an edge drawer with the modal accessibility contract.

    Args:
        context: Component context carrying drawer props and default slot.

    Returns:
        The rendered drawer element.

    """
    props = context.props or {}
    open_raw = props.get("open", False)
    on_close = props.get("on_close")
    edge = props.get("edge", "right")
    if edge not in ("left", "right", "top", "bottom"):
        edge = "right"
    aria_label = props.get("aria_label", "")
    aria_labelledby = props.get("aria_labelledby", "")
    close_on_backdrop = props.get("close_on_backdrop", True)
    close_on_escape = props.get("close_on_escape", True)
    transition_name = props.get("transition_name")
    class_name = props.get("class_name", "")
    class_backdrop = props.get("class_backdrop", "")
    class_panel = props.get("class_panel", "")

    panel_id = f"webcompy-drawer-panel-{generate_id('drawer')[:8]}"
    backdrop_id = f"webcompy-drawer-backdrop-{generate_id('backdrop')[:8]}"

    is_signal = isinstance(open_raw, SignalBase)
    if is_signal:
        is_open_computed = use_computed(lambda: bool(open_raw.value))  # type: ignore[union-attr]
        is_open = lambda: bool(is_open_computed.value)
    else:
        is_open_computed = None
        is_open = lambda: bool(open_raw)

    slot_content = context.slots("default", fallback=lambda: None)
    captured: list[Any] = [None]
    cleanups: list[Callable[[], None]] = []
    destroyed: list[bool] = [False]

    def _clear() -> None:
        while cleanups:
            fn = cleanups.pop()
            with contextlib.suppress(Exception):
                fn()

    def _setup_listeners() -> None:
        _clear()
        if not is_open():
            return
        try:
            dom = inject(DOM_PORT_KEY, default=None)
        except Exception:
            dom = None
        if dom is None:
            return
        if close_on_escape and on_close is not None:
            local_close = on_close

            def _esc(event: Any) -> None:
                if not is_open():
                    return
                key = getattr(event, "key", None)
                if key is None and isinstance(event, dict):
                    key = event.get("key")
                if key == "Escape":
                    local_close()

            cleanups.append(dom.add_document_event_listener("keydown", _esc))
        if close_on_backdrop and on_close is not None:
            local_close2 = on_close

            def _click(event: Any) -> None:
                if not is_open():
                    return
                target = getattr(event, "target", None)
                if target is None and isinstance(event, dict):
                    target = event.get("target")
                if target is None:
                    return
                try:
                    tid = getattr(target, "getAttribute", lambda _: None)("id")
                    if tid == backdrop_id:
                        local_close2()
                        return
                    cls = getattr(target, "getAttribute", lambda _: None)("class") or ""
                    if _BACKDROP_CLASS in cls:
                        local_close2()
                except Exception:
                    pass

            cleanups.append(dom.add_document_event_listener("click", _click))

        def _tab(event: Any) -> None:
            if not is_open():
                return
            key = getattr(event, "key", None)
            if key is None and isinstance(event, dict):
                key = event.get("key")
            if key != "Tab":
                return
            try:
                panel = None
                try:
                    panel = dom.get_element_by_id(panel_id) if dom else None
                    if panel is None:
                        panel = dom.query_selector(f"#{panel_id}") if dom else None
                except Exception:
                    panel = None
                if panel is None:
                    return
                focusable = get_focusable_elements(panel)
                if not focusable:
                    return
                try:
                    host = inject(HOST_PORT_KEY, default=None)
                    active = None
                    if host is not None:
                        getter = host.create_js_global_getter(
                            "document",
                            wrapper=lambda doc: getattr(doc, "activeElement", None) if doc is not None else None,
                        )
                        active = getter()
                except Exception:
                    active = None
                shift = bool(getattr(event, "shiftKey", False) or (isinstance(event, dict) and event.get("shiftKey")))
                first = focusable[0]
                last = focusable[-1]
                if active is None:
                    with contextlib.suppress(Exception):
                        first.focus()
                    _prevent(event)
                    return
                if not shift and active is last:
                    with contextlib.suppress(Exception):
                        first.focus()
                    _prevent(event)
                elif shift and active is first:
                    with contextlib.suppress(Exception):
                        last.focus()
                    _prevent(event)
            except Exception:
                pass

        cleanups.append(dom.add_document_event_listener("keydown", _tab))

    def _prevent(event: Any) -> None:
        try:
            fn = getattr(event, "preventDefault", None)
            if fn is not None:
                fn()
        except Exception:
            pass

    def _on_open_change(new_val: bool) -> None:
        if new_val:
            captured[0] = capture_active_element()
            _setup_listeners()
            try:
                host = inject(HOST_PORT_KEY, default=None)
                if host is not None:

                    def _do_focus() -> None:
                        if destroyed[0] or not is_open():
                            return
                        try:
                            dom = inject(DOM_PORT_KEY, default=None)
                            panel = dom.get_element_by_id(panel_id) if dom else None
                            if panel is not None:
                                focus_initial(panel)
                        except Exception:
                            pass

                    host.schedule_macro_task(_do_focus)
            except Exception:
                pass
        else:
            _clear()
            restore_focus(captured[0])
            captured[0] = None

    if is_open_computed is not None:
        is_open_computed.on_after_updating(_on_open_change)
        if is_open():
            captured[0] = capture_active_element()
            try:
                host = inject(HOST_PORT_KEY, default=None)
                if host is not None:

                    def _deferred() -> None:
                        if destroyed[0] or not is_open():
                            return
                        _setup_listeners()

                    host.schedule_macro_task(_deferred)
            except Exception:
                pass

    from webcompy.components._hooks import _register_before_destroy_chained

    def _on_destroy() -> None:
        destroyed[0] = True
        _clear()
        restore_focus(captured[0])

    _register_before_destroy_chained(_on_destroy)

    def _build_container() -> Any:
        backdrop = create_element("div", {"class": _compose_class(_BACKDROP_CLASS, class_backdrop), "id": backdrop_id})
        panel_attrs: dict[str, Any] = {
            "class": _compose_class(_PANEL_CLASS, class_panel),
            "id": panel_id,
            "data-state": "open",
            "data-edge": edge,
        }
        inner = slot_content
        children: list[Any] = []
        if inner is not None:
            if isinstance(inner, list):
                children.extend(inner)
            else:
                children.append(inner)
        panel = create_element("div", panel_attrs, *children)
        container_attrs: dict[str, Any] = {
            "class": _compose_class(_FRAMEWORK_CLASS, class_name),
            "role": "dialog",
            "aria-modal": "true",
            "data-state": "open",
            "data-edge": edge,
        }
        if aria_label:
            container_attrs["aria-label"] = aria_label
        elif aria_labelledby:
            container_attrs["aria-labelledby"] = aria_labelledby
        return create_element("div", container_attrs, backdrop, panel)

    def _child_gen() -> Any:
        cur = is_open()
        if is_open_computed is not None:
            _ = is_open_computed.value
            cur = bool(is_open_computed.value)
        if not cur:
            return None
        return _build_container()

    if is_open_computed is not None and transition_name:
        content: Any = Transition({"name": transition_name}, _child_gen)
        return Teleport({"to": "body"}, content)
    if is_open_computed is not None and not transition_name:
        content2: Any = Transition({"name": "webcompy-headless-drawer", "duration": 0}, _child_gen)
        return Teleport({"to": "body"}, content2)
    inner = _build_container() if bool(open_raw) else None
    if inner is None:
        return Teleport({"to": "body"})
    if transition_name:
        content3: Any = Transition({"name": transition_name}, lambda: inner)
        return Teleport({"to": "body"}, content3)
    return Teleport({"to": "body"}, inner)


Drawer.scoped_style = {}
