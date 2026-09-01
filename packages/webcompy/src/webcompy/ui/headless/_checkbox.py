"""Headless Checkbox control binding a native checkbox input to a Field or raw value."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element
from webcompy.exception import WebComPyException
from webcompy.forms._field import Field
from webcompy.ui.headless._form_utils import (
    bound_value,
    compose_attrs,
    compose_control_id,
    control_state,
    form_field_context,
    join_classes,
    optional_text_attrs,
    resolve_bind_target,
)

_FRAMEWORK_CLASS = "webcompy-headless-checkbox"
_INPUT_CLASS = "webcompy-headless-checkbox-input"
_LABEL_CLASS = "webcompy-headless-checkbox-label"


class CheckboxProps(TypedDict, total=False):
    """Props for the headless ``Checkbox`` component."""

    field: Field[Any]
    value: Any
    on_change: Callable[[Any], None]
    id: str
    aria_label: str
    label: str
    disabled: bool
    required: bool
    class_name: str
    class_input: str
    class_label: str


@define_component(custom_element_name="headless-checkbox")
def Checkbox(context: ComponentContext[CheckboxProps]) -> Any:
    """Render a native checkbox bound through the framework ``:bind`` mechanism.

    The checkbox binds to either a forms-module ``Field`` carrying a
    ``bool`` value (``field`` prop) or a raw value (``value`` plus
    optional ``on_change``); supplying both is an error. When a
    standalone ``label`` prop is given the input is wrapped in a native
    ``<label>`` for implicit association; inside a ``FormField`` the
    ``label`` prop is ignored because the FormField supplies the caption,
    and the native input adopts the field's generated ids instead. In
    the touched-invalid state the input carries ``data-state="invalid"``
    and ``aria-invalid``.

    Args:
        context: Component context with the checkbox props. ``class_name``
            targets the root element (the wrapping label when present,
            otherwise the input), ``class_input`` the input element, and
            ``class_label`` the standalone label.

    Returns:
        The rendered checkbox element.

    Raises:
        WebComPyException: When both binding modes are supplied or
            ``on_change`` is given without a bound value.

    """
    props = context.props or {}
    ctx = form_field_context()
    bind = resolve_bind_target(props, "Checkbox")
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.target is None:
        raise WebComPyException("Checkbox 'on_change' requires a bound 'field' or 'value'")

    wraps_label = bool(props.get("label")) and ctx is None
    root_class = props.get("class_name", "")

    base: dict[str, Any] = {
        "type": "checkbox",
        **optional_text_attrs(props, ("disabled", "required")),
    }
    attrs = compose_attrs(
        base,
        framework_class=_INPUT_CLASS,
        props=props,
        state=state,
        control_id=compose_control_id(props, ctx),
    )
    attrs["class"] = join_classes(
        "" if wraps_label else _FRAMEWORK_CLASS,
        _INPUT_CLASS,
        props.get("class_input", ""),
        "" if wraps_label else root_class,
    )
    if bind.target is not None:
        attrs[":bind"] = bind.target
    if on_change is not None:
        attrs["@change"] = lambda ev: on_change(bound_value(bind, False))
    input_el = create_element("input", attrs)

    if wraps_label:
        label_attrs: dict[str, Any] = {
            "class": join_classes(_FRAMEWORK_CLASS, _LABEL_CLASS, props.get("class_label", ""), root_class),
        }
        return create_element("label", label_attrs, input_el, props.get("label", ""))
    return input_el
