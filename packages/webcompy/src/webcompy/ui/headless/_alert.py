"""Headless Alert component providing inline feedback with announcement roles."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element, event
from webcompy.signal import use_computed, use_state

AlertVariant = Literal["info", "success", "warning", "error"]

_ROLE_BY_VARIANT: dict[str, str] = {"info": "status", "success": "status", "warning": "alert", "error": "alert"}


class AlertProps(TypedDict, total=False):
    """Props accepted by the headless ``Alert`` component."""

    variant: str
    dismissable: bool
    on_dismiss: Callable[[], None]
    dismiss_label: str
    class_name: str
    class_dismiss: str


_FRAMEWORK_CLASS = "webcompy-headless-alert"
_DISMISS_CLASS = "webcompy-headless-alert-dismiss"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-alert")
def Alert(context: ComponentContext[AlertProps]) -> Any:
    """Render an inline feedback region with variant-driven semantics.

    The error and warning variants announce assertively through
    ``role="alert"``; info and success are polite via ``role="status"``.
    When ``dismissable`` is set the alert renders an accessible dismiss
    button; activating it hides the alert (the root carries the boolean
    ``hidden`` attribute, removing it from the accessibility tree) and
    invokes the optional ``on_dismiss`` callback. The ``data-variant``
    attribute mirrors the variant for styling hooks; no interaction state
    beyond dismissal is exposed. No visual styling is emitted.

    Args:
        context: Component context carrying the ``variant``,
            ``dismissable``, ``on_dismiss``, ``dismiss_label``, and class
            pass-through props. The ``default`` slot supplies the message.

    Returns:
        The rendered headless alert element.

    """
    props = context.props or {}
    variant = props.get("variant", "info")
    if variant not in _ROLE_BY_VARIANT:
        variant = "info"
    dismissable = bool(props.get("dismissable", False))
    on_dismiss: Callable[[], None] | None = props.get("on_dismiss")
    dismiss_label = props.get("dismiss_label", "Dismiss")

    dismissed = use_state(lambda: False)

    def _dismiss(_ev: Any = None) -> None:
        dismissed.value = True
        if on_dismiss is not None:
            on_dismiss()

    attrs: dict[str, Any] = {
        "role": _ROLE_BY_VARIANT[variant],
        "data-variant": variant,
        "class": _compose_class(_FRAMEWORK_CLASS, props.get("class_name", "")),
        "hidden": use_computed(lambda: bool(dismissed.value)),
    }

    children: list[Any] = []
    content = context.slots("default", fallback=lambda: None)
    if content is not None:
        if isinstance(content, list):
            children.extend(content)
        else:
            children.append(content)
    if dismissable:
        dismiss_attrs: dict[str, Any] = {
            "type": "button",
            "aria-label": dismiss_label,
            "class": _compose_class(_DISMISS_CLASS, props.get("class_dismiss", "")),
            event("click"): _dismiss,
        }
        children.append(create_element("button", dismiss_attrs, dismiss_label))

    return create_element("div", attrs, *children)


Alert.scoped_style = {}
