"""Themed Switch component composing the headless Switch."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._form_utils import join_classes
from webcompy.ui.headless._switch import Switch as HeadlessSwitch
from webcompy.ui.headless._switch import SwitchProps as HeadlessSwitchProps


class SwitchProps(TypedDict, total=False):
    """Props for the themed ``Switch`` component."""

    field: Field[Any]
    value: Any
    on_change: Any
    id: str
    aria_label: str
    label: str
    disabled: bool
    required: bool
    class_name: str
    class_input: str
    class_label: str


@define_component(custom_element_name="webcompy-switch")
def Switch(context: ComponentContext[SwitchProps]) -> Any:
    """Render a themed switch.

    Composes the headless ``Switch`` and supplies token-based default
    classes for the track/thumb visuals and its parts; the
    ``role="switch"`` semantics and binding behavior are inherited.

    Args:
        context: Component context with the switch props.

    Returns:
        The themed switch element.

    """
    props = context.props or {}
    headless_props: HeadlessSwitchProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "label": props.get("label", ""),
        "disabled": props.get("disabled", False),
        "required": props.get("required", False),
        "class_name": join_classes("webcompy-switch", props.get("class_name", "")),
        "class_input": join_classes("webcompy-switch-input", props.get("class_input", "")),
        "class_label": join_classes("webcompy-switch-label", props.get("class_label", "")),
    }
    return HeadlessSwitch(headless_props)  # type: ignore[call-arg]
