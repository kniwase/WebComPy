"""Themed Toast host."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._toast import ToastHost as HeadlessToastHost
from webcompy.ui.headless._toast import ToastHostProps as HeadlessToastHostProps


class ToastHostProps(TypedDict, total=False):
    """Props for the themed ``ToastHost``."""

    toasts: Any
    on_dismiss: Callable[[str], None]
    on_remove: Callable[[str], None]
    transition_name: str | None
    class_name: str
    class_item: str
    class_dismiss: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-toast-host")
def ToastHost(context: ComponentContext[ToastHostProps]) -> Any:
    """Render a themed toast host.

    Args:
        context: Component context with toast host props.

    Returns:
        The themed toast host element.

    """
    props = context.props or {}
    headless_props: HeadlessToastHostProps = {  # type: ignore[typeddict-item]
        "toasts": props.get("toasts"),
        "on_dismiss": props.get("on_dismiss"),
        "on_remove": props.get("on_remove"),
        "transition_name": props.get("transition_name", "webcompy-toast"),
        "class_name": _compose_class("webcompy-toast-host", props.get("class_name", "")),
        "class_item": _compose_class("webcompy-toast", props.get("class_item", "")),
        "class_dismiss": _compose_class("webcompy-toast-dismiss", props.get("class_dismiss", "")),
    }  # type: ignore[typeddict-item]
    return HeadlessToastHost(headless_props)  # type: ignore[arg-type]
