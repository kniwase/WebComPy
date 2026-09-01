"""Themed Input component composing the headless Input."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._form_utils import join_classes
from webcompy.ui.headless._input import Input as HeadlessInput
from webcompy.ui.headless._input import InputProps as HeadlessInputProps


class InputProps(TypedDict, total=False):
    """Props for the themed ``Input`` component."""

    field: Field[Any]
    value: Any
    on_change: Any
    input_type: str
    id: str
    aria_label: str
    placeholder: str
    name: str
    disabled: bool
    required: bool
    class_name: str


@define_component(custom_element_name="webcompy-input")
def Input(context: ComponentContext[InputProps]) -> Any:
    """Render a themed text input.

    Composes the headless ``Input`` and supplies token-based default
    classes; all binding, state, and accessibility behavior is inherited
    from the headless component. The user ``class_name`` is appended
    after the themed default so user rules win at equal specificity.

    Args:
        context: Component context with the input props.

    Returns:
        The themed input element.

    """
    props = context.props or {}
    headless_props: HeadlessInputProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "input_type": props.get("input_type", "text"),
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "placeholder": props.get("placeholder", ""),
        "name": props.get("name", ""),
        "disabled": props.get("disabled", False),
        "required": props.get("required", False),
        "class_name": join_classes("webcompy-input", props.get("class_name", "")),
    }
    return HeadlessInput(headless_props)  # type: ignore[call-arg]
