"""Headless FormField wrapper composing a caption, a bound control, and errors."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element, repeat
from webcompy.exception import WebComPyException
from webcompy.forms._field import Field
from webcompy.signal import use_computed
from webcompy.ui.headless._dom_id import component_dom_id
from webcompy.ui.headless._form_field_context import FormFieldContext
from webcompy.ui.headless._form_utils import join_classes, providing_form_field_context

_FRAMEWORK_CLASS = "webcompy-headless-form-field"
_LABEL_CLASS = "webcompy-headless-form-field-label"
_CONTROL_CLASS = "webcompy-headless-form-field-control"
_ERROR_CLASS = "webcompy-headless-form-field-error"
_ERROR_ITEM_CLASS = "webcompy-headless-form-field-error-message"


class FormFieldProps(TypedDict, total=False):
    """Props for the headless ``FormField`` component."""

    field: Field[Any]
    label: str
    control_id: str
    error_id: str
    class_name: str
    class_label: str
    class_control: str
    class_error: str


@define_component(custom_element_name="headless-form-field")
def FormField(context: ComponentContext[FormFieldProps]) -> Any:
    """Compose a caption, a bound control, and an accessible error region.

    The field's association ids are generated from the instance's
    hydration-stable transfer id (or taken from the ``control_id``/
    ``error_id`` props when a themed wrapper supplies them) and provided
    through the component DI scope for the duration of this render pass
    only, so controls rendered afterwards as siblings never observe them.
    Bound controls rendered in the default slot adopt the ids: the native
    control receives the ``id`` referenced by the caption's
    ``<label for>``, and, while the field is touched and invalid,
    ``aria-invalid="true"`` plus an ``aria-describedby`` link to the error
    region. Error messages render only in the touched-invalid state, so an
    invalid-but-untouched form shows nothing on load. Group controls
    (``RadioGroup``) self-label with a ``legend``; pass no ``label`` here
    for those. The root carries ``data-state`` following the same gating.
    The ``field`` prop is required; raw value mode controls are used
    without a FormField.

    Args:
        context: Component context with the field props and the control
            slot content. ``class_name`` targets the root, ``class_label``
            the caption, ``class_control`` the control wrapper, and
            ``class_error`` the error region.

    Returns:
        The rendered wrapper element.

    Raises:
        WebComPyException: When no ``field`` prop is given.

    """
    props = context.props or {}
    field = props.get("field")
    if field is None:
        raise WebComPyException("FormField requires a 'field' prop")

    control_id = props.get("control_id") or component_dom_id("form-field-control", context)
    error_id = props.get("error_id") or component_dom_id("form-field-error", context)
    ctx = FormFieldContext(control_id=control_id, error_id=error_id, label=props.get("label", ""))

    with providing_form_field_context(context, ctx):
        gated = use_computed(lambda: bool(field.touched.value and field.invalid.value))
        data_state = use_computed(lambda: "invalid" if gated.value else "valid")
        visible_errors = use_computed(lambda: list(field.errors.value) if gated.value else [])

        children: list[Any] = []
        label_text = props.get("label", "")
        if label_text:
            children.append(
                create_element(
                    "label",
                    {"for": control_id, "class": join_classes(_LABEL_CLASS, props.get("class_label", ""))},
                    label_text,
                )
            )

        slot_content = context.slots("default", fallback=lambda: None)
        control_children: list[Any] = []
        if slot_content is not None:
            if isinstance(slot_content, list):
                control_children.extend(slot_content)
            else:
                control_children.append(slot_content)
        children.append(
            create_element(
                "div",
                {"class": join_classes(_CONTROL_CLASS, props.get("class_control", ""))},
                *control_children,
            )
        )

        children.append(
            create_element(
                "div",
                {
                    "id": error_id,
                    "role": "alert",
                    "class": join_classes(_ERROR_CLASS, props.get("class_error", "")),
                },
                repeat(visible_errors, lambda message: create_element("span", {"class": _ERROR_ITEM_CLASS}, message)),
            )
        )

        return create_element(
            "div",
            {"class": join_classes(_FRAMEWORK_CLASS, props.get("class_name", "")), "data-state": data_state},
            *children,
        )
