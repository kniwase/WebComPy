from __future__ import annotations

from operator import truth
from typing import Any, cast

from webcompy.elements.generators import repeat
from webcompy.elements.typealias._element_property import (
    AttrValue,
    ElementChildren,
    EventHandler,
)
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, SignalBase
from webcompy.template._ast import (
    AttrSpec,
    ForNode,
    IfNode,
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


def _to_element(child: ElementChildren) -> ElementAbstract:
    if isinstance(child, ElementAbstract):
        return child
    if isinstance(child, str):
        return TextElement(child)
    if isinstance(child, SignalBase):
        return TextElement(child)
    raise WebComPyException(f"Cannot convert {type(child).__name__} to ElementAbstract")


def _wrap_for_fragment(children: list[ElementChildren]) -> ElementChildren:
    """Wrap a list of ElementChildren into a single ElementChildren for switch/repeat callbacks.

    * 0 children → None
    * 1 child    → pass-through
    * multiple   → FragmentElement wrapping all as ElementAbstract
    """
    filtered = [c for c in children if c is not None]
    if not filtered:
        return None
    if len(filtered) == 1:
        return filtered[0]
    return FragmentElement([_to_element(c) for c in filtered])


def _make_branch_generator(body: list[TemplateNode], ctx: dict[str, Any]):
    def gen() -> ElementChildren:
        return _wrap_for_fragment(bind_children(body, ctx))

    return gen


def bind_if(node: IfNode, ctx: dict[str, Any]) -> list[ElementChildren]:
    branch_data: list[tuple[bool, Any, list[TemplateNode]]] = []
    has_signal = False
    for cond_str, body in node.branches:
        if cond_str is None:
            branch_data.append((True, None, body))
        else:
            resolved = resolve_var(cond_str, ctx)
            if isinstance(resolved, SignalBase):
                has_signal = True
            branch_data.append((False, resolved, body))

    if has_signal:
        cases: list[tuple[Any, Any]] = []
        default = None
        for is_else, cond, body in branch_data:
            if is_else:
                default = _make_branch_generator(body, ctx)
            else:
                cases.append((cond, _make_branch_generator(body, ctx)))
        return [SwitchElement(cases, default)]

    for is_else, cond, body in branch_data:
        if is_else or truth(cond):
            return bind_children(body, ctx)
    return []


def _extend_for_ctx(
    ctx: dict[str, Any],
    loop_vars: list[str],
    value: Any,
    key: Any,
    is_dict: bool,
) -> dict[str, Any]:
    new_ctx = dict(ctx)
    if len(loop_vars) == 1:
        new_ctx[loop_vars[0]] = value
    elif len(loop_vars) == 2 and is_dict:
        new_ctx[loop_vars[0]] = key
        new_ctx[loop_vars[1]] = value
    else:
        raise WebComPyException(f"Invalid for-loop variable count: expected 1 or 2, got {len(loop_vars)}")
    return new_ctx


def bind_for(node: ForNode, ctx: dict[str, Any]) -> list[ElementChildren]:
    loop_vars = node.loop_vars
    iterable_resolved = resolve_var(node.iterable_path, ctx)

    if isinstance(iterable_resolved, SignalBase):
        return [_bind_for_reactive(loop_vars, iterable_resolved, node.body, ctx)]

    is_dict = isinstance(iterable_resolved, dict)
    result: list[ElementChildren] = []

    if len(loop_vars) == 1:
        items: list[Any] = list(iterable_resolved.values()) if is_dict else list(iterable_resolved)
        for value in items:
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, None, is_dict)
            result.extend(bind_children(node.body, new_ctx))
        return result

    if len(loop_vars) == 2:
        if not is_dict:
            raise WebComPyException(
                f"Two-variable for-loop requires a dict iterable (got {type(iterable_resolved).__name__})"
            )
        for key, value in iterable_resolved.items():
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, key, is_dict=True)
            result.extend(bind_children(node.body, new_ctx))
        return result

    raise WebComPyException(f"Invalid for-loop variable count: expected 1 or 2, got {len(loop_vars)}")


def _bind_for_reactive(
    loop_vars: list[str],
    signal: SignalBase,
    body: list[TemplateNode],
    ctx: dict[str, Any],
) -> ElementChildren:
    is_dict = isinstance(signal.value, dict)

    if len(loop_vars) == 1:

        def single_arg_cb(value: Any) -> ElementChildren:
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, None, is_dict)
            return _wrap_for_fragment(bind_children(body, new_ctx))

        return repeat(signal, single_arg_cb)

    if len(loop_vars) == 2:
        if not is_dict:
            raise WebComPyException("Two-variable for-loop over a reactive non-dict iterable is not supported")

        def two_arg_cb(value: Any, key: Any) -> ElementChildren:
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, key, is_dict=True)
            return _wrap_for_fragment(bind_children(body, new_ctx))

        return repeat(signal, two_arg_cb)

    raise WebComPyException(f"Invalid for-loop variable count: expected 1 or 2, got {len(loop_vars)}")


def bind_children(nodes: list[TemplateNode], ctx: dict[str, Any]) -> list[ElementChildren]:
    result: list[ElementChildren] = []
    for node in nodes:
        if isinstance(node, TemplateText):
            result.extend(bind_text_part(node, ctx))
        elif isinstance(node, TemplateElement):
            result.append(bind_element(node, ctx))
        elif isinstance(node, IfNode):
            result.extend(bind_if(node, ctx))
        elif isinstance(node, ForNode):
            result.extend(bind_for(node, ctx))
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
