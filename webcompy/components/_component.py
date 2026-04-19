from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias, TypeGuard
from uuid import UUID, uuid4

from webcompy._browser._modules import browser
from webcompy.components._hooks import _active_component_context
from webcompy.components._libs import ComponentProperty, Context, generate_id
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._element import Element, ElementBase
from webcompy.exception import WebComPyException
from webcompy.signal import ReactiveDict, computed_property

_defer_after_rendering_depth: int = 0
_deferred_after_rendering_callbacks: list[Callable[[], None]] = []


def start_defer_after_rendering() -> None:
    global _defer_after_rendering_depth
    _defer_after_rendering_depth += 1


def end_defer_after_rendering() -> list[Callable[[], None]]:
    global _defer_after_rendering_depth, _deferred_after_rendering_callbacks
    _defer_after_rendering_depth -= 1
    callbacks = _deferred_after_rendering_callbacks[:]
    _deferred_after_rendering_callbacks.clear()
    return callbacks


FuncComponentDef: TypeAlias = Callable[[Context[Any]], ElementChildren]


def _is_function_style_component_def(obj: Any) -> TypeGuard[FuncComponentDef]:
    return bool(callable(obj) and getattr(obj, "__webcompy_component_definition__", None))


class HeadPropsStore:
    def __init__(self) -> None:
        self.titles = ReactiveDict[UUID, str]({})
        self.head_metas = ReactiveDict[UUID, dict[str, dict[str, str]]]({})

    @computed_property
    def title(self):
        return tuple(self.titles.values())[-1]

    @computed_property
    def head_meta(self):
        return {key: attributes for meta in self.head_metas.values() for key, attributes in meta.items()}


class Component(ElementBase):
    def __init__(
        self,
        component_def: FuncComponentDef,
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> None:
        self._instance_id = uuid4()
        self._attrs = {}
        self._event_handlers = {}
        self._ref = None
        self._children = []
        self._head_props: HeadPropsStore | None = None
        super().__init__()
        self.__init_component(self.__setup(component_def, props, slots))

    def __setup(
        self,
        component_def: FuncComponentDef,
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> ComponentProperty:
        from webcompy.components._hooks import _active_effect_scope
        from webcompy.di import _pending_di_parent, inject
        from webcompy.di._keys import _HEAD_PROPS_KEY
        from webcompy.signal._effect import create_effect_scope

        component_name = component_def.__name__
        head_props = inject(_HEAD_PROPS_KEY)
        self._head_props = head_props
        context = Context(
            props,
            slots,
            component_name,
            lambda: head_props.title.value,
            lambda: head_props.head_meta.value,
            self._set_title,
            self._set_meta,
        )
        token = _active_component_context.set(context)
        scope = create_effect_scope()
        scope_token = _active_effect_scope.set(scope)

        parent_di_scope = _active_di_scope.get(None)
        di_token = None
        pending_token = None
        existing_children_count = 0

        if parent_di_scope is not None:
            di_token = _active_di_scope.set(parent_di_scope)
            pending_token = _pending_di_parent.set(parent_di_scope)
            existing_children_count = len(parent_di_scope._children)

        try:
            template = component_def(context)
        finally:
            _active_component_context.reset(token)
            _active_effect_scope.reset(scope_token)
            if pending_token is not None:
                _pending_di_parent.reset(pending_token)
            if di_token is not None:
                _active_di_scope.reset(di_token)

        child_di_scope: DIScope | None = None
        if parent_di_scope is not None and len(parent_di_scope._children) > existing_children_count:
            child_di_scope = parent_di_scope._children[-1]

        hooks = context.__get_lifecyclehooks__()
        original_on_before_destroy = hooks.get("on_before_destroy", lambda: None)

        def on_before_destroy_with_scope_cleanup():
            if child_di_scope is not None:
                child_di_scope.dispose()
            scope.dispose()
            original_on_before_destroy()

        return {
            "component_id": generate_id(component_name),
            "component_name": component_name,
            "template": template,
            "on_before_rendering": hooks.get("on_before_rendering", lambda: None),
            "on_after_rendering": hooks.get("on_after_rendering", lambda: None),
            "on_before_destroy": on_before_destroy_with_scope_cleanup,
        }

    def __init_component(self, property: ComponentProperty):
        node = property["template"]
        if not isinstance(node, Element):
            raise WebComPyException("Root Node of Component must be instance of 'Element'")
        self._tag_name = node._tag_name
        self._attrs = {
            **node._attrs,
            "webcompy-component": property["component_name"],
            "webcompy-cid-" + property["component_id"]: True,
        }
        self._event_handlers = node._event_handlers
        self._ref = node._ref
        self._init_children(node._children)
        self._property = property

    def _render(self):
        self._property["on_before_rendering"]()
        super()._render()
        after_rendering = self._property["on_after_rendering"]
        global _defer_after_rendering_depth, _deferred_after_rendering_callbacks
        if _defer_after_rendering_depth > 0 and browser:
            _deferred_after_rendering_callbacks.append(after_rendering)
        else:
            after_rendering()

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        if self._head_props is not None:
            if self._instance_id in self._head_props.titles:
                del self._head_props.titles[self._instance_id]
            if self._instance_id in self._head_props.head_metas:
                del self._head_props.head_metas[self._instance_id]
        self._property["on_before_destroy"]()
        super()._remove_element(recursive, remove_node)

    def _get_belonging_component(self):
        return self._property["component_id"]

    def _get_belonging_components(self) -> tuple[Component, ...]:
        return (*self._parent._get_belonging_components(), self)

    def _set_title(self, title: str):
        if self._head_props is not None:
            self._head_props.titles[self._instance_id] = title

    def _set_meta(self, key: str, attributes: dict[str, str]):
        if self._head_props is not None:
            meta = self._head_props.head_metas.get(self._instance_id, {})
            meta[key] = attributes
            self._head_props.head_metas[self._instance_id] = meta
