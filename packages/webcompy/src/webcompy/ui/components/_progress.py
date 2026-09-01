"""Themed Progress component composing the headless Progress with token styling."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._progress import Progress as HeadlessProgress
from webcompy.ui.headless._progress import ProgressProps as HeadlessProgressProps


class ThemedProgressProps(TypedDict, total=False):
    """Props accepted by the themed ``Progress`` component."""

    value: float
    min: float
    max: float
    indeterminate: bool
    aria_label: str
    class_name: str
    class_fill: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-progress")
def Progress(context: ComponentContext[ThemedProgressProps]) -> Any:
    """Render a themed progress bar.

    Composes the headless ``Progress`` with the default ``webcompy-progress``
    track and ``webcompy-progress-fill`` classes whose rules live in the
    shipped primitives stylesheet; the indeterminate mode animates an
    internal sweep and honors reduced motion. ARIA semantics and the
    reactive value binding come from the headless component, whose
    ``value``, ``min``, ``max``, and ``indeterminate`` props accept
    signal-like objects as well as plain values.

    Args:
        context: Component context carrying the ``value``, ``min``,
            ``max``, ``indeterminate``, ``aria_label``, and class
            pass-through props.

    Returns:
        The rendered themed progress element.

    """
    props = context.props or {}
    headless_props: HeadlessProgressProps = {
        "value": props.get("value", 0),  # type: ignore[typeddict-item]
        "min": props.get("min", 0),  # type: ignore[typeddict-item]
        "max": props.get("max", 100),  # type: ignore[typeddict-item]
        "indeterminate": props.get("indeterminate", False),  # type: ignore[typeddict-item]
        "aria_label": props.get("aria_label", ""),
        "class_name": _compose_class("webcompy-progress", props.get("class_name", "")),
        "class_fill": _compose_class("webcompy-progress-fill", props.get("class_fill", "")),
    }
    return HeadlessProgress(headless_props)
