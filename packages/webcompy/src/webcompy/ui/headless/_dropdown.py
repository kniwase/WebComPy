"""Headless Dropdown component with menu button pattern."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.components._libs import generate_id
from webcompy.di import inject
from webcompy.elements import Teleport, Transition, create_element
from webcompy.ports._keys import DOM_PORT_KEY, HOST_PORT_KEY
from webcompy.signal import use_computed
from webcompy.signal._base import SignalBase


class DropdownProps(TypedDict, total=False):
    """Props for the headless ``Dropdown`` component."""

    open: bool
    on_close: Callable[[], None]
    transition_name: str | None
    class_name: str
    class_trigger: str
    class_menu: str


_FRAMEWORK_CLASS = "webcompy-headless-dropdown"
_TRIGGER_CLASS = "webcompy-headless-dropdown-trigger"
_MENU_CLASS = "webcompy-headless-dropdown-menu"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-dropdown")
def Dropdown(context: ComponentContext[DropdownProps]) -> Any:
    """Render a dropdown trigger and menu with keyboard navigation.

    The trigger is a button and the menu is a ``role="menu"`` list
    whose items carry ``role="menuitem"``. The menu renders through
    ``Teleport`` to ``body`` wrapped in a ``Transition``.

    Args:
        context: Component context with dropdown props and named slots
            ``trigger`` and ``default``.

    Returns:
        The rendered dropdown element.

    """
    props = context.props or {}
    open_raw = props.get("open", False)
    on_close = props.get("on_close")
    transition_name = props.get("transition_name")
    class_name = props.get("class_name", "")
    class_trigger = props.get("class_trigger", "")
    class_menu = props.get("class_menu", "")

    trigger_id = f"webcompy-dropdown-trigger-{generate_id('dropdown')[:8]}"
    menu_id = f"webcompy-dropdown-menu-{generate_id('menu')[:8]}"

    is_signal = isinstance(open_raw, SignalBase)
    if is_signal:
        is_open_computed = use_computed(lambda: bool(open_raw.value))  # type: ignore[union-attr]
        is_open = lambda: bool(is_open_computed.value)
    else:
        is_open_computed = None
        is_open = lambda: bool(open_raw)

    trigger_content = context.slots("trigger", fallback=lambda: "Menu")  # type: ignore[assignment]
    menu_children = context.slots("default", fallback=lambda: None)  # type: ignore[assignment]

    cleanups: list[Callable[[], None]] = []
    trigger_ref: list[Any] = [None]
    menu_ref: list[Any] = [None]

    def _clear() -> None:
        while cleanups:
            fn = cleanups.pop()
            with contextlib.suppress(Exception):
                fn()

    def _setup_outside() -> None:
        _clear()
        if not is_open():
            return
        try:
            dom = inject(DOM_PORT_KEY, default=None)
        except Exception:
            dom = None
        if dom is None:
            return

        def _outside(event: Any) -> None:
            if not is_open():
                return
            target = getattr(event, "target", None)
            if target is None and isinstance(event, dict):
                target = event.get("target")
            if target is None:
                return
            # Direct id check for Fake DOM compatibility
            try:
                tid = getattr(target, "getAttribute", lambda _: None)("id")
                if tid == trigger_id:
                    return
                if tid == menu_id:
                    return
                # Also check class-based trigger identification
                tcls = getattr(target, "getAttribute", lambda _: None)("class") or ""
                if trigger_id in tcls or menu_id in tcls:
                    return
            except Exception:
                pass
            # Exclude trigger and menu via DOM lookup
            trigger_el = None
            menu_el = None
            try:
                trigger_el = dom.get_element_by_id(trigger_id) if dom else None
                menu_el = dom.get_element_by_id(menu_id) if dom else None
                if trigger_el is None:
                    trigger_el = trigger_ref[0]
                if menu_el is None:
                    menu_el = menu_ref[0]
            except Exception:
                pass

            def _contains(ancestor: Any, t: Any) -> bool:
                n: Any = t
                while n is not None:
                    if n is ancestor:
                        return True
                    try:
                        n = n.parentNode
                    except Exception:
                        return False
                return False

            if trigger_el is not None and _contains(trigger_el, target):
                return
            if menu_el is not None and _contains(menu_el, target):
                return
            if on_close is not None:
                on_close()

        cleanups.append(dom.add_document_event_listener("click", _outside))

        def _esc(event: Any) -> None:
            if not is_open():
                return
            key = getattr(event, "key", None)
            if key is None and isinstance(event, dict):
                key = event.get("key")
            if key == "Escape":
                if on_close is not None:
                    on_close()
                # Focus return to trigger
                try:
                    trig = dom.get_element_by_id(trigger_id) if dom else None
                    if trig is not None:
                        trig.focus()
                except Exception:
                    pass

        cleanups.append(dom.add_document_event_listener("keydown", _esc))

    def _on_open_change(new_val: bool) -> None:
        if new_val:
            _setup_outside()
            # Focus first menu item after a tick
            try:
                host = inject(HOST_PORT_KEY, default=None)
                if host is not None:
                    host.schedule_macro_task(_focus_first)
            except Exception:
                pass
        else:
            _clear()
            # Focus return to trigger
            try:
                dom = inject(DOM_PORT_KEY, default=None)
                trig = dom.get_element_by_id(trigger_id) if dom else None
                if trig is not None:
                    trig.focus()
            except Exception:
                pass

    def _focus_first() -> None:
        try:
            dom = inject(DOM_PORT_KEY, default=None)
            if dom is None:
                return
            menu_el = dom.get_element_by_id(menu_id)
            if menu_el is None:
                return
            # Find menuitems
            try:
                items = dom.query_selector_all('[role="menuitem"]', root=menu_el)
                # Filter out disabled
                enabled = [
                    it
                    for it in items
                    if it.getAttribute("aria-disabled") != "true" and it.getAttribute("data-disabled") != "true"
                ]
                if enabled:
                    enabled[0].focus()
            except Exception:
                pass
        except Exception:
            pass

    if is_open_computed is not None:
        is_open_computed.on_after_updating(_on_open_change)
        if is_open():
            try:
                host = inject(HOST_PORT_KEY, default=None)
                if host is not None:
                    host.schedule_macro_task(_setup_outside)
            except Exception:
                pass

    from webcompy.components._hooks import _register_before_destroy_chained

    _register_before_destroy_chained(_clear)

    # Toggle handler for trigger
    def _on_trigger_click(event: Any) -> None:
        if is_signal:
            # Toggle via signal mutation if possible
            try:
                open_raw.value = not bool(open_raw.value)  # type: ignore[union-attr]
                return
            except Exception:
                pass
        # For non-signal, if open, close via on_close; if closed, no-op (parent controls)
        if is_open() and on_close is not None:
            on_close()

    from webcompy.elements import event

    trigger_attrs: dict[str, Any] = {
        "id": trigger_id,
        "aria-expanded": "true" if is_open() else "false",
        "aria-haspopup": "menu",
        "aria-controls": menu_id,
        "data-state": "open" if is_open() else "closed",
        "class": _compose_class(_TRIGGER_CLASS, class_trigger),
        event("click"): _on_trigger_click,
    }
    # For reactive, aria-expanded and data-state should be computed
    if is_signal:
        trigger_attrs["aria-expanded"] = use_computed(lambda: "true" if bool(is_open_computed.value) else "false")  # type: ignore[union-attr]
        trigger_attrs["data-state"] = use_computed(lambda: "open" if bool(is_open_computed.value) else "closed")  # type: ignore[union-attr]

    trigger_inner: list[Any] = []
    tc = trigger_content
    if tc is not None:
        if isinstance(tc, list):
            trigger_inner.extend(tc)
        else:
            trigger_inner.append(tc)
    trigger_btn = create_element("button", trigger_attrs, *trigger_inner)
    # Store refs for outside detection (virtual element reference, will be resolved via DOM query after mount)
    trigger_ref[0] = trigger_btn

    def _on_menu_keydown(event: Any) -> None:
        if not is_open():
            return
        key = getattr(event, "key", None)
        if key is None and isinstance(event, dict):
            key = event.get("key")
        if key not in ("ArrowDown", "ArrowUp", "Home", "End", "Enter", " ", "Escape"):
            return
        try:
            dom = inject(DOM_PORT_KEY, default=None)
            menu_el = dom.get_element_by_id(menu_id) if dom else None
            if menu_el is None:
                return
            items = dom.query_selector_all('[role="menuitem"]', root=menu_el) if dom else []
            enabled = [
                it
                for it in items
                if it.getAttribute("aria-disabled") != "true" and it.getAttribute("data-disabled") != "true"
            ]
            if not enabled:
                return
            # Find current focus
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
            idx = -1
            for i, it in enumerate(enabled):
                if it is active:
                    idx = i
                    break
            if key == "ArrowDown":
                nxt = (idx + 1) % len(enabled) if idx >= 0 else 0
                enabled[nxt].focus()
                if hasattr(event, "preventDefault"):
                    event.preventDefault()
            elif key == "ArrowUp":
                nxt = (idx - 1) % len(enabled) if idx >= 0 else len(enabled) - 1
                enabled[nxt].focus()
                if hasattr(event, "preventDefault"):
                    event.preventDefault()
            elif key == "Home":
                enabled[0].focus()
                if hasattr(event, "preventDefault"):
                    event.preventDefault()
            elif key == "End":
                enabled[-1].focus()
                if hasattr(event, "preventDefault"):
                    event.preventDefault()
            elif key == "Escape":
                if on_close is not None:
                    on_close()
                try:
                    trig = dom.get_element_by_id(trigger_id) if dom else None
                    if trig is not None:
                        trig.focus()
                except Exception:
                    pass
                if hasattr(event, "preventDefault"):
                    event.preventDefault()
            elif key in ("Enter", " "):
                if active is not None and active in enabled:
                    # Dispatch click on active
                    import contextlib

                    with contextlib.suppress(Exception):
                        active.dispatchEvent(active)  # type: ignore[attr-defined]
                    # Also try on_click via getAttribute? For virtual, dispatch may not work
                    # Call on_close to close menu
                    if on_close is not None:
                        on_close()
                if hasattr(event, "preventDefault"):
                    event.preventDefault()
        except Exception:
            pass

    menu_attrs: dict[str, Any] = {
        "id": menu_id,
        "role": "menu",
        "data-state": "open" if is_open() else "closed",
        "class": _compose_class(_MENU_CLASS, class_menu),
        event("keydown"): _on_menu_keydown,
    }
    if is_signal:
        menu_attrs["data-state"] = use_computed(lambda: "open" if bool(is_open_computed.value) else "closed")  # type: ignore[union-attr]

    menu_children: list[Any] = []
    mc = menu_children_raw = menu_children  # noqa: F841
    # menu_children from slot
    # Actually menu_children is from default slot
    # Re-evaluate: menu slot content
    m_content = context.slots("default", fallback=lambda: None)
    # But we already have menu_children via earlier? Let's use m_content
    menu_inner: list[Any] = []
    if m_content is not None:
        if isinstance(m_content, list):
            menu_inner.extend(m_content)
        else:
            menu_inner.append(m_content)
    menu_el = create_element("ul", menu_attrs, *menu_inner)
    menu_ref[0] = menu_el

    def _child_gen() -> Any:
        cur = is_open()
        if is_open_computed is not None:
            _ = is_open_computed.value
            cur = bool(is_open_computed.value)
        if not cur:
            return None
        return menu_el

    if is_signal and transition_name:
        content: Any = Transition({"name": transition_name}, _child_gen)
        teleported: Any = Teleport({"to": "body"}, content)
    elif is_signal and not transition_name:
        content2: Any = Transition({"name": "webcompy-headless-dropdown", "duration": 0}, _child_gen)
        teleported = Teleport({"to": "body"}, content2)
    else:
        inner = menu_el if bool(open_raw) else None
        if inner is None:
            teleported = None
        elif transition_name:
            content3: Any = Transition({"name": transition_name}, lambda: inner)
            teleported = Teleport({"to": "body"}, content3)
        else:
            teleported = Teleport({"to": "body"}, inner)

    root_attrs: dict[str, Any] = {
        "class": _compose_class(_FRAMEWORK_CLASS, class_name),
        "data-state": "open" if is_open() else "closed",
    }
    if is_signal:
        root_attrs["data-state"] = use_computed(lambda: "open" if bool(is_open_computed.value) else "closed")  # type: ignore[union-attr]

    children: list[Any] = [trigger_btn]
    if teleported is not None:
        children.append(teleported)
    return create_element("div", root_attrs, *children)


Dropdown.scoped_style = {}
