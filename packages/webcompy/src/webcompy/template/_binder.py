from __future__ import annotations

from collections.abc import Callable, Iterable
from operator import truth
from typing import Any, cast

from webcompy.components._generator import ComponentStore
from webcompy.di import inject
from webcompy.di._keys import _COMPONENT_STORE_KEY
from webcompy.elements._bind import is_bind_target
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
from webcompy.elements.types._refference import DomNodeRef
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
from webcompy.template._expression import _EvalState, compile_expression, evaluate, resolve_scope
from webcompy.template._holes import (
    Hole,
    LiteralText,
    format_value,
    resolve_var,
    restore_protected,
)
from webcompy.template._naming import TagResolution, kebab_to_snake, resolve_tag

_EMPTY_COMPONENT_STORE = ComponentStore()


def _attr_text(parts: list[LiteralText | Hole]) -> str:
    return "".join(part.text for part in parts if isinstance(part, LiteralText))


def classify_attrs(
    attrs: list[AttrSpec], ctx: dict[str, Any]
) -> tuple[dict[str, EventHandler], Any, Any, list[AttrSpec]]:
    events: dict[str, EventHandler] = {}
    ref: Any = None
    bind: Any = None
    regular: list[AttrSpec] = []
    for attr in attrs:
        if attr.name.startswith("@"):
            if any(isinstance(p, Hole) for p in attr.value):
                raise WebComPyException(f"{{{{ }}}} interpolation is not supported in @event attributes: {attr.name}")
            event_name = attr.name[1:]
            if "." in event_name:
                raise WebComPyException(
                    f"Event modifiers are not supported in templates: '{attr.name}'. "
                    f"Use the plain event name '@{event_name.split('.')[0]}' and "
                    "handle the modifier logic inside the handler."
                )
            raw_value = _attr_text(attr.value)
            handler = resolve_var(raw_value, ctx)
            if not callable(handler):
                raise WebComPyException(
                    f"Event handler '{raw_value}' for {attr.name} is not callable (got {type(handler).__name__})"
                )
            events[event_name] = handler
        elif attr.name.startswith(":"):
            if attr.name not in (":ref", ":bind"):
                raise WebComPyException(
                    f"Unsupported attribute '{attr.name}' on HTML element: only ':ref' and ':bind' are allowed "
                    f"for ':'-prefixed attributes. Use {{{{ }}}} interpolation instead, "
                    f'e.g. {attr.name[1:]}="{{{{ ... }}}}".'
                )
            if any(isinstance(p, Hole) for p in attr.value):
                raise WebComPyException(
                    f"{{{{ }}}} interpolation is not supported in {attr.name} attributes: {attr.name}"
                )
            raw_value = _attr_text(attr.value)
            resolved = resolve_var(raw_value, ctx)
            if attr.name == ":ref":
                if not isinstance(resolved, DomNodeRef):
                    raise WebComPyException(
                        f":ref value '{raw_value}' must be a DomNodeRef instance (got {type(resolved).__name__})"
                    )
                ref = resolved
            else:
                if not is_bind_target(resolved):
                    raise WebComPyException(
                        f":bind value '{raw_value}' must be a writable Signal (got {type(resolved).__name__})"
                    )
                bind = resolved
        else:
            regular.append(attr)
    return events, ref, bind, regular


def resolve_attr(parts: list[LiteralText | Hole], ctx: dict[str, Any]) -> AttrValue:
    thunks: list[Callable[[], str]] = []
    has_signal = False
    for part in parts:
        if isinstance(part, LiteralText):
            text = restore_protected(part.text)
            thunks.append(lambda t=text: t)
        else:
            plan = part.plan
            if plan.is_plain_path:
                value = resolve_var(part.expr_source, ctx)
                if isinstance(value, SignalBase):
                    has_signal = True
                    thunks.append(lambda v=value: format_value(v))
                else:
                    thunks.append(lambda v=value: format_value(v))
            else:
                scope = resolve_scope(plan, ctx)
                state = _EvalState()
                value = evaluate(plan, scope, state)
                if state.saw_signal:
                    has_signal = True
                    thunks.append(lambda plan=plan, scope=scope: format_value(evaluate(plan, scope)))
                else:
                    thunks.append(lambda v=value: format_value(v))

    def _render_parts() -> str:
        return "".join(t() for t in thunks)

    if not has_signal:
        return _render_parts()
    return Computed(_render_parts)


def bind_text_part(node: TemplateText, ctx: dict[str, Any]) -> list[ElementChildren]:
    result: list[ElementChildren] = []
    for part in node.parts:
        if isinstance(part, LiteralText):
            result.append(restore_protected(part.text))
            continue
        plan = part.plan
        if plan.is_plain_path:
            value = resolve_var(part.expr_source, ctx)
            if value is None:
                continue
            if isinstance(value, (str, SignalBase, ElementAbstract)):
                result.append(value)
            else:
                result.append(str(value))
            continue
        scope = resolve_scope(plan, ctx)
        state = _EvalState()
        value = evaluate(plan, scope, state)
        if state.saw_signal:
            result.append(Computed(lambda plan=plan, scope=scope: evaluate(plan, scope)))
            continue
        if value is None:
            continue
        if isinstance(value, (str, ElementAbstract)):
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
            plan = compile_expression(cond_str)
            if plan.is_plain_path:
                resolved = resolve_var(cond_str, ctx)
                if isinstance(resolved, SignalBase):
                    has_signal = True
                branch_data.append((False, resolved, body))
            else:
                scope = resolve_scope(plan, ctx)
                state = _EvalState()
                value = evaluate(plan, scope, state)
                if state.saw_signal:
                    has_signal = True
                    branch_data.append((False, Computed(lambda plan=plan, scope=scope: evaluate(plan, scope)), body))
                else:
                    branch_data.append((False, value, body))

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


