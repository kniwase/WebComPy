"""Themed Skeleton component composing the headless Skeleton with token styling."""

from __future__ import annotations

from typing import Any, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless._skeleton import Skeleton as HeadlessSkeleton
from webcompy.ui.headless._skeleton import SkeletonProps as HeadlessSkeletonProps


class ThemedSkeletonProps(TypedDict, total=False):
    """Props accepted by the themed ``Skeleton`` component."""

    shape: str
    width: str
    height: str
    class_name: str


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="webcompy-skeleton")
def Skeleton(context: ComponentContext[ThemedSkeletonProps]) -> Any:
    """Render a themed loading placeholder.

    Composes the headless ``Skeleton`` with the default ``webcompy-skeleton``
    class plus a ``webcompy-skeleton--{shape}`` modifier. The themed layer
    supplies a shimmer animation that is suppressed under reduced motion.
    The ``aria-hidden`` decoration marking comes from the headless
    component; pair skeletons with an accessible loading indicator in the
    surrounding container.

    Args:
        context: Component context carrying the ``shape``, ``width``,
            ``height``, and ``class_name`` props.

    Returns:
        The rendered themed skeleton element.

    """
    props = context.props or {}
    shape = props.get("shape", "rectangle")
    if shape not in ("rectangle", "line", "circle"):
        shape = "rectangle"
    headless_props: HeadlessSkeletonProps = {
        "shape": shape,
        "width": props.get("width", ""),
        "height": props.get("height", ""),
        "class_name": _compose_class(f"webcompy-skeleton webcompy-skeleton--{shape}", props.get("class_name", "")),
    }
    return HeadlessSkeleton(headless_props)
