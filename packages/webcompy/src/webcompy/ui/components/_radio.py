"""Themed Radio and RadioGroup components composing the headless controls."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._form_utils import join_classes
from webcompy.ui.headless._radio import Radio as HeadlessRadio
from webcompy.ui.headless._radio import RadioGroup as HeadlessRadioGroup
from webcompy.ui.headless._radio import RadioGroupProps as HeadlessRadioGroupProps
from webcompy.ui.headless._radio import RadioProps as HeadlessRadioProps
from webcompy.ui.headless._select import SelectOption


class RadioProps(TypedDict, total=False):
    """Props for the themed ``Radio`` component."""

    field: Field[Any]
    value: Any
    on_change: Any
    option_value: str
    name: str
    id: str
    aria_label: str
    disabled: bool
    class_name: str


@define_component(custom_element_name="webcompy-radio")
def Radio(context: ComponentContext[RadioProps]) -> Any:
    """Render a themed standalone native radio for custom group compositions.

    Args:
        context: Component context with the radio props.

    Returns:
        The themed radio input element.

    """
    props = context.props or {}
    headless_props: HeadlessRadioProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "option_value": props.get("option_value", ""),
        "name": props.get("name", ""),
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "disabled": props.get("disabled", False),
        "class_name": join_classes("webcompy-radio", props.get("class_name", "")),
    }
    return HeadlessRadio(headless_props)  # type: ignore[call-arg]


class RadioGroupProps(TypedDict, total=False):
    """Props for the themed ``RadioGroup`` component."""

    field: Field[Any]
    value: Any
    on_change: Any
    options: list[SelectOption]
    legend: str
    id: str
    aria_label: str
    disabled: bool
    required: bool
    class_name: str
    class_input: str
    class_label: str
    class_legend: str


@define_component(custom_element_name="webcompy-radio-group")
def RadioGroup(context: ComponentContext[RadioGroupProps]) -> Any:
    """Render a themed radio group (fieldset with same-name radios).

    Composes the headless ``RadioGroup`` and supplies token-based default
    classes for the fieldset, legend, items, and radios; the shared
    generated ``name`` and native keyboard behavior are inherited.

    Args:
        context: Component context with the radio group props.

    Returns:
        The themed fieldset element.

    """
    props = context.props or {}
    headless_props: HeadlessRadioGroupProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "options": props.get("options", []),  # type: ignore[typeddict-item]
        "legend": props.get("legend", ""),
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "disabled": props.get("disabled", False),
        "required": props.get("required", False),
        "class_name": join_classes("webcompy-radio-group", props.get("class_name", "")),
        "class_input": join_classes("webcompy-radio", props.get("class_input", "")),
        "class_label": join_classes("webcompy-radio-group-item", props.get("class_label", "")),
        "class_legend": join_classes("webcompy-radio-group-legend", props.get("class_legend", "")),
    }
    return HeadlessRadioGroup(headless_props)  # type: ignore[call-arg]
