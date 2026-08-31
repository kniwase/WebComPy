"""Headless Card component providing a structural container with regions."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element


class CardProps(TypedDict, total=False):
    """Props accepted by the headless ``Card`` component."""

    class_name: str
    class_header: str
    class_body: str
    class_footer: str


_FRAMEWORK_CLASS = "webcompy-headless-card"
_HEADER_CLASS = "webcompy-headless-card-header"
_BODY_CLASS = "webcompy-headless-card-body"
_FOOTER_CLASS = "webcompy-headless-card-footer"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-card")
def Card(context: ComponentContext[CardProps]) -> Any:
    """Render a structural container with header, body, and footer regions.

    Card is behavior-free: it only wires named regions through so layout
    containers share class hooks instead of each application re-deriving
    them. A region element is rendered only when its slot is supplied
    (``header``, ``default`` for the body, ``footer``). Part class props
    style individual regions; ``class_name`` targets the root. No visual
    styling is emitted.

    Args:
        context: Component context carrying the region class pass-through
            props and the ``header`` / ``default`` / ``footer`` slots.

    Returns:
        The rendered headless card element.

    """
    props = context.props or {}
    children: list[Any] = []

    header = context.slots("header", fallback=lambda: None)
    if header is not None:
        header_inner = header if isinstance(header, list) else [header]
        children.append(
            create_element(
                "div",
                {"class": _compose_class(_HEADER_CLASS, props.get("class_header", ""))},
                *header_inner,
            )
        )

    body = context.slots("default", fallback=lambda: None)
    if body is not None:
        body_inner = body if isinstance(body, list) else [body]
        children.append(
            create_element("div", {"class": _compose_class(_BODY_CLASS, props.get("class_body", ""))}, *body_inner)
        )

    footer = context.slots("footer", fallback=lambda: None)
    if footer is not None:
        footer_inner = footer if isinstance(footer, list) else [footer]
        children.append(
            create_element(
                "div",
                {"class": _compose_class(_FOOTER_CLASS, props.get("class_footer", ""))},
                *footer_inner,
            )
        )

    return create_element("div", {"class": _compose_class(_FRAMEWORK_CLASS, props.get("class_name", ""))}, *children)


Card.scoped_style = {}
