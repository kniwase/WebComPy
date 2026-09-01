"""Themed FormField component composing the headless FormField wrapper."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.forms._field import Field
from webcompy.ui.headless._dom_id import component_dom_id
from webcompy.ui.headless._form_field import FormField as HeadlessFormField
from webcompy.ui.headless._form_field import FormFieldProps as HeadlessFormFieldProps
from webcompy.ui.headless._form_field_context import FormFieldContext
from webcompy.ui.headless._form_utils import join_classes, providing_form_field_context


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
    the instance's transfer id, provided to the DI scope for the duration
    of this render pass only (siblings rendered afterwards never observe
    them), and forwarded to the headless wrapper as ``control_id`` /
    ``error_id`` props so caption, control, and error region agree.

    Args:
        context: Component context with the field props and the control
            slot content.

    Returns:
        The themed form field element.

    """
    props = context.props or {}
    control_id = props.get("control_id", "") or component_dom_id("form-field-control", context)
    error_id = props.get("error_id", "") or component_dom_id("form-field-error", context)
    with providing_form_field_context(
        context, FormFieldContext(control_id=control_id, error_id=error_id, label=props.get("label", ""))
    ):
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
