from __future__ import annotations

from collections.abc import Callable, Coroutine
from contextvars import ContextVar
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypeAlias, TypeGuard, cast
from uuid import UUID, uuid4

from webcompy.components._context_manager import component_context
from webcompy.components._libs import ComponentProperty, Context, generate_id
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._element import Element, ElementBase
from webcompy.exception import WebComPyException
from webcompy.signal import ReactiveDict, computed_property

if TYPE_CHECKING:
    from webcompy.app._render_context import RenderContext
    from webcompy.components._generator import ComponentGenerator

_active_app_context: ContextVar[RenderContext | None] = ContextVar("_active_app_context", default=None)

_app_instance: Any = None


def _set_app_instance(app: Any | None) -> None:
    global _app_instance
    _app_instance = app


def _get_app_instance() -> Any:
    return _app_instance


def start_defer_after_rendering() -> None:
    app = _active_app_context.get() or _get_app_instance()
    if app is not None:
        app._defer_depth += 1
    else:
        pass


def end_defer_after_rendering() -> list[Callable[[], None]]:
    app = _active_app_context.get() or _get_app_instance()
    if app is not None:
        app._defer_depth -= 1
        callbacks = app._deferred_callbacks[:]
        app._deferred_callbacks.clear()
        return callbacks
    return []


FuncComponentDef: TypeAlias = (
    Callable[[Context[Any]], ElementChildren] | Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]
)


def _is_function_style_component_def(obj: Any) -> TypeGuard[FuncComponentDef]:
    return bool(callable(obj) and getattr(obj, "__webcompy_component_definition__", None))


class HeadPropsStore:
    def __init__(self) -> None:
        self.titles = ReactiveDict[UUID, str]({})
        self.head_metas = ReactiveDict[UUID, dict[str, dict[str, str]]]({})
        self._app_title: str | None = None

    @computed_property
    def title(self):
        values = tuple(self.titles.values())
        return values[-1] if values else self._app_title

    @computed_property
    def head_meta(self):
        return {key: attributes for meta in self.head_metas.values() for key, attributes in meta.items()}


