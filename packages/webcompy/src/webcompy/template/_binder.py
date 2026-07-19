from __future__ import annotations

from typing import Any, cast

from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
    EventHandler,
)
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import NewLine
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, SignalBase
from webcompy.template._ast import (
    AttrSpec,
    TemplateElement,
    TemplateNode,
    TemplateText,
)
from webcompy.template._holes import (
    Hole,
    LiteralText,
    format_value,
    resolve_var,
)


def _attr_text(parts: list[LiteralText | Hole]) -> str:
    return "".join(part.text for part in parts if isinstance(part, LiteralText))


def classify_attrs(attrs: list[AttrSpec], ctx: dict[str, Any]) -> tuple[dict[str, EventHandler], Any, list[AttrSpec]]:
    events: dict[str, EventHandler] = {}
    ref: Any = None
    regular: list[AttrSpec] = []
    for attr in attrs:
        if attr.name.startswith("@"):
            if any(isinstance(p, Hole) for p in attr.value):
                raise WebComPyException(f"{{{{ }}}} interpolation is not supported in @event attributes: {attr.name}")
            event_name = attr.name[1:]
            raw_value = _attr_text(attr.value)
            handler = resolve_var(raw_value, ctx)
            if not callable(handler):
                raise WebComPyException(
                    f"Event handler '{raw_value}' for {attr.name} is not callable (got {type(handler).__name__})"
                )
            events[event_name] = handler
        elif attr.name.startswith(":"):
            if any(isinstance(p, Hole) for p in attr.value):
                raise WebComPyException(f"{{{{ }}}} interpolation is not supported in :ref attributes: {attr.name}")
            raw_value = _attr_text(attr.value)
            ref = resolve_var(raw_value, ctx)
        else:
            regular.append(attr)
    return events, ref, regular


def resolve_attr(parts: list[LiteralText | Hole], ctx: dict[str, Any]) -> AttrValue:
    resolved_vars: list[Any] = []
    has_signal = False
    for part in parts:
        if isinstance(part, Hole):
            value = resolve_var(part.var_path, ctx)
            resolved_vars.append(value)
            if isinstance(value, SignalBase):
                has_signal = True
        else:
            resolved_vars.append(None)

    def _render_parts() -> str:
        out: list[str] = []
        for idx, part in enumerate(parts):
            if isinstance(part, LiteralText):
                out.append(part.text)
            else:
                out.append(format_value(resolved_vars[idx]))
        return "".join(out)

    if not has_signal:
        return _render_parts()
    return Computed(_render_parts)


def bind_text_part(node: TemplateText, ctx: dict[str, Any]) -> list[ElementChildren]:
    result: list[ElementChildren] = []
    for part in node.parts:
        if isinstance(part, LiteralText):
            result.append(part.text)
            continue
        value = resolve_var(part.var_path, ctx)
        if value is None:
            continue
        if isinstance(value, (str, SignalBase, ElementAbstract)):
            result.append(value)
        else:
            result.append(str(value))
    return result


def bind_children(nodes: list[TemplateNode], ctx: dict[str, Any]) -> list[ElementChildren]:
    result: list[ElementChildren] = []
    for node in nodes:
        if isinstance(node, TemplateText):
            result.extend(bind_text_part(node, ctx))
        elif isinstance(node, TemplateElement):
            result.append(bind_element(node, ctx))
    return result


def bind_element(node: TemplateElement, ctx: dict[str, Any]) -> ElementChildren:
    if node.tag_name == "br":
        return NewLine()
    events, ref, regular_attrs = classify_attrs(node.attrs, ctx)
    resolved_attrs: dict[str, AttrValue] = {}
    for attr in regular_attrs:
        if attr.is_boolean:
            resolved_attrs[attr.name] = True
        else:
            resolved_attrs[attr.name] = resolve_attr(attr.value, ctx)
    children = bind_children(node.children, ctx)
    return Element(
        tag_name=cast("HtmlTags", node.tag_name),
        attrs=resolved_attrs,
        events=events,
        ref=ref,
        children=children,
    )
