"""Themed Dropdown component."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._dropdown import Dropdown as HeadlessDropdown
from webcompy.ui.headless._dropdown import DropdownProps as HeadlessDropdownProps


class DropdownProps(TypedDict, total=False):
    """Props for the themed ``Dropdown``."""

    open: bool
    on_close: Callable[[], None]
    transition_name: str | None
    class_name: str
    class_trigger: str
    class_menu: str
    render_closed: bool


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-dropdown")
def Dropdown(context: ComponentContext[DropdownProps]) -> Any:
    """Render a themed dropdown.

    Args:
        context: Component context with dropdown props and slots.

    Returns:
        The themed dropdown element.

    """
    props = context.props or {}
    # Collect slots
    trigger_content = context.slots("trigger", fallback=lambda: None)
    default_content = context.slots("default", fallback=lambda: None)
    slots: dict[str, Any] = {}
    if trigger_content is not None:
        slots["trigger"] = lambda: trigger_content
    if default_content is not None:
        slots["default"] = lambda: default_content
    headless_props: HeadlessDropdownProps = {
        "open": props.get("open", False),  # type: ignore[typeddict-item]
        "on_close": props.get("on_close"),  # type: ignore[typeddict-item]
        "transition_name": props.get("transition_name", "webcompy-dropdown"),
        "class_name": _compose_class("webcompy-dropdown", props.get("class_name", "")),
        "class_trigger": _compose_class("webcompy-dropdown-trigger", props.get("class_trigger", "")),
        "class_menu": _compose_class("webcompy-dropdown-menu", props.get("class_menu", "")),
        "render_closed": bool(props.get("render_closed", False)),
    }
    return HeadlessDropdown(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