def _bind_for_static(
    iterable_resolved: Any,
    loop_vars: list[str],
    body: list[TemplateNode],
    ctx: dict[str, Any],
    iterable_path: str,
) -> list[ElementChildren]:
    is_dict = isinstance(iterable_resolved, dict)
    if not is_dict and not isinstance(iterable_resolved, Iterable):
        raise WebComPyException(
            f"Non-iterable {{% for %}} target: '{iterable_path}' resolved to {type(iterable_resolved).__name__}"
        )
    result: list[ElementChildren] = []
    if len(loop_vars) == 1:
        items: list[Any] = list(iterable_resolved.values()) if is_dict else list(iterable_resolved)
        for value in items:
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, None, is_dict)
            result.extend(bind_children(body, new_ctx))
        return result
    if len(loop_vars) == 2:
        if not is_dict:
            raise WebComPyException(
                f"Two-variable for-loop requires a dict iterable (got {type(iterable_resolved).__name__})"
            )
        for key, value in iterable_resolved.items():
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, key, is_dict=True)
            result.extend(bind_children(body, new_ctx))
        return result
    raise WebComPyException(f"Invalid for-loop variable count: expected 1 or 2, got {len(loop_vars)}")


def bind_for(node: ForNode, ctx: dict[str, Any]) -> list[ElementChildren]:
    loop_vars = node.loop_vars
    iterable_path = node.iterable_path
    plan = compile_expression(iterable_path)

    if plan.is_plain_path:
        iterable_resolved = resolve_var(iterable_path, ctx)
        if isinstance(iterable_resolved, SignalBase):
            return [_bind_for_reactive(loop_vars, iterable_resolved, node.body, ctx)]
        return _bind_for_static(iterable_resolved, loop_vars, node.body, ctx, iterable_path)

    scope = resolve_scope(plan, ctx)
    state = _EvalState()
    value = evaluate(plan, scope, state)
    if state.saw_signal:
        return [
            _bind_for_reactive(
                loop_vars, Computed(lambda plan=plan, scope=scope: evaluate(plan, scope)), node.body, ctx
            )
        ]

    return _bind_for_static(value, loop_vars, node.body, ctx, iterable_path)


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


def _bind_component_tag(node: TemplateElement, ctx: dict[str, Any], generator: Any) -> ElementChildren:
    props: dict[str, Any] = {}
    for attr in node.attrs:
        if attr.name.startswith("@"):
            raise WebComPyException(
                f"@event attribute '{attr.name}' is not supported on component "
                f"tags (<{node.tag_name}>). Components emit events via their "
                f"own API, not through DOM-style @ attributes."
            )
        if attr.name.startswith(":"):
            if any(isinstance(p, Hole) for p in attr.value):
                raise WebComPyException(
                    f"{{{{ }}}} interpolation is not supported in :prop attributes on component tags: {attr.name}"
                )
            raw_value = _attr_text(attr.value)
            props[kebab_to_snake(attr.name[1:])] = resolve_var(raw_value, ctx)
        else:
            if attr.is_boolean:
                value: Any = True
            else:
                value = resolve_attr(attr.value, ctx)
            props[kebab_to_snake(attr.name)] = value

    if node.children:
        body = node.children

        def slot_gen() -> ElementChildren:
            return _wrap_for_fragment(bind_children(body, ctx))

        slots: dict[str, Any] = {"default": slot_gen}
    else:
        slots = {}

    return generator(props, slots=slots)


def bind_element(node: TemplateElement, ctx: dict[str, Any]) -> ElementChildren:
    if node.tag_name == "br":
        if any(attr.name == ":bind" for attr in node.attrs):
            raise WebComPyException(
                ":bind is not supported on <br> "
                "(supported: input[type=text|email|password|search|tel|url|number|checkbox|radio] and textarea)"
            )
        return NewLine()

    store_obj: Any = inject(_COMPONENT_STORE_KEY, default=None)
    if store_obj is None:
        store_obj = _EMPTY_COMPONENT_STORE
    store = cast("ComponentStore", store_obj)
    resolution, component_name = resolve_tag(node.tag_name, store)
    if resolution is TagResolution.COMPONENT:
        assert component_name is not None
        generator = store.components[component_name]
        return _bind_component_tag(node, ctx, generator)

    events, ref, bind, regular_attrs = classify_attrs(node.attrs, ctx)
    resolved_attrs: dict[str, AttrValue] = {}
    for attr in regular_attrs:
        if attr.is_boolean:
            resolved_attrs[attr.name] = True
        else:
            resolved_attrs[attr.name] = resolve_attr(attr.value, ctx)
    if bind is not None:
        resolved_attrs[":bind"] = bind
    children = bind_children(node.children, ctx)
    return Element(
        tag_name=cast("HtmlTags", node.tag_name),
        attrs=resolved_attrs,
        events=events,
        ref=ref,
        children=children,
    )
