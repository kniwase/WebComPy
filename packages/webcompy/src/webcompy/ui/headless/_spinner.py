"""Headless Spinner component providing an accessible loading status region."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element


class SpinnerProps(TypedDict, total=False):
    """Props accepted by the headless ``Spinner`` component."""

    label: str
    aria_label: str
    class_name: str


_FRAMEWORK_CLASS = "webcompy-headless-spinner"
_SR_ONLY_CLASS = "webcompy-sr-only"
_STATE = "loading"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-spinner")
def Spinner(context: ComponentContext[SpinnerProps]) -> Any:
    """Render an accessible loading status region without visual styling.

    The root element carries ``role="status"``, ``data-state="loading"``,
    and the framework class followed by the user ``class_name`` classes.
    The accessible name comes from ``label`` rendered as visually hidden
    text; when ``label`` is empty, ``aria_label`` is applied as the
    ``aria-label`` attribute instead. Supplying neither leaves the status
    region unnamed. No colors, spacing, typography, or animation are
    emitted; style the component through ``class_name`` and the
    ``data-state`` attribute.

    Args:
        context: Component context carrying the ``label``, ``aria_label``,
            and ``class_name`` props.

    Returns:
        The rendered headless spinner element.

    """
    props = context.props or {}
    label = props.get("label", "")
    aria_label = props.get("aria_label", "")

    attrs: dict[str, Any] = {
        "role": "status",
        "data-state": _STATE,
        "class": _compose_class(_FRAMEWORK_CLASS, props.get("class_name", "")),
    }

    children: list[Any] = []
    if label:
        children.append(create_element("span", {"class": _SR_ONLY_CLASS}, label))
    elif aria_label:
        attrs["aria-label"] = aria_label

    return create_element("div", attrs, *children)


Spinner.scoped_style = {
    f".{_SR_ONLY_CLASS}": {
        "position": "absolute",
        "width": "1px",
        "height": "1px",
        "padding": "0",
        "margin": "-1px",
        "overflow": "hidden",
        "clip": "rect(0, 0, 0, 0)",
        "white-space": "nowrap",
        "border": "0",
    },
}
