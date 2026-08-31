"""Shared binding-resolution and state-attribute helpers for headless form controls."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

from webcompy.components import ComponentContext
from webcompy.di import inject
from webcompy.di._scope import _active_di_scope
from webcompy.exception import WebComPyException
from webcompy.forms._field import Field
from webcompy.signal import Computed, Signal, SignalBase, use_computed, use_state
from webcompy.ui.headless._form_field_context import FORM_FIELD_CONTEXT_KEY, FormFieldContext


@dataclass(frozen=True)
class BindSpec:
    """Resolved binding target for one control instance.

    Attributes:
        target: The value passed to ``:bind`` (a ``Field`` or a plain
            ``Signal``), or ``None`` when the control is unbound.
        field: The ``Field`` when bound in field mode, else ``None``.
        signal: The signal carrying the control value (``field.value``
            in field mode), or ``None`` when unbound.

    """

    target: Field[Any] | Signal[Any] | None
    field: Field[Any] | None
    signal: Signal[Any] | None


def resolve_bind_target(props: Mapping[str, Any], control: str) -> BindSpec:
    """Resolve the ``field`` / ``value`` binding modes for a control.

    A ``field`` prop selects field mode; a ``value`` prop (plain value or
    a ``Signal``) selects raw mode, seeding a component-scoped signal for
    plain values. A plain ``value`` is only the initial seed: later
    external changes to it are not observed, so live two-way
    synchronization requires passing a ``Signal``. Supplying both modes
    raises; supplying neither yields an unbound control.

    Args:
        props: The control's component props.
        control: Control display name used in error messages.

    Returns:
        The resolved :class:`BindSpec`.

    Raises:
        WebComPyException: When both ``field`` and ``value`` are given.

    """
    field = props.get("field")
    value = props.get("value")
    if field is not None and value is not None:
        raise WebComPyException(f"{control} accepts either 'field' or 'value'/'on_change', not both")
    if field is not None:
        return BindSpec(field, field, field.value)
    if value is None:
        return BindSpec(None, None, None)
    if isinstance(value, SignalBase):
        signal = cast("Signal[Any]", value)
        return BindSpec(signal, None, signal)
    signal = use_state(lambda: value)
    return BindSpec(signal, None, signal)


def form_field_context() -> FormFieldContext | None:
    """Return the surrounding ``FormFieldContext`` when one is provided.

    Returns:
        The injected context, or ``None`` outside a ``FormField``'s slot
        subtree (or when no active DI scope is present).

    """
    return inject(FORM_FIELD_CONTEXT_KEY, default=None)


@contextmanager
def providing_form_field_context(context: ComponentContext[Any], ctx: FormFieldContext) -> Iterator[None]:
    """Provide a ``FormFieldContext`` for the duration of the provider's render pass.

    Registers ``ctx`` in the provider's component-scoped DI context and
    keeps the association visible only to controls constructed while the
    wrapped body runs (slot content evaluates eagerly inside it). The
    previously active scope is restored on exit so controls rendered
    afterwards as siblings of the provider never resolve this context.

    Args:
        context: The provider component's context, used to register the
            value in the component-scoped DI context.
        ctx: The association context to expose to slotted controls.

    Yields:
        None; the active DI scope is confined to the ``with`` block.

    """
    previous = _active_di_scope.get(None)
    context.provide(FORM_FIELD_CONTEXT_KEY, ctx)
    try:
        yield
    finally:
        _active_di_scope.set(previous)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ControlState:
    """Reactive state attributes shared by all bound form controls.

    Attributes:
        data_state: ``"invalid"`` while the field is touched and invalid,
            ``"valid"`` otherwise.
        aria_invalid: ``"true"`` in the gated-invalid state, ``False``
            (attribute removed) otherwise.
        aria_describedby: The FormField error id in the gated-invalid
            state when a context is present, ``False`` otherwise.

    """

    data_state: Computed[str]
    aria_invalid: Computed[Any]
    aria_describedby: Computed[Any]


def control_state(field: Field[Any] | None, ctx: FormFieldContext | None) -> ControlState:
    """Build the reactive state attributes for a control.

    Args:
        field: The bound ``Field``, or ``None`` for raw/unbound mode.
        ctx: The surrounding FormField context, or ``None``.

    Returns:
        Computeds for ``data-state``, ``aria-invalid``, and
        ``aria-describedby``.

    """
    gated = use_computed(lambda: field is not None and bool(field.touched.value and field.invalid.value))
    return ControlState(
        data_state=use_computed(lambda: "invalid" if gated.value else "valid"),
        aria_invalid=use_computed(lambda: "true" if gated.value else False),
        aria_describedby=use_computed(lambda: ctx.error_id if ctx is not None and gated.value else False),
    )


def bound_value(bind: BindSpec, fallback: Any = None) -> Any:
    """Read the current bound value after a write-back.

    Args:
        bind: The control's resolved binding.
        fallback: Value returned when the control is unbound.

    Returns:
        The signal's current value, or ``fallback`` when unbound.

    """
    if bind.signal is None:
        return fallback
    return bind.signal.value


def compose_attrs(
    base: dict[str, Any],
    *,
    framework_class: str,
    props: Mapping[str, Any],
    state: ControlState,
    control_id: str,
) -> dict[str, Any]:
    """Assemble the common attribute set for a native control element.

    Adds the framework class plus user ``class_name``, the reactive state
    attributes, the resolved ``id`` (when present), and the optional
    ``aria_label``.

    Args:
        base: Control-specific attributes applied first.
        framework_class: The headless framework class name.
        props: The component props.
        state: Reactive state computeds for the control.
        control_id: Resolved DOM id for the native element (empty when
            absent; the key is then omitted).

    Returns:
        The merged attribute mapping for ``create_element``.

    """
    parts = [framework_class]
    user_class = props.get("class_name", "")
    if user_class:
        parts.append(user_class)
    attrs: dict[str, Any] = dict(base)
    attrs["class"] = " ".join(parts)
    attrs["data-state"] = state.data_state
    attrs["aria-invalid"] = state.aria_invalid
    attrs["aria-describedby"] = state.aria_describedby
    if control_id:
        attrs["id"] = control_id
    aria_label = props.get("aria_label", "")
    if aria_label:
        attrs["aria-label"] = aria_label
    return attrs


def optional_text_attrs(props: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    """Collect non-empty string props into attribute entries.

    Args:
        props: The component props.
        keys: Prop names to copy verbatim when their value is truthy.

    Returns:
        Attribute mapping containing only the provided keys.

    """
    return {key: props[key] for key in keys if props.get(key)}


def compose_control_id(props: Mapping[str, Any], ctx: FormFieldContext | None) -> str:
    """Resolve the native element id from an explicit prop or context.

    Args:
        props: The component props (``id`` key).
        ctx: The surrounding FormField context, or ``None``.

    Returns:
        The explicit ``id`` prop when given, else the context control id,
        else an empty string.

    """
    explicit = props.get("id", "")
    if explicit:
        return explicit
    return ctx.control_id if ctx is not None else ""


def join_classes(*parts: str) -> str:
    """Join non-empty class names into a single attribute value.

    Args:
        *parts: Class name fragments; empty strings are dropped.

    Returns:
        The space-joined class attribute value.

    """
    return " ".join(part for part in parts if part)


def instance_dom_id(kind: str, transfer_id: str) -> str:
    """Derive a per-instance, hydration-stable DOM id string.

    The id comes from the component instance's hydration-stable transfer
    id so server-rendered and hydrated markup carry identical values; the
    ``#`` ordinal separator is replaced with ``-`` to stay usable in CSS
    selectors and attribute values.

    Args:
        kind: Element kind used as the id prefix (e.g. ``radio-group``).
        transfer_id: The component context's ``transfer_id``.

    Returns:
        The generated id string.

    """
    safe = transfer_id.replace("#", "-")
    return f"webcompy-{kind}-{safe}"
