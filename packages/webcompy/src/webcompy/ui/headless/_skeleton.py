"""Headless Skeleton component rendering decorative loading placeholders."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.elements import create_element

SkeletonShape = Literal["rectangle", "line", "circle"]

_SHAPES = ("rectangle", "line", "circle")


class SkeletonProps(TypedDict, total=False):
    """Props accepted by the headless ``Skeleton`` component."""

    shape: str
    width: str
    height: str
    class_name: str


_FRAMEWORK_CLASS = "webcompy-headless-skeleton"


def _compose_class(*parts: str) -> str:
    return " ".join(part for part in parts if part)


@define_component(custom_element_name="headless-skeleton")
def Skeleton(context: ComponentContext[SkeletonProps]) -> Any:
    """Render a decorative loading placeholder.

    The placeholder is marked ``aria-hidden="true"``: skeletons are
    visual decoration and must not reach assistive technology. The
    surrounding container must carry the accessible loading indication
    (e.g. a ``Spinner`` with ``role="status"`` or visible loading text).
    ``shape`` selects the geometry hook (``data-shape``: rectangle, line,
    or circle; unknown values fall back to rectangle); optional ``width``
    and ``height`` strings are applied as inline styles. The shimmer
    animation belongs to the themed layer.

    Args:
        context: Component context carrying the ``shape``, ``width``,
            ``height``, and ``class_name`` props.

    Returns:
        The rendered headless skeleton element.

    """
    props = context.props or {}
    shape = props.get("shape", "rectangle")
    if shape not in _SHAPES:
        shape = "rectangle"
    attrs: dict[str, Any] = {
        "aria-hidden": "true",
        "data-shape": shape,
        "class": _compose_class(_FRAMEWORK_CLASS, props.get("class_name", "")),
    }
    width = props.get("width", "")
    height = props.get("height", "")
    style = "; ".join(
        part for part in ((f"width: {width}" if width else ""), (f"height: {height}" if height else "")) if part
    )
    if style:
        attrs["style"] = style
    return create_element("div", attrs)


Skeleton.scoped_style = {}
