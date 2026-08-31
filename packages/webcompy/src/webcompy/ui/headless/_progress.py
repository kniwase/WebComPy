"""Headless Progress component exposing determinate and indeterminate states."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element
from webcompy.signal import use_computed
from webcompy.signal._base import SignalBase


class ProgressProps(TypedDict, total=False):
    """Props accepted by the headless ``Progress`` component.

    ``value`` and ``indeterminate`` may be plain values or signal-like
    objects for reactive updates.
    """

    value: float
    min: float
    max: float
    indeterminate: bool
    aria_label: str
    class_name: str
    class_fill: str


_FRAMEWORK_CLASS = "webcompy-headless-progress"
_FILL_CLASS = "webcompy-headless-progress-fill"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def _read(raw: Any, default: Any) -> Any:
    if isinstance(raw, SignalBase):
        value = raw.value
        return default if value is None else value
    return default if raw is None else raw


def _fmt(number: float) -> str:
    return str(int(number)) if number.is_integer() else str(number)


@define_component(custom_element_name="headless-progress")
def Progress(context: ComponentContext[ProgressProps]) -> Any:
    """Render a progressbar with determinate or indeterminate semantics.

    The root carries ``role="progressbar"`` with ``aria-valuemin`` and
    ``aria-valuemax`` from the bounds props. In determinate mode it sets
    ``aria-valuenow`` from the clamped value and exposes
    ``data-state="determinate"``; in indeterminate mode ``aria-valuenow``
    is omitted (an ARIA progressbar without a current value is
    indeterminate) and ``data-state="indeterminate"`` is exposed. Supply
    ``aria_label`` for the accessible name; without it the progressbar
    renders unnamed. A fill element is provided for the determinate bar;
    its ``width`` style tracks the clamped percentage (indeterminate
    visuals belong to the themed layer). No other visual styling is
    emitted.

    Args:
        context: Component context carrying the ``value``, ``min``,
            ``max``, ``indeterminate``, ``aria_label``, and class
            pass-through props.

    Returns:
        The rendered headless progress element.

    """
    props = context.props or {}
    value_raw = props.get("value")
    indeterminate_raw = props.get("indeterminate", False)
    lower = float(_read(props.get("min"), 0))
    upper = float(_read(props.get("max"), 100))

    def _indeterminate() -> bool:
        return bool(_read(indeterminate_raw, False))

    def _percent() -> float:
        raw = float(_read(value_raw, 0))
        span = upper - lower if upper > lower else 1.0
        return max(0.0, min(1.0, (raw - lower) / span)) * 100.0

    def _value_now() -> Any:
        if _indeterminate():
            return False
        return _fmt(float(_read(value_raw, 0)))

    state_computed = use_computed(lambda: "indeterminate" if _indeterminate() else "determinate")

    attrs: dict[str, Any] = {
        "role": "progressbar",
        "aria-valuemin": _fmt(lower),
        "aria-valuemax": _fmt(upper),
        "aria-valuenow": use_computed(_value_now),
        "data-state": state_computed,
        "class": _compose_class(_FRAMEWORK_CLASS, props.get("class_name", "")),
    }
    aria_label = props.get("aria_label", "")
    if aria_label:
        attrs["aria-label"] = aria_label

    fill_attrs: dict[str, Any] = {
        "class": _compose_class(_FILL_CLASS, props.get("class_fill", "")),
        "aria-hidden": "true",
        "style": use_computed(lambda: False if _indeterminate() else f"width: {_percent():.4f}%"),
    }

    return create_element("div", attrs, create_element("div", fill_attrs))


Progress.scoped_style = {}
