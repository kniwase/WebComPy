"""Headless Tabs component implementing the WAI-ARIA tabs pattern."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.di import inject
from webcompy.elements import create_element, event
from webcompy.ports._keys import DOM_PORT_KEY
from webcompy.signal import use_computed, use_state
from webcompy.signal._base import SignalBase
from webcompy.ui.headless._dom_id import component_dom_id


class TabItem(TypedDict):
    """One tab entry: stable key, trigger label, and panel content generator."""

    key: str
    label: Any
    content: Callable[[], Any]


class TabsProps(TypedDict, total=False):
    """Props accepted by the headless ``Tabs`` component."""

    tabs: list[TabItem]
    active: str
    on_select: Callable[[str], None]
    aria_label: str
    class_name: str
    class_tablist: str
    class_tab: str
    class_panel: str


_FRAMEWORK_CLASS = "webcompy-headless-tabs"
_TABLIST_CLASS = "webcompy-headless-tabs-tablist"
_TAB_CLASS = "webcompy-headless-tabs-tab"
_PANEL_CLASS = "webcompy-headless-tabs-panel"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def _id_part(key: object) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "-" for ch in str(key))


def _collect(node: Any, into: list[Any]) -> None:
    if node is None:
        return
    if isinstance(node, list):
        into.extend(item for item in node if item is not None)
    else:
        into.append(node)


@define_component(custom_element_name="headless-tabs")
def Tabs(context: ComponentContext[TabsProps]) -> Any:
    """Render an accessible tablist whose panels all stay mounted.

    The root contains a ``role="tablist"`` bar of ``role="tab"`` buttons
    followed by every ``role="tabpanel"``. Inactive panels are hidden with
    the boolean ``hidden`` attribute instead of being unmounted, so panel
    internal state (form input, scroll, component lifecycle) survives
    switches and switching is instant. Tab switching drives no animation:
    element replacement is outside the Transition capability's contract.

    The active tab resolves in three modes: an omitted ``active`` prop lets
    the component own internal state (uncontrolled); a ``SignalBase`` value
    is written through on activation; a plain string keeps the component
    parent-controlled, with changes delivered only to ``on_select``. Each
    tab carries ``aria-selected``, ``aria-controls`` and
    ``data-state="active" | "inactive"`` with roving focus semantics
    (active ``tabindex="0"``, inactive ``"-1"``); Left/Right arrows move
    focus with wrapping and activate automatically, Home/End jump to the
    first/last tab. Generated ids are per-instance and hydration-stable.
    The ``tabs`` list is read once at setup; a different tab set requires
    remounting. Style through ``class_name`` and the part class props and
    the ``data-state`` attributes.

    Args:
        context: Component context carrying the ``tabs``, ``active``,
            ``on_select``, ``aria_label``, and class pass-through props.

    Returns:
        The rendered headless tabs element.

    """
    props = context.props or {}
    tabs: list[TabItem] = list(props.get("tabs") or [])
    keys = [str(item.get("key", "")) for item in tabs]
    on_select: Callable[[str], None] | None = props.get("on_select")
    class_name = props.get("class_name", "")
    class_tablist = props.get("class_tablist", "")
    class_tab = props.get("class_tab", "")
    class_panel = props.get("class_panel", "")

    active_raw = props.get("active")
    external_signal: Any = active_raw if isinstance(active_raw, SignalBase) else None
    internal: Any = None
    if external_signal is None and active_raw is None:
        internal = use_state(lambda: keys[0] if keys else "")

    tablist_id = component_dom_id("tabs-tablist", context)

    def _tab_id(key: str) -> str:
        return component_dom_id(f"tabs-tab-{_id_part(key)}", context)

    def _panel_id(key: str) -> str:
        return component_dom_id(f"tabs-panel-{_id_part(key)}", context)

    def _current_key() -> str | None:
        if external_signal is not None:
            src: Any = external_signal.value
        elif internal is not None:
            src = internal.value
        else:
            src = active_raw
        if src is not None and str(src) in keys:
            return str(src)
        return keys[0] if keys else None

    def _activate(new_key: str) -> None:
        if new_key == _current_key():
            return
        if external_signal is not None:
            with contextlib.suppress(Exception):
                external_signal.value = new_key
        elif internal is not None:
            internal.value = new_key
        if on_select is not None:
            on_select(new_key)

    def _tab_nodes_from(tablist_el: Any) -> list[Any]:
        """Collect ``role="tab"`` element nodes under ``tablist_el`` in document order."""
        found: list[Any] = []
        stack = [tablist_el]
        while stack:
            node = stack.pop()
            try:
                if node.getAttribute("role") == "tab":
                    found.append(node)
            except Exception:
                pass
            children = getattr(node, "childNodes", None)
            if children is None:
                continue
            try:
                count = children.length
            except Exception:
                count = len(children)
            for i in reversed(range(count)):
                child = children[i]
                if child is not None:
                    stack.append(child)
        return found

    def _resolve_tablist(evt_target: Any) -> Any:
        """Find the tablist DOM node for the keydown, port lookup then target walk."""
        try:
            dom = inject(DOM_PORT_KEY, default=None)
            if dom is not None:
                tablist_el = dom.get_element_by_id(tablist_id)
                if tablist_el is not None:
                    return tablist_el
        except Exception:
            pass
        node = evt_target
        while node is not None:
            try:
                if node.getAttribute("role") == "tablist":
                    return node
                node = node.parentNode
            except Exception:
                return None
        return None

    def _focus_tab_at(evt_target: Any, index: int) -> None:
        try:
            tablist_el = _resolve_tablist(evt_target)
            if tablist_el is None:
                return
            tab_els = _tab_nodes_from(tablist_el)
            if 0 <= index < len(tab_els):
                tab_els[index].focus()
        except Exception:
            pass

    def _on_tablist_keydown(evt: Any) -> None:
        key = getattr(evt, "key", None)
        if key is None and isinstance(evt, dict):
            key = evt.get("key")
        if key not in ("ArrowLeft", "ArrowRight", "Home", "End") or not keys:
            return
        cur = _current_key()
        idx = keys.index(cur) if cur is not None and cur in keys else 0
        if key == "ArrowRight":
            nxt = (idx + 1) % len(keys)
        elif key == "ArrowLeft":
            nxt = (idx - 1) % len(keys)
        elif key == "Home":
            nxt = 0
        else:
            nxt = len(keys) - 1
        _activate(keys[nxt])
        target = getattr(evt, "target", None)
        if target is None and isinstance(evt, dict):
            target = evt.get("target")
        _focus_tab_at(target, nxt)
        if hasattr(evt, "preventDefault"):
            evt.preventDefault()

    def _is_active(key: str) -> bool:
        return _current_key() == key

    tab_buttons: list[Any] = []
    panels: list[Any] = []
    for item in tabs:
        key = str(item.get("key", ""))
        label_attrs: dict[str, Any] = {
            "id": _tab_id(key),
            "role": "tab",
            "aria-controls": _panel_id(key),
            "aria-selected": use_computed(lambda k=key: "true" if _is_active(k) else "false"),
            "data-state": use_computed(lambda k=key: "active" if _is_active(k) else "inactive"),
            "tabindex": use_computed(lambda k=key: "0" if _is_active(k) else "-1"),
            "class": _compose_class(_TAB_CLASS, class_tab),
            event("click"): lambda _ev, k=key: _activate(k),
        }
        label_inner: list[Any] = []
        _collect(item.get("label", ""), label_inner)
        tab_buttons.append(create_element("button", label_attrs, *label_inner))

        content = item.get("content")
        panel_inner: list[Any] = []
        _collect(content() if callable(content) else content, panel_inner)
        panel_attrs: dict[str, Any] = {
            "id": _panel_id(key),
            "role": "tabpanel",
            "aria-labelledby": _tab_id(key),
            "data-state": use_computed(lambda k=key: "active" if _is_active(k) else "inactive"),
            "hidden": use_computed(lambda k=key: not _is_active(k)),
            "class": _compose_class(_PANEL_CLASS, class_panel),
        }
        panels.append(create_element("div", panel_attrs, *panel_inner))

    tablist_attrs: dict[str, Any] = {
        "id": tablist_id,
        "role": "tablist",
        "class": _compose_class(_TABLIST_CLASS, class_tablist),
        event("keydown"): _on_tablist_keydown,
    }
    aria_label = props.get("aria_label", "")
    if aria_label:
        tablist_attrs["aria-label"] = aria_label

    root_attrs: dict[str, Any] = {"class": _compose_class(_FRAMEWORK_CLASS, class_name)}
    tablist = create_element("div", tablist_attrs, *tab_buttons)
    return create_element("div", root_attrs, tablist, *panels)


Tabs.scoped_style = {}
