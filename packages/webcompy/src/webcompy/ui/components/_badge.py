"""Themed Badge component composing the headless Badge with token styling."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._badge import _VARIANTS
from webcompy.ui.headless._badge import Badge as HeadlessBadge
from webcompy.ui.headless._badge import BadgeProps as HeadlessBadgeProps


class ThemedBadgeProps(TypedDict, total=False):
    """Props accepted by the themed ``Badge`` component."""

    variant: str
    class_name: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-badge")
def Badge(context: ComponentContext[ThemedBadgeProps]) -> Any:
    """Render a themed status badge.

    Composes the headless ``Badge`` with the default ``webcompy-badge``
    class plus a ``webcompy-badge--{variant}`` modifier consuming design
    tokens. User classes are appended after the themed defaults.

    Args:
        context: Component context carrying the ``variant`` and
            ``class_name`` props, plus the label in the ``default`` slot.

    Returns:
        The rendered themed badge element.

    """
    props = context.props or {}
    variant = props.get("variant", "neutral")
    if variant not in _VARIANTS:
        variant = "neutral"
    headless_props: HeadlessBadgeProps = {
        "variant": variant,
        "class_name": _compose_class(f"webcompy-badge webcompy-badge--{variant}", props.get("class_name", "")),
    }
    content = context.slots("default", fallback=lambda: None)
    slots: dict[str, Any] = {}
    if content is not None:
        slots["default"] = lambda: content
    return HeadlessBadge(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
