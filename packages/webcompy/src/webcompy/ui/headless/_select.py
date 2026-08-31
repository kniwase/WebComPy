"""Headless Select control binding a native ``<select>`` to a Field or raw value."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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
    optional_text_attrs,
    resolve_bind_target,
)

_FRAMEWORK_CLASS = "webcompy-headless-select"


class SelectOption(TypedDict, total=False):
    """One option entry for the headless ``Select`` and ``RadioGroup`` controls."""

    value: str
    label: str


class SelectProps(TypedDict, total=False):
    """Props for the headless ``Select`` component."""

    field: Field[Any]
    value: Any
    on_change: Callable[[Any], None]
    options: Sequence[SelectOption]
    id: str
    aria_label: str
    name: str
    disabled: bool
    required: bool
    class_name: str


@define_component(custom_element_name="headless-select")
def Select(context: ComponentContext[SelectProps]) -> Any:
    """Render a native select populated from an options prop.

    The select binds to either a forms-module ``Field`` (``field`` prop)
    or a raw value (``value`` plus optional ``on_change``); supplying both
    is an error. Bound values are option strings: the Signal must carry a
    ``str`` value, and each option's ``value`` is written back unchanged on
    selection. Options are rendered as native ``<option>`` elements, each
    reflecting the ``selected`` state so server-rendered output matches
    the current value. Inside a ``FormField`` the native element adopts the
    field's generated ids; standalone the control renders without them.

    Args:
        context: Component context with the select props. ``options`` is a
            sequence of ``SelectOption`` value/label pairs; an empty label
            falls back to the option value.

    Returns:
        The rendered native ``<select>`` element.

    Raises:
        WebComPyException: When both binding modes are supplied or
            ``on_change`` is given without a bound value.

    """
    props = context.props or {}
    options = props.get("options") or []
    ctx = form_field_context()
    bind = resolve_bind_target(props, "Select")
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.target is None:
        raise WebComPyException("Select 'on_change' requires a bound 'field' or 'value'")

    base: dict[str, Any] = {**optional_text_attrs(props, ("name", "disabled", "required"))}
    attrs = compose_attrs(
        base,
        framework_class=_FRAMEWORK_CLASS,
        props=props,
        state=state,
        control_id=compose_control_id(props, ctx),
    )
    if bind.target is not None:
        attrs[":bind"] = bind.target
    if on_change is not None:
        attrs["@change"] = lambda ev: on_change(bound_value(bind, ""))

    children: list[Any] = []
    current_value = bind.signal.value if bind.signal is not None else None
    for option in options:
        option_value = option.get("value", "")
        option_attrs: dict[str, Any] = {"value": option_value}
        if current_value is not None:
            option_attrs["selected"] = bool(current_value == option_value)
        children.append(create_element("option", option_attrs, option.get("label") or option_value))
    return create_element("select", attrs, *children)
