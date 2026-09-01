"""Headless Textarea control binding a native ``<textarea>`` to a Field or raw value."""

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

_FRAMEWORK_CLASS = "webcompy-headless-textarea"


class TextareaProps(TypedDict, total=False):
    """Props for the headless ``Textarea`` component."""

    field: Field[Any]
    value: Any
    on_change: Callable[[Any], None]
    id: str
    aria_label: str
    placeholder: str
    name: str
    rows: int
    disabled: bool
    required: bool
    class_name: str


@define_component(custom_element_name="headless-textarea")
def Textarea(context: ComponentContext[TextareaProps]) -> Any:
    """Render a native textarea bound through the framework ``:bind`` mechanism.

    The textarea binds to either a forms-module ``Field`` (``field`` prop)
    or a raw value (``value`` plus optional ``on_change``); supplying both
    is an error. Inside a ``FormField`` the native element adopts the
    field's generated ids; standalone the control renders without them.
    The bound text content is the reactive value (textareas expose no
    ``value`` attribute in markup), matching the framework binding rules.

    Args:
        context: Component context with the textarea props. ``rows`` sets
            the visible line count.

    Returns:
        The rendered native ``<textarea>`` element.

    Raises:
        WebComPyException: When both binding modes are supplied or
            ``on_change`` is given without a bound value.

    """
    props = context.props or {}
    ctx = form_field_context()
    bind = resolve_bind_target(props, "Textarea")
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.target is None:
        raise WebComPyException("Textarea 'on_change' requires a bound 'field' or 'value'")

    base: dict[str, Any] = {**optional_text_attrs(props, ("placeholder", "name", "rows", "disabled", "required"))}
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
    return create_element("textarea", attrs)
