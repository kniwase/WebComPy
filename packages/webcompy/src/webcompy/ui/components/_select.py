"""Themed Select component composing the headless Select."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._form_utils import join_classes
from webcompy.ui.headless._select import Select as HeadlessSelect
from webcompy.ui.headless._select import SelectOption
from webcompy.ui.headless._select import SelectProps as HeadlessSelectProps


class SelectProps(TypedDict, total=False):
    """Props for the themed ``Select`` component."""

    field: Field[Any]
    value: Any
    on_change: Any
    options: list[SelectOption]
    id: str
    aria_label: str
    name: str
    disabled: bool
    required: bool
    class_name: str


@define_component(custom_element_name="webcompy-select")
def Select(context: ComponentContext[SelectProps]) -> Any:
    """Render a themed native select populated from an options prop.

    Composes the headless ``Select`` and supplies token-based default
    classes; behavior and accessibility wiring are inherited.

    Args:
        context: Component context with the select props.

    Returns:
        The themed select element.

    """
    props = context.props or {}
    headless_props: HeadlessSelectProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "options": props.get("options", []),  # type: ignore[typeddict-item]
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "name": props.get("name", ""),
        "disabled": props.get("disabled", False),
        "required": props.get("required", False),
        "class_name": join_classes("webcompy-select", props.get("class_name", "")),
    }
    return HeadlessSelect(headless_props)  # type: ignore[call-arg]
