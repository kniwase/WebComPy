"""Headless Collapse component providing an accessible disclosure region."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import Transition, create_element, event
from webcompy.signal import use_computed, use_state
from webcompy.signal._base import SignalBase
from webcompy.ui.headless._dom_id import component_dom_id


class CollapseProps(TypedDict, total=False):
    """Props accepted by the headless ``Collapse`` component.

    ``transition_name`` selects the enter/leave class set driven by the
    Transition capability; pass an empty value for instant expansion.
    ``open`` may be a plain boolean (parent-controlled), a signal-like
    object (two-way), or omitted for an uncontrolled component.
    """

    open: bool
    on_toggle: Callable[[bool], None]
    transition_name: str | None
    class_name: str
    class_trigger: str
    class_content: str


_FRAMEWORK_CLASS = "webcompy-headless-collapse"
_TRIGGER_CLASS = "webcompy-headless-collapse-trigger"
_CONTENT_CLASS = "webcompy-headless-collapse-content"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-collapse")
def Collapse(context: ComponentContext[CollapseProps]) -> Any:
    """Render a disclosure trigger with an animated content region.

    The trigger is a ``button`` carrying ``aria-expanded``,
    ``aria-controls``, and ``data-state="open" | "closed"``. Activating it
    expands/collapses the content region, which is mounted only while
    open and animates through the Transition capability (a None-to-element
    swap, so the enter/leave sequences always run). While mounted the
    content element carries ``data-state="open"``. The open state follows
    the overlay control model: an omitted ``open`` prop lets the component
    own internal state (uncontrolled); a signal-like value is written
    through on toggle; a plain boolean keeps the component parent-driven
    with changes delivered to ``on_toggle``. Generated ids are
    per-instance and hydration-stable. No visual styling is emitted;
    animate the natural height in the themed layer via CSS-only techniques
    (see the themed Collapse documentation).

    Args:
        context: Component context carrying the ``open``, ``on_toggle``,
            ``transition_name``, and class pass-through props, plus the
            ``default`` slot rendered inside the content region.

    Returns:
        The rendered headless collapse element.

    """
    props = context.props or {}
    on_toggle: Callable[[bool], None] | None = props.get("on_toggle")
    class_name = props.get("class_name", "")
    class_trigger = props.get("class_trigger", "")
    class_content = props.get("class_content", "")
    transition_name = props.get("transition_name")

    open_raw = props.get("open")
    external_signal: Any = open_raw if isinstance(open_raw, SignalBase) else None
    internal: Any = None
    if external_signal is None and open_raw is None:
        internal = use_state(lambda: False)

    def _is_open() -> bool:
        if external_signal is not None:
            return bool(external_signal.value)
        if internal is not None:
            return bool(internal.value)
        return bool(open_raw)

    open_computed = use_computed(lambda: _is_open())

    trigger_id = component_dom_id("collapse-trigger", context)
    content_id = component_dom_id("collapse-content", context)

    def _toggle(_ev: Any = None) -> None:
        new_open = not bool(open_computed.value)
        if external_signal is not None:
            with contextlib.suppress(Exception):
                external_signal.value = new_open
        elif internal is not None:
            internal.value = new_open
        if on_toggle is not None:
            on_toggle(new_open)

    trigger_attrs: dict[str, Any] = {
        "id": trigger_id,
        "aria-expanded": use_computed(lambda: "true" if bool(open_computed.value) else "false"),
        "aria-controls": content_id,
        "data-state": use_computed(lambda: "open" if bool(open_computed.value) else "closed"),
        "class": _compose_class(_TRIGGER_CLASS, class_trigger),
        event("click"): _toggle,
    }
    trigger_inner: list[Any] = []
    trigger_content = context.slots("trigger", fallback=lambda: None)
    if trigger_content is not None:
        if isinstance(trigger_content, list):
            trigger_inner.extend(trigger_content)
        else:
            trigger_inner.append(trigger_content)
    trigger_btn = create_element("button", trigger_attrs, *trigger_inner)

    content_slot = context.slots("default", fallback=lambda: None)
    content_inner: list[Any] = []
    if content_slot is not None:
        if isinstance(content_slot, list):
            content_inner.extend(content_slot)
        else:
            content_inner.append(content_slot)
    content_attrs: dict[str, Any] = {
        "id": content_id,
        "role": "region",
        "aria-labelledby": trigger_id,
        "data-state": "open",
        "class": _compose_class(_CONTENT_CLASS, class_content),
    }
    content_div = create_element("div", content_attrs, *content_inner)

    def _child_gen() -> Any:
        if not bool(open_computed.value):
            return None
        return content_div

    content: Any
    if transition_name:
        content = Transition({"name": transition_name}, _child_gen)
    else:
        content = Transition({"name": "webcompy-headless-collapse", "duration": 0}, _child_gen)

    root_attrs: dict[str, Any] = {
        "class": _compose_class(_FRAMEWORK_CLASS, class_name),
    }
    return create_element("div", root_attrs, trigger_btn, content)


Collapse.scoped_style = {}
