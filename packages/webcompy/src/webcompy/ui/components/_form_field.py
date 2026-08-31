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
    control_id: str
    error_id: str
    class_name: str
    class_label: str
    class_control: str
    class_error: str


@define_component(custom_element_name="webcompy-form-field")
def FormField(context: ComponentContext[FormFieldProps]) -> Any:
    """Render a themed form field wrapper.

    Composes the headless ``FormField`` and supplies token-based default
    classes for the label, control wrapper, and error region; the error
    gating behavior is inherited. Because slot content evaluates eagerly
    in this wrapper's pass, the association ids are generated here from
    the instance's transfer id, provided to the DI scope before the slot
    renders, and forwarded to the headless wrapper as ``control_id`` /
    ``error_id`` props so caption, control, and error region agree.

    Args:
        context: Component context with the field props and the control
            slot content.

    Returns:
        The themed form field element.

    """
    props = context.props or {}
    base = context.transfer_id
    control_id = props.get("control_id", "") or instance_dom_id("form-field-control", base)
    error_id = props.get("error_id", "") or instance_dom_id("form-field-error", base)
    context.provide(
        FORM_FIELD_CONTEXT_KEY, FormFieldContext(control_id=control_id, error_id=error_id, label=props.get("label", ""))
    )
    slot_content = context.slots("default", fallback=lambda: None)
    headless_props: HeadlessFormFieldProps = {
        "field": props.get("field"),  # type: ignore[typeddict-item]
        "label": props.get("label", ""),
        "control_id": control_id,
        "error_id": error_id,
        "class_name": join_classes("webcompy-form-field", props.get("class_name", "")),
        "class_label": join_classes("webcompy-form-field-label", props.get("class_label", "")),
        "class_control": join_classes("webcompy-form-field-control", props.get("class_control", "")),
        "class_error": join_classes("webcompy-form-field-error", props.get("class_error", "")),
    }
    slots: dict[str, Any] = {}
    if slot_content is not None:
        slots["default"] = lambda: slot_content
    return HeadlessFormField(headless_props, slots=slots)  # type: ignore[call-arg]
