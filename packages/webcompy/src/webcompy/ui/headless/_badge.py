"""Headless Badge component rendering a compact status label."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element

BadgeVariant = Literal["neutral", "info", "success", "warning", "error"]

_VARIANTS = ("neutral", "info", "success", "warning", "error")


class BadgeProps(TypedDict, total=False):
    """Props accepted by the headless ``Badge`` component."""

    variant: str
    class_name: str


_FRAMEWORK_CLASS = "webcompy-headless-badge"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-badge")
def Badge(context: ComponentContext[BadgeProps]) -> Any:
    """Render a compact status label.

    The ``data-variant`` attribute carries the variant for styling hooks
    (unknown values fall back to ``neutral``). The badge is a static
    label: it carries no interaction state and emits no visual styling.

    Args:
        context: Component context carrying the ``variant`` and
            ``class_name`` props. The ``default`` slot supplies the
            label content.

    Returns:
        The rendered headless badge element.

    """
    props = context.props or {}
    variant = props.get("variant", "neutral")
    if variant not in _VARIANTS:
        variant = "neutral"
    attrs: dict[str, Any] = {
        "data-variant": variant,
        "class": _compose_class(_FRAMEWORK_CLASS, props.get("class_name", "")),
    }
    children: list[Any] = []
    content = context.slots("default", fallback=lambda: None)
    if content is not None:
        if isinstance(content, list):
            children.extend(content)
        else:
            children.append(content)
    return create_element("span", attrs, *children)


Badge.scoped_style = {}
