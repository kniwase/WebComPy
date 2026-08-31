"""Headless Input control binding a native ``<input>`` to a Field or raw value."""

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
    optional_text_attrs,
    resolve_bind_target,
)

_FRAMEWORK_CLASS = "webcompy-headless-input"

_TEXT_TYPES = ("text", "email", "password", "search", "tel", "url", "number")


class InputProps(TypedDict, total=False):
    """Props for the headless ``Input`` component."""

    field: Field[Any]
    value: Any
    on_change: Callable[[Any], None]
    input_type: str
    id: str
    aria_label: str
    placeholder: str
    name: str
    disabled: bool
    required: bool
    class_name: str


@define_component(custom_element_name="headless-input")
def Input(context: ComponentContext[InputProps]) -> Any:
    """Render a native text input bound through the framework ``:bind`` mechanism.

    The input binds to either a forms-module ``Field`` (``field`` prop) or
    a raw value (``value`` plus optional ``on_change``); supplying both is
    an error. Inside a ``FormField`` the native element adopts the field's
    generated ids so the label association and error description resolve;
    standalone the control renders without them. In the touched-invalid
    state the input carries ``data-state="invalid"`` and ``aria-invalid``.

    Args:
        context: Component context with the input props. ``input_type``
            selects the native type (one of text, email, password, search,
            tel, url, number) and stays static.

    Returns:
        The rendered native ``<input>`` element.

    Raises:
        WebComPyException: When both binding modes are supplied, an
            unsupported ``input_type`` is requested, or ``on_change`` is
            given without a bound value.

    """
    props = context.props or {}
    input_type = props.get("input_type", "text")
    if input_type not in _TEXT_TYPES:
        raise WebComPyException(
            f"Input does not support input_type {input_type!r} (supported: {'|'.join(_TEXT_TYPES)})"
        )

    ctx = form_field_context()
    bind = resolve_bind_target(props, "Input")
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.target is None:
        raise WebComPyException("Input 'on_change' requires a bound 'field' or 'value'")

    base: dict[str, Any] = {
        "type": input_type,
        **optional_text_attrs(props, ("placeholder", "name", "disabled", "required")),
    }
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
        attrs["@input"] = lambda ev: on_change(bound_value(bind, ""))
    return create_element("input", attrs)
