from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._element import Element
from webcompy.exception import WebComPyException
from webcompy.template._ast import (
    AttrSpec,
    TemplateElement,
    TemplateNode,
    TemplateText,
)
from webcompy.template._binder import bind_children
from webcompy.template._cache import get_or_compile
from webcompy.template._holes import (
    HOLE_PATTERN,
    Hole,
    LiteralText,
    format_value,
    resolve_holes,
    resolve_var,
    split_text,
)


def _render_nodes(source: str, context: Mapping[str, Any] | None = None) -> list[ElementChildren]:
    ctx: dict[str, Any] = dict(context) if context else {}
    roots = get_or_compile(source)
    return bind_children(roots, ctx)


def render_template(source: str, context: Mapping[str, Any] | None = None) -> Element:
    nodes = _render_nodes(source, context)
    if len(nodes) == 1 and isinstance(nodes[0], Element):
        return nodes[0]
    raise WebComPyException("Template must have exactly one root element")


__all__ = [
    "HOLE_PATTERN",
    "AttrSpec",
    "Hole",
    "LiteralText",
    "TemplateElement",
    "TemplateNode",
    "TemplateText",
    "format_value",
    "render_template",
    "resolve_holes",
    "resolve_var",
    "split_text",
]
