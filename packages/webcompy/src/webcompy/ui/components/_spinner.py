"""Themed Spinner component composing the headless Spinner with token styling."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._spinner import Spinner as HeadlessSpinner
from webcompy.ui.headless._spinner import SpinnerProps, _compose_class

_SIZE_CLASSES: dict[str, str] = {
    "sm": "webcompy-spinner webcompy-spinner--sm",
    "md": "webcompy-spinner",
    "lg": "webcompy-spinner webcompy-spinner--lg",
}


class ThemedSpinnerProps(TypedDict, total=False):
    """Props accepted by the themed ``Spinner`` component."""

    label: str
    aria_label: str
    class_name: str
    size: Literal["sm", "md", "lg"]


@define_component(custom_element_name="webcompy-spinner")
def Spinner(context: ComponentContext[ThemedSpinnerProps]) -> Any:
    """Render a themed loading spinner with token-based animation.

    Composes the headless ``Spinner`` and supplies the default
    ``webcompy-spinner`` classes whose rules live in the shipped
    primitives stylesheet inside the ``components`` layer. The ``size``
    prop selects the ``sm``, ``md`` (default), or ``lg`` variant. The
    animation pauses under ``prefers-reduced-motion``. Behavior,
    accessibility, and the ``class_name`` pass-through are inherited
    from the headless component; user classes are appended after the
    themed defaults so user rules win at equal specificity.

    Args:
        context: Component context carrying the ``label``,
            ``aria_label``, ``class_name``, and ``size`` props.

    Returns:
        The rendered themed spinner element.

    """
    props = context.props or {}
    size = props.get("size", "md")
    if size not in _SIZE_CLASSES:
        size = "md"

    headless_props: SpinnerProps = {
        "class_name": _compose_class(_SIZE_CLASSES[size], props.get("class_name", "")),
        "label": props.get("label", ""),
        "aria_label": props.get("aria_label", ""),
    }
    return HeadlessSpinner(headless_props)
