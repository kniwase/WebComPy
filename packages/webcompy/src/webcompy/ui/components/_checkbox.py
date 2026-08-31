"""Themed Checkbox component composing the headless Checkbox."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._checkbox import Checkbox as HeadlessCheckbox
from webcompy.ui.headless._checkbox import CheckboxProps as HeadlessCheckboxProps
from webcompy.ui.headless._form_utils import join_classes


class CheckboxProps(TypedDict, total=False):
    """Props for the themed ``Checkbox`` component."""

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


@define_component(custom_element_name="webcompy-checkbox")
def Checkbox(context: ComponentContext[CheckboxProps]) -> Any:
    """Render a themed checkbox.

    Composes the headless ``Checkbox`` and supplies token-based default
    classes for the root and its parts; behavior and accessibility
    wiring are inherited.

    Args:
        context: Component context with the checkbox props.

    Returns:
        The themed checkbox element.

    """
    props = context.props or {}
    headless_props: HeadlessCheckboxProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "label": props.get("label", ""),
        "disabled": props.get("disabled", False),
        "required": props.get("required", False),
        "class_name": join_classes("webcompy-checkbox", props.get("class_name", "")),
        "class_input": join_classes("webcompy-checkbox-input", props.get("class_input", "")),
        "class_label": join_classes("webcompy-checkbox-label", props.get("class_label", "")),
    }
    return HeadlessCheckbox(headless_props)  # type: ignore[call-arg]
