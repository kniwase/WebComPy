from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
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
from webcompy.elements.types._dynamic import DynamicElement, _run_refresh_sync
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._refference import DomNodeRef
from webcompy.elements.types._switch import SwitchElement
from webcompy.elements.types._text import NewLine, TextElement
from webcompy.exception import WebComPyException
from webcompy.signal import Computed, SignalBase
from webcompy.signal._graph import consumer_destroy
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
    _resolve_segments,
    _resolve_segments_with_signal,
    format_value,
    resolve_var,
    restore_protected,
)
from webcompy.template._naming import TagResolution, kebab_to_snake, resolve_tag

_EMPTY_COMPONENT_STORE = ComponentStore()


@dataclass
class LoopMetadata:
    index: object
    index0: object
    revindex: object
    revindex0: object
    first: object
    last: object
    length: object


def _make_loop_meta(index0: int, length: int) -> LoopMetadata:
    index = index0 + 1
    return LoopMetadata(
        index=index,
        index0=index0,
        revindex=length - index0,
        revindex0=length - index,
        first=index0 == 0,
        last=index == length,
        length=length,
    )


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
                segments = part.expr_source.split(".")
                static_value, saw_signal = _resolve_segments_with_signal(segments, ctx)
                if saw_signal:
                    has_signal = True
                    thunks.append(lambda segments=segments, ctx=ctx: format_value(_resolve_segments(segments, ctx)))
                else:
                    thunks.append(lambda v=static_value: format_value(v))
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
    loop_meta: LoopMetadata | None = None,
) -> dict[str, Any]:
    new_ctx = dict(ctx)
    if loop_meta is not None:
        new_ctx["loop"] = loop_meta
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
        total = len(items)
        for idx0, value in enumerate(items):
            meta = _make_loop_meta(idx0, total)
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, None, is_dict, loop_meta=meta)
            result.extend(bind_children(body, new_ctx))
        return result
    if len(loop_vars) == 2:
        if not is_dict:
            raise WebComPyException(
                f"Two-variable for-loop requires a dict iterable (got {type(iterable_resolved).__name__})"
            )
        items = list(iterable_resolved.items())
        total = len(items)
        for idx0, (key, value) in enumerate(items):
            meta = _make_loop_meta(idx0, total)
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, key, is_dict=True, loop_meta=meta)
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


class _DictValueRow(DynamicElement):
    """Keyed ``ReactiveDict`` row that regenerates its children when the stored
    value's representation (Element/Component vs scalar) or Element identity
    changes. Scalar value changes are handled reactively by the inner
    ``TextElement(Computed(read_value))``; representation changes rebuild the
    row via ``_refresh``.
    """

    def __init__(self, token: Computed, generator: Callable[[], ElementChildren]) -> None:
        super().__init__()
        self._token = token
        self._generator = generator

    def _on_set_parent(self) -> None:
        self._children = self._build_children()
        _ = self._token.value
        self._add_callback_node(self._token.on_after_updating(self._refresh_sync))

    def _build_children(self) -> list[ElementAbstract]:
        child = self._generator()
        if child is None:
            return []
        if isinstance(child, ElementAbstract):
            child._parent = self
            return [child]
        return [TextElement(child)]

    def _refresh_sync(self, *args: Any) -> None:
        _run_refresh_sync(self._refresh, *args)

    async def _refresh(self, *args: Any) -> None:
        self._cancel_pending_render_tasks()
        for child in self._children:
            child._remove_element()
        self._children = self._build_children()
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            await child._render()
            idx += child._node_count
        self._parent._re_index_children(False)


def _bind_dict_reactive(
    loop_vars: list[str],
    signal: SignalBase,
    body: list[TemplateNode],
    ctx: dict[str, Any],
) -> ElementChildren:
    def dict_cb(_value: Any, key: Any) -> ElementChildren:
        if not body:
            return FragmentElement()

        def read_value() -> Any:
            try:
                stored = signal.value[key]
            except (KeyError, IndexError):
                return _value
            if isinstance(stored, SignalBase):
                return stored.value
            return stored

        def _value_token() -> tuple[str, Any]:
            current = read_value()
            if isinstance(current, ElementAbstract):
                return ("element", current)
            return ("scalar", None)

        token = Computed(_value_token)

        def _row_generator() -> ElementChildren:
            length = Computed(lambda: len(signal.value))

            def pos() -> int:
                try:
                    return list(signal.value).index(key)
                except ValueError:
                    return -1

            meta = LoopMetadata(
                index=Computed(lambda: pos() + 1),
                index0=Computed(pos),
                revindex=Computed(lambda: len(signal.value) - pos()),
                revindex0=Computed(lambda: len(signal.value) - pos() - 1),
                first=Computed(lambda: pos() == 0),
                last=Computed(lambda: pos() + 1 == len(signal.value)),
                length=length,
            )
            members: list[SignalBase] = [
                cast("SignalBase", meta.index),
                cast("SignalBase", meta.index0),
                cast("SignalBase", meta.revindex),
                cast("SignalBase", meta.revindex0),
                cast("SignalBase", meta.first),
                cast("SignalBase", meta.last),
                cast("SignalBase", meta.length),
            ]
            current = read_value()
            if isinstance(current, ElementAbstract):
                loop_value: Any = current
            else:
                loop_value = Computed(read_value)
                members.append(loop_value)
            new_ctx = _extend_for_ctx(ctx, loop_vars, loop_value, key, is_dict=True, loop_meta=meta)
            try:
                result = _wrap_for_fragment(bind_children(body, new_ctx))
            except Exception:
                for member in members:
                    consumer_destroy(member)
                consumer_destroy(token)
                raise
            if result is None:
                result = FragmentElement()
            elif isinstance(result, (str, SignalBase)):
                result = TextElement(result)
            for idx, member in enumerate(members):
                result.__set_signal_member__(f"_loop_member_{idx}", member)
            return result

        return _DictValueRow(token, _row_generator)

    return repeat(signal, dict_cb)


def _bind_for_reactive(
    loop_vars: list[str],
    signal: SignalBase,
    body: list[TemplateNode],
    ctx: dict[str, Any],
) -> ElementChildren:
    is_dict = isinstance(signal.value, dict)

    if len(loop_vars) == 1:
        if is_dict:
            return _bind_dict_reactive(loop_vars, signal, body, ctx)

        gen: dict[str, Any] = {"idx": 0}

        def list_cb(value: Any) -> ElementChildren:
            idx0 = gen["idx"]
            gen["idx"] = idx0 + 1
            total = len(signal.value)
            if gen["idx"] >= total:
                gen["idx"] = 0
            meta = _make_loop_meta(idx0, total)
            new_ctx = _extend_for_ctx(ctx, loop_vars, value, None, is_dict, loop_meta=meta)
            return _wrap_for_fragment(bind_children(body, new_ctx))

        return repeat(signal, list_cb)

    if len(loop_vars) == 2:
        if not is_dict:
            raise WebComPyException("Two-variable for-loop over a reactive non-dict iterable is not supported")
        return _bind_dict_reactive(loop_vars, signal, body, ctx)

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
    element = Element(
        tag_name=cast("HtmlTags", node.tag_name),
        attrs=resolved_attrs,
        events=events,
        ref=ref,
        children=children,
    )
    for name, value in resolved_attrs.items():
        if name == ":bind":
            continue
        if isinstance(value, SignalBase):
            element.__set_signal_member__(f"__attr_{name}", value)
    return element
