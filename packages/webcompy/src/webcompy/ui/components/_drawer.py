"""Themed Drawer component."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._drawer import Drawer as HeadlessDrawer
from webcompy.ui.headless._drawer import DrawerProps as HeadlessDrawerProps


class DrawerProps(TypedDict, total=False):
    """Props for the themed ``Drawer``."""

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


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-drawer")
def Drawer(context: ComponentContext[DrawerProps]) -> Any:
    """Render a themed drawer.

    Args:
        context: Component context with drawer props.

    Returns:
        The themed drawer element.

    """
    props = context.props or {}
    slot_content = context.slots("default", fallback=lambda: None)
    headless_props: HeadlessDrawerProps = {
        "open": props.get("open", False),  # type: ignore[typeddict-item]
        "on_close": props.get("on_close"),  # type: ignore[typeddict-item]
        "edge": props.get("edge", "right"),  # type: ignore[typeddict-item]
        "aria_label": props.get("aria_label", ""),  # type: ignore[typeddict-item]
        "aria_labelledby": props.get("aria_labelledby", ""),  # type: ignore[typeddict-item]
        "close_on_backdrop": props.get("close_on_backdrop", True),  # type: ignore[typeddict-item]
        "close_on_escape": props.get("close_on_escape", True),  # type: ignore[typeddict-item]
        "transition_name": props.get("transition_name", "webcompy-drawer"),
        "class_name": _compose_class("webcompy-drawer", props.get("class_name", "")),
        "class_backdrop": _compose_class("webcompy-drawer-backdrop", props.get("class_backdrop", "")),
        "class_panel": _compose_class("webcompy-drawer-panel", props.get("class_panel", "")),
    }
    slots: dict[str, Any] = {}
    try:
        inner = slot_content
        if inner is not None:
            slots["default"] = lambda: inner
    except Exception:
        pass
    return HeadlessDrawer(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
