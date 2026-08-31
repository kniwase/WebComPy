"""Themed Textarea component composing the headless Textarea."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._form_utils import join_classes
from webcompy.ui.headless._textarea import Textarea as HeadlessTextarea
from webcompy.ui.headless._textarea import TextareaProps as HeadlessTextareaProps


class TextareaProps(TypedDict, total=False):
    """Props for the themed ``Textarea`` component."""

    field: Field[Any]
    value: Any
    on_change: Any
    id: str
    aria_label: str
    placeholder: str
    name: str
    rows: int
    disabled: bool
    required: bool
    class_name: str


@define_component(custom_element_name="webcompy-textarea")
def Textarea(context: ComponentContext[TextareaProps]) -> Any:
    """Render a themed multiline text area.

    Composes the headless ``Textarea`` and supplies token-based default
    classes; behavior and accessibility wiring are inherited.

    Args:
        context: Component context with the textarea props.

    Returns:
        The themed textarea element.

    """
    props = context.props or {}
    headless_props: HeadlessTextareaProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "value": props.get("value"),  # type: ignore[typeddict-item]
        "on_change": props.get("on_change"),  # type: ignore[typeddict-item]
        "id": props.get("id", ""),
        "aria_label": props.get("aria_label", ""),
        "placeholder": props.get("placeholder", ""),
        "name": props.get("name", ""),
        "rows": props.get("rows", 4),
        "disabled": props.get("disabled", False),
        "required": props.get("required", False),
        "class_name": join_classes("webcompy-textarea", props.get("class_name", "")),
    }
    return HeadlessTextarea(headless_props)  # type: ignore[call-arg]
