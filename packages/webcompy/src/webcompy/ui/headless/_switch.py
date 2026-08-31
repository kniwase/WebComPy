"""Headless Switch control: a checkbox input exposing the ``role="switch"`` pattern."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element
from webcompy.exception import WebComPyException
from webcompy.forms._field import Field
from webcompy.signal import use_computed
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

_FRAMEWORK_CLASS = "webcompy-headless-switch"
_INPUT_CLASS = "webcompy-headless-switch-input"
_LABEL_CLASS = "webcompy-headless-switch-label"


class SwitchProps(TypedDict, total=False):
    """Props for the headless ``Switch`` component."""

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


@define_component(custom_element_name="headless-switch")
def Switch(context: ComponentContext[SwitchProps]) -> Any:
    """Render a checkbox-based switch with ``role="switch"`` semantics.

    The switch binds like a ``Checkbox`` (``field`` or ``value`` plus
    optional ``on_change``, mutually exclusive) and toggles through the
    native checkbox interaction, preserving keyboard behavior. The input
    exposes ``aria-checked`` reflecting the current state. A standalone
    ``label`` wraps the input in a ``<label>``; inside a ``FormField`` the
    label prop is ignored and the input adopts the field's generated ids.

    Args:
        context: Component context with the switch props. ``class_name``
            targets the root (wrapping label or input), ``class_input``
            the input, and ``class_label`` the standalone label.

    Returns:
        The rendered switch element.

    Raises:
        WebComPyException: When both binding modes are supplied or
            ``on_change`` is given without a bound value.

    """
    props = context.props or {}
    ctx = form_field_context()
    bind = resolve_bind_target(props, "Switch")
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.target is None:
        raise WebComPyException("Switch 'on_change' requires a bound 'field' or 'value'")

    signal = bind.signal
    aria_checked = use_computed(lambda: "true" if signal is not None and bool(signal.value) else "false")

    wraps_label = bool(props.get("label")) and ctx is None
    root_class = props.get("class_name", "")

    base: dict[str, Any] = {
        "type": "checkbox",
        "role": "switch",
        "aria-checked": aria_checked,
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
