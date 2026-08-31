"""Themed FormField component composing the headless FormField wrapper."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._form_field import FormField as HeadlessFormField
from webcompy.ui.headless._form_field import FormFieldProps as HeadlessFormFieldProps
from webcompy.ui.headless._form_field_context import FORM_FIELD_CONTEXT_KEY, FormFieldContext
from webcompy.ui.headless._form_utils import instance_dom_id, join_classes


class FormFieldProps(TypedDict, total=False):
    """Props for the themed ``FormField`` component."""

    field: Field[Any]
    label: str
    class_name: str
    class_label: str
    class_control: str
    class_error: str


@define_component(custom_element_name="webcompy-form-field")
def FormField(context: ComponentContext[FormFieldProps]) -> Any:
    """Render a themed form field wrapper.

    Composes the headless ``FormField`` and supplies token-based default
    classes for the label, control wrapper, and error region; the error
    gating behavior is inherited. The association-id context is provided
    from this component's scope before slot contents are produced, so
    controls created through the themed wrapper resolve the ids, and the
    headless wrapper reuses the provided context instead of generating
    its own.

    Args:
        context: Component context with the field props and the control
            slot content.

    Returns:
        The themed form field element.

    """
    props = context.props or {}
    label_text = props.get("label", "")
    base = context.transfer_id
    context.provide(
        FORM_FIELD_CONTEXT_KEY,
        FormFieldContext(
            control_id=instance_dom_id("form-field-control", base),
            error_id=instance_dom_id("form-field-error", base),
            label=label_text,
        ),
    )
    slot_content = context.slots("default", fallback=lambda: None)
    headless_props: HeadlessFormFieldProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "label": label_text,
        "class_name": join_classes("webcompy-form-field", props.get("class_name", "")),
        "class_label": join_classes("webcompy-form-field-label", props.get("class_label", "")),
        "class_control": join_classes("webcompy-form-field-control", props.get("class_control", "")),
        "class_error": join_classes("webcompy-form-field-error", props.get("class_error", "")),
    }
    slots: dict[str, Any] = {}
    if slot_content is not None:
        slots["default"] = lambda: slot_content
    return HeadlessFormField(headless_props, slots=slots)  # type: ignore[call-arg]
