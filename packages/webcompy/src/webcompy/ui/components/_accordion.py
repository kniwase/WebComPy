"""Themed Accordion component composing themed Collapse items."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._accordion import Accordion as HeadlessAccordion
from webcompy.ui.headless._accordion import AccordionItem
from webcompy.ui.headless._accordion import AccordionProps as HeadlessAccordionProps


class ThemedAccordionProps(TypedDict, total=False):
    """Props accepted by the themed ``Accordion`` component."""

    items: list[AccordionItem]
    single_open: bool
    on_toggle: Callable[[str, bool], None]
    class_name: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-accordion")
def Accordion(context: ComponentContext[ThemedAccordionProps]) -> Any:
    """Render a themed accordion.

    Composes the headless ``Accordion`` and forwards the themed Collapse
    class hooks and default transition class set to every item, so items
    share the collapse visuals (bordered sections, animated natural-height
    expansion). Behavior, the open policy, and accessibility come from
    the headless component; user classes are appended after the themed
    defaults.

    Args:
        context: Component context carrying the ``items``, ``single_open``,
            ``on_toggle``, and ``class_name`` props.

    Returns:
        The rendered themed accordion element.

    """
    props = context.props or {}
    headless_props: HeadlessAccordionProps = {
        "items": props.get("items", []),  # type: ignore[typeddict-item]
        "single_open": bool(props.get("single_open", False)),
        "on_toggle": props.get("on_toggle"),  # type: ignore[typeddict-item]
        "transition_name": "webcompy-collapse",
        "class_name": _compose_class("webcompy-accordion", props.get("class_name", "")),
        "class_trigger": "webcompy-collapse-trigger",
        "class_content": "webcompy-collapse-content",
    }
    return HeadlessAccordion(headless_props)
