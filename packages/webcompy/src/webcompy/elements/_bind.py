from __future__ import annotations

from contextlib import suppress
from inspect import iscoroutinefunction
from typing import Any, cast

from webcompy.elements._dom_objs import DOMEvent
from webcompy.elements.typealias._element_property import AttrValue, ElementChildren, EventHandler
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, Signal, SignalBase

_TEXT_TYPES = {"text", "email", "password", "search", "tel", "url"}
_SUPPORTED_ELEMENTS = "input[type=text|email|password|search|tel|url|number|checkbox|radio] and textarea"


def is_bind_target(value: Any) -> bool:
    """Return True only for a plain writable Signal instance (not subclasses)."""
    return type(value) is Signal


def _chain_handlers(binding_handler: EventHandler, user_handler: EventHandler) -> EventHandler:
    if iscoroutinefunction(user_handler):

        async def chained_async(ev: DOMEvent) -> None:
            binding_handler(ev)
            await user_handler(ev)

        return chained_async

    def chained(ev: DOMEvent) -> None:
        binding_handler(ev)
        user_handler(ev)

    return chained


def _register_write_back(
    events: dict[str, EventHandler],
    event_name: str,
    handler: EventHandler,
) -> None:
    existing = events.get(event_name)
    if existing is None:
        events[event_name] = handler
    else:
        events[event_name] = _chain_handlers(handler, existing)


def _expand_text_bind(
    signal: Signal[Any],
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
) -> None:
    if not isinstance(signal.value, str):
        raise WebComPyException(
            f":bind on a text input or textarea requires a str-valued Signal (got {type(signal.value).__name__})"
        )
    if "value" in attrs:
        raise WebComPyException("':bind' conflicts with explicit 'value' attribute")
    attrs["value"] = signal

    def write_back(ev: DOMEvent) -> None:
        if (target := ev.target) is not None:
            signal.value = target.value

    _register_write_back(events, "input", write_back)


def _expand_textarea_bind(
    signal: Signal[Any],
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
    children: list[ElementChildren],
) -> None:
    if not isinstance(signal.value, str):
        raise WebComPyException(
            f":bind on a text input or textarea requires a str-valued Signal (got {type(signal.value).__name__})"
        )
    if "value" in attrs:
        raise WebComPyException("':bind' conflicts with explicit 'value' attribute")
    children.append(signal)

    def write_back(ev: DOMEvent) -> None:
        if (target := ev.target) is not None:
            signal.value = target.value

    _register_write_back(events, "input", write_back)


def _expand_number_bind(
    signal: Signal[Any],
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
) -> None:
    current = signal.value
    if not isinstance(current, (int, float)) or isinstance(current, bool):
        raise WebComPyException(
            f":bind on input[type=number] requires an int or float-valued Signal (got {type(current).__name__})"
        )
    if "value" in attrs:
        raise WebComPyException("':bind' conflicts with explicit 'value' attribute")
    attrs["value"] = signal

    def write_back(ev: DOMEvent) -> None:
        target = ev.target
        if target is None:
            return
        raw = target.value
        if raw == "":
            return
        current_value = signal.value
        with suppress(ValueError):
            signal.value = int(raw) if isinstance(current_value, int) else float(raw)

    _register_write_back(events, "input", write_back)


def _expand_checkbox_bind(
    signal: Signal[Any],
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
) -> None:
    if not isinstance(signal.value, bool):
        raise WebComPyException(
            f":bind on a checkbox requires a bool-valued Signal (got {type(signal.value).__name__})"
        )
    if "checked" in attrs:
        raise WebComPyException("':bind' conflicts with explicit 'checked' attribute")
    attrs["checked"] = signal

    def write_back(ev: DOMEvent) -> None:
        if (target := ev.target) is not None:
            signal.value = bool(target.checked)

    _register_write_back(events, "change", write_back)


def _expand_radio_bind(
    signal: Signal[Any],
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
) -> None:
    radio_value = attrs.get("value")
    if radio_value is None or isinstance(radio_value, SignalBase):
        raise WebComPyException("radio :bind requires a static value attribute")
    if "checked" in attrs:
        raise WebComPyException("':bind' conflicts with explicit 'checked' attribute")
    attrs["checked"] = Computed(lambda: signal.value == radio_value)

    def write_back(ev: DOMEvent) -> None:
        if (target := ev.target) is not None and target.checked:
            signal.value = radio_value

    _register_write_back(events, "change", write_back)


def expand_bind_attr(
    tag_name: str,
    attrs: dict[str, AttrValue],
    events: dict[str, EventHandler],
    children: list[ElementChildren] | None = None,
) -> None:
    """Pop ':bind' from attrs and expand it into a bound attr + write-back handler.

    Raises WebComPyException for: unsupported tag, non-Signal value, read-only
    signal kind, type-discipline violation, bound-attr conflict, dynamic type attr.
    """
    bind_value = attrs.pop(":bind")
    if not is_bind_target(bind_value):
        raise WebComPyException(f":bind requires a writable Signal (got {type(bind_value).__name__})")
    signal = cast("Signal[Any]", bind_value)

    type_attr = attrs.get("type")
    if isinstance(type_attr, SignalBase):
        raise WebComPyException(":bind requires a static 'type' attribute")
    input_type = type_attr if isinstance(type_attr, str) else None

    if tag_name == "textarea":
        if children is None:
            raise WebComPyException("textarea :bind requires the element children list")
        _expand_textarea_bind(signal, attrs, events, children)
    elif tag_name == "input" and (input_type is None or input_type in _TEXT_TYPES):
        _expand_text_bind(signal, attrs, events)
    elif tag_name == "input" and input_type == "number":
        _expand_number_bind(signal, attrs, events)
    elif tag_name == "input" and input_type == "checkbox":
        _expand_checkbox_bind(signal, attrs, events)
    elif tag_name == "input" and input_type == "radio":
        _expand_radio_bind(signal, attrs, events)
    else:
        raise WebComPyException(f":bind is not supported on <{tag_name}> (supported: {_SUPPORTED_ELEMENTS})")