class Component(ElementBase):
    def __init__(
        self,
        component_def: FuncComponentDef,
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
        generator: ComponentGenerator[Any] | None = None,
    ) -> None:
        self._instance_id = uuid4()
        self._attrs = {}
        self._event_handlers = {}
        self._ref = None
        self._children = []
        self._head_props: HeadPropsStore | None = None
        self._generator = generator
        self._pending_async_template: Coroutine[Any, Any, ElementChildren] | None = None
        self._async_results: list = []
        self._async_setup_extracted: bool = False
        super().__init__()
        property = self.__setup(component_def, props, slots)
        self._property = property
        if self._pending_async_template is None:
            self._init_component(property)

    def __setup(
        self,
        component_def: FuncComponentDef,
        props: Any,
        slots: dict[str, Callable[[], ElementChildren]],
    ) -> ComponentProperty:
        from webcompy.components._context_manager import ComponentRenderState, component_context
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
            generator=self._generator,
        )
        scope = create_effect_scope()

        parent_di_scope = _active_di_scope.get(None)
        pending_token = None
        existing_children_count = 0

        if parent_di_scope is not None:
            pending_token = _pending_di_parent.set(parent_di_scope)
            existing_children_count = len(parent_di_scope._children)

        child_di_scope: DIScope | None = None

        def _framework_cleanup():
            if child_di_scope is not None:
                child_di_scope.dispose()
            scope.dispose()

        self._render_state = ComponentRenderState(
            context=context,
            effect_scope=scope,
            framework_cleanup=_framework_cleanup,
        )

        try:
            with component_context(self._render_state):
                if iscoroutinefunction(component_def):
                    coro = component_def(context)
                    self._pending_async_template = coro
                    template: ElementChildren | None = None
                else:
                    template = cast("ElementChildren", component_def(context))
        finally:
            if pending_token is not None:
                _pending_di_parent.reset(pending_token)

        self._async_results = list(context._async_results)
        self._merge_transferables(context)

        if self._pending_async_template is None:
            self._async_setup_extracted = True

        if parent_di_scope is not None and len(parent_di_scope._children) > existing_children_count:
            child_di_scope = parent_di_scope._children[-1]

        hooks = context.__get_lifecyclehooks__()
        original_on_before_destroy = hooks.get("on_before_destroy", lambda: None)

        def on_before_destroy_with_scope_cleanup():
            self._render_state.framework_cleanup()
            original_on_before_destroy()

        return {
            "component_id": generate_id(component_name),
            "component_name": component_name,
            "template": template,
            "on_before_rendering": hooks.get("on_before_rendering", lambda: None),
            "on_after_rendering": hooks.get("on_after_rendering", lambda: None),
            "on_before_destroy": on_before_destroy_with_scope_cleanup,
        }

    def _init_component(self, property: ComponentProperty):
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
        self._preserve_children = node._preserve_children
        self._init_children(node._children)
        self._property = property

    def _cleanup_pending_async(self):
        self._pending_async_template = None
        self._property["on_before_destroy"]()
        for cb in self._callback_nodes:
            from webcompy.signal._graph import consumer_destroy

            consumer_destroy(cb)
        self._callback_nodes.clear()
        self.__purge_signal_members__()

    def _merge_transferables(self, context: Any) -> None:
        for key, sig in context._transferable_signals.items():
            self.__set_signal_member__(key, sig)

    def _refresh_async_setup_results(self) -> None:
        if self._render_state is None:
            return
        context = self._render_state.context
        hooks = context.__get_lifecyclehooks__()
        self._property["on_before_rendering"] = hooks.get("on_before_rendering", lambda: None)
        self._property["on_after_rendering"] = hooks.get("on_after_rendering", lambda: None)
        user_on_before_destroy = hooks.get("on_before_destroy", lambda: None)
        framework_cleanup = self._render_state.framework_cleanup

        def on_before_destroy_with_scope_cleanup():
            framework_cleanup()
            user_on_before_destroy()

        self._property["on_before_destroy"] = on_before_destroy_with_scope_cleanup
        self._async_results = list(context._async_results)
        self._merge_transferables(context)
        self._async_setup_extracted = True

    async def _render(self):
        if self._pending_async_template is not None:
            from webcompy.di import inject
            from webcompy.di._keys import SUSPENSE_RESOLVING_KEY

            if not inject(SUSPENSE_RESOLVING_KEY, default=False):
                try:
                    with component_context(self._render_state):
                        template = await self._pending_async_template
                except Exception:
                    self._cleanup_pending_async()
                    try:
                        parent = self._parent
                    except AttributeError:
                        parent = None
                    if parent is not None and self in parent._children:
                        parent._children.remove(self)
                    raise
                self._pending_async_template = None
                property = self._property
                property["template"] = template
                self._refresh_async_setup_results()
                self._init_component(property)
        if not self._async_setup_extracted and self._render_state is not None:
            self._refresh_async_setup_results()
        on_before = self._property["on_before_rendering"]
        if iscoroutinefunction(on_before):
            await on_before()
        else:
            on_before()
        await super()._render()
        on_after = self._property["on_after_rendering"]
        app = _active_app_context.get() or _get_app_instance()
        if app is not None and app._defer_depth > 0:
            app._deferred_callbacks.append(on_after)
        else:
            if iscoroutinefunction(on_after):
                await on_after()
            else:
                on_after()

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        if self._pending_async_template is not None:
            self._cleanup_pending_async()
            return
        if self._head_props is not None:
            if self._instance_id in self._head_props.titles:
                del self._head_props.titles[self._instance_id]
            if self._instance_id in self._head_props.head_metas:
                del self._head_props.head_metas[self._instance_id]
        self._property["on_before_destroy"]()
        super()._remove_element(recursive, remove_node)

    def _detach_from_node(self) -> None:
        if self._pending_async_template is not None:
            self._cleanup_pending_async()
            return
        if self._head_props is not None:
            if self._instance_id in self._head_props.titles:
                del self._head_props.titles[self._instance_id]
            if self._instance_id in self._head_props.head_metas:
                del self._head_props.head_metas[self._instance_id]
        self._property["on_before_destroy"]()
        super()._detach_from_node()

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
