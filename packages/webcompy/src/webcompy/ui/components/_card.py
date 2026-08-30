"""Themed Card component composing the headless Card with token styling."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._card import Card as HeadlessCard
from webcompy.ui.headless._card import CardProps as HeadlessCardProps


class ThemedCardProps(TypedDict, total=False):
    """Props accepted by the themed ``Card`` component."""

    class_name: str
    class_header: str
    class_body: str
    class_footer: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-card")
def Card(context: ComponentContext[ThemedCardProps]) -> Any:
    """Render a themed structural card.

    Composes the headless ``Card`` with the default ``webcompy-card`` and
    region classes (header/body/footer) whose token-based rules live in
    the shipped primitives stylesheet. Region rendering and slot wiring
    come from the headless component; user classes are appended after the
    themed defaults so user rules win at equal specificity.

    Args:
        context: Component context carrying the region class pass-through
            props and the ``header`` / ``default`` / ``footer`` slots.

    Returns:
        The rendered themed card element.

    """
    props = context.props or {}
    headless_props: HeadlessCardProps = {
        "class_name": _compose_class("webcompy-card", props.get("class_name", "")),
        "class_header": _compose_class("webcompy-card-header", props.get("class_header", "")),
        "class_body": _compose_class("webcompy-card-body", props.get("class_body", "")),
        "class_footer": _compose_class("webcompy-card-footer", props.get("class_footer", "")),
    }
    slots: dict[str, Any] = {}
    for name in ("header", "default", "footer"):
        content = context.slots(name, fallback=lambda: None)
        if content is not None:
            slots[name] = lambda c=content: c
    return HeadlessCard(headless_props, slots=slots)  # type: ignore[call-arg, arg-type]
