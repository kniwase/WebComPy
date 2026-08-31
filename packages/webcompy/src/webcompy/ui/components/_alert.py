"""Themed Alert component composing the headless Alert with token styling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._alert import _ROLE_BY_VARIANT
from webcompy.ui.headless._alert import Alert as HeadlessAlert
from webcompy.ui.headless._alert import AlertProps as HeadlessAlertProps


class ThemedAlertProps(TypedDict, total=False):
    """Props accepted by the themed ``Alert`` component."""

    variant: str
    dismissable: bool
    on_dismiss: Callable[[], None]
    dismiss_label: str
    class_name: str
    class_dismiss: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-alert")
def Alert(context: ComponentContext[ThemedAlertProps]) -> Any:
    """Render a themed inline alert.

    Composes the headless ``Alert`` and supplies the default
    ``webcompy-alert`` classes with a ``webcompy-alert--{variant}``
    modifier whose rules live in the shipped primitives stylesheet.
    Role mapping, dismissal, and accessibility come from the headless
    component; user classes are appended after the themed defaults.

    Args:
        context: Component context carrying the ``variant``,
            ``dismissable``, ``on_dismiss``, ``dismiss_label``, and class
            pass-through props, plus the message in the ``default`` slot.

    Returns:
        The rendered themed alert element.

    """
    props = context.props or {}
    variant = props.get("variant", "info")
    if variant not in _ROLE_BY_VARIANT:
        variant = "info"
    headless_props: HeadlessAlertProps = {
        "variant": variant,
        "dismissable": bool(props.get("dismissable", False)),
        "on_dismiss": props.get("on_dismiss"),  # type: ignore[typeddict-item]
        "dismiss_label": props.get("dismiss_label", "Dismiss"),
        "class_name": _compose_class(f"webcompy-alert webcompy-alert--{variant}", props.get("class_name", "")),
        "class_dismiss": _compose_class("webcompy-alert-dismiss", props.get("class_dismiss", "")),
    }
    content = context.slots("default", fallback=lambda: None)
    slots: dict[str, Any] = {}
    if content is not None:
        slots["default"] = lambda: content
    return HeadlessAlert(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
