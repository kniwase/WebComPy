"""Headless Radio and RadioGroup controls grouping native radios in a fieldset."""

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
    control_state,
    form_field_context,
    instance_dom_id,
    join_classes,
    optional_text_attrs,
    resolve_bind_target,
)
from webcompy.ui.headless._select import SelectOption

_FRAMEWORK_CLASS = "webcompy-headless-radio-group"
_FIELDSET_CLASS = "webcompy-headless-radio-group-fieldset"
_LEGEND_CLASS = "webcompy-headless-radio-group-legend"
_ITEM_CLASS = "webcompy-headless-radio-group-item"
_INPUT_CLASS = "webcompy-headless-radio-group-input"

_RADIO_FRAMEWORK_CLASS = "webcompy-headless-radio"


class RadioProps(TypedDict, total=False):
    """Props for the headless ``Radio`` component."""

    field: Field[Any]
    value: Any
    on_change: Callable[[Any], None]
    option_value: str
    name: str
    id: str
    aria_label: str
    disabled: bool
    class_name: str


@define_component(custom_element_name="headless-radio")
def Radio(context: ComponentContext[RadioProps]) -> Any:
    """Render a standalone native radio for custom group compositions.

    The radio's ``checked`` state compares the shared group binding (a
    ``Field`` or raw ``Signal`` in the ``value`` prop) with the static
    ``option_value`` prop, and selecting it writes ``option_value`` back
    through the framework ``:bind`` mechanism. A plain (non-Signal)
    ``value`` is not meaningful for radios because the group signal must
    be shared; bind a ``Field`` or pass a ``Signal``. The caller supplies
    the shared ``name`` so native arrow-key navigation applies;
    ``RadioGroup`` is the intended default for grouped radios.

    Args:
        context: Component context with the radio props.

    Returns:
        The rendered native ``<input type="radio">`` element.

    Raises:
        WebComPyException: When both binding modes are supplied, no
            binding is given, or ``option_value``/``name`` are missing.

    """
    props = context.props or {}
    bind = resolve_bind_target(props, "Radio")
    if bind.target is None:
        raise WebComPyException("Radio requires a 'field' or a shared group 'value' Signal")
    option_value = props.get("option_value", "")
    name = props.get("name", "")
    if not option_value or not name:
        raise WebComPyException("Radio requires static 'option_value' and 'name' props")

    ctx = form_field_context()
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.signal is None:
        raise WebComPyException("Radio 'on_change' requires a bound 'field' or 'value'")

    base: dict[str, Any] = {
        "type": "radio",
        "name": name,
        "value": option_value,
        **optional_text_attrs(props, ("disabled",)),
    }
    attrs = compose_attrs(
        base,
        framework_class=_RADIO_FRAMEWORK_CLASS,
        props=props,
        state=state,
        control_id=props.get("id", ""),
    )
    attrs[":bind"] = bind.target
    if on_change is not None:
        attrs["@change"] = lambda ev: on_change(bound_value(bind, option_value))
    return create_element("input", attrs)


class RadioGroupProps(TypedDict, total=False):
    """Props for the headless ``RadioGroup`` component."""

    field: Field[Any]
    value: Any
    on_change: Callable[[Any], None]
    options: Sequence[SelectOption]
    legend: str
    id: str
    aria_label: str
    disabled: bool
    required: bool
    class_name: str
    class_input: str
    class_label: str
    class_legend: str


@define_component(custom_element_name="headless-radio-group")
def RadioGroup(context: ComponentContext[RadioGroupProps]) -> Any:
    """Render a fieldset of same-name native radios from an options prop.

    The group binds the selected item's string value to either a
    forms-module ``Field`` (``field`` prop) or a raw value (``value``
    plus optional ``on_change``); supplying both is an error. One radio
    per option is rendered inside a native ``<label>``, all sharing a
    ``name`` generated from the instance's hydration-stable transfer id,
    so native arrow-key navigation moves selection within the group
    without custom keyboard code. The optional ``legend`` captions the
    group (the group self-labels; a surrounding ``FormField`` should omit
    its ``label`` for group controls). In the touched-invalid state the
    fieldset carries ``data-state="invalid"`` and ``aria-invalid``.

    Args:
        context: Component context with the radio group props.
            ``class_name`` targets the fieldset root, ``class_legend``
            the legend, ``class_input`` the radios, and ``class_label``
            the option labels.

    Returns:
        The rendered ``<fieldset>`` element.

    Raises:
        WebComPyException: When both binding modes are supplied or
            ``on_change`` is given without a bound value.

    """
    props = context.props or {}
    options = props.get("options") or []
    ctx = form_field_context()
    bind = resolve_bind_target(props, "RadioGroup")
    state = control_state(bind.field, ctx)
    on_change = props.get("on_change")
    if on_change is not None and bind.target is None:
        raise WebComPyException("RadioGroup 'on_change' requires a bound 'field' or 'value'")

    group_name = instance_dom_id("radio-group", context.transfer_id)

    fieldset_attrs = compose_attrs(
        {**optional_text_attrs(props, ("disabled",))},
        framework_class=_FIELDSET_CLASS,
        props=props,
        state=state,
        control_id="",
    )
    fieldset_attrs["class"] = join_classes(_FIELDSET_CLASS, _FRAMEWORK_CLASS, props.get("class_name", ""))

    children: list[Any] = []
    legend = props.get("legend", "")
    if legend:
        children.append(
            create_element("legend", {"class": join_classes(_LEGEND_CLASS, props.get("class_legend", ""))}, legend)
        )
    for option in options:
        option_value = option.get("value", "")
        input_attrs: dict[str, Any] = {
            "type": "radio",
            "name": group_name,
            "value": option_value,
            ":bind": bind.target,
            "class": join_classes(_INPUT_CLASS, props.get("class_input", "")),
        }
        if props.get("disabled"):
            input_attrs["disabled"] = True
        if on_change is not None:
            input_attrs["@change"] = lambda ev, ov=option_value: on_change(bound_value(bind, ov))
        input_el = create_element("input", input_attrs)
        item_label = option.get("label") or option_value
        children.append(
            create_element(
                "label",
                {"class": join_classes(_ITEM_CLASS, props.get("class_label", ""))},
                input_el,
                item_label,
            )
        )
    return create_element("fieldset", fieldset_attrs, *children)
