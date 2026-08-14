from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Mapping
from contextvars import ContextVar
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypeAlias, TypeGuard, cast
from uuid import UUID, uuid4

from webcompy.components._context_manager import component_context
from webcompy.components._libs import (
    ComponentProperty,
    ComponentTemplateResult,
    Context,
    WebComPyComponentException,
    generate_id,
)
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.typealias._html_tag_names import HtmlTags
from webcompy.elements.types._element import Element, ElementBase
from webcompy.exception import WebComPyException
from webcompy.ports._dom import DOMNode
from webcompy.signal import ReactiveDict, computed_property
from webcompy.signal._computed import _OwnedComputed

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
    Callable[[Context[Any]], ComponentTemplateResult]
    | Callable[[Context[Any]], Coroutine[Any, Any, ComponentTemplateResult]]
)


def _is_function_style_component_def(obj: Any) -> TypeGuard[FuncComponentDef]:
    return bool(callable(obj) and getattr(obj, "__webcompy_component_definition__", None))


def _normalize_component_template(template: ComponentTemplateResult | None) -> list[ElementChildren]:
    if template is None:
        return []
    if isinstance(template, list):
        return template
    if isinstance(template, tuple):
        return list(template)
    return [template]


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
        self._pending_async_template: Coroutine[Any, Any, ComponentTemplateResult] | None = None
        self._pending_async_cleanup_done: bool = False
        self._async_results: list = []
        self._async_setup_extracted: bool = False
        self._error_captured_hooks: list[Callable[[Exception], Any]] = []
        self._observed_props: ReactiveDict[str, Any] | None = None
        self._custom_element_binding: Any = None
        self._mount_delivered: bool = False
        self._flush_scheduled: bool = False
        self._destroyed: bool = False
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
        props_for_context = self._prepare_props_for_setup(props)
        context = Context(
            props_for_context,
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
                    template: ComponentTemplateResult | None = None
                else:
                    template = cast("ComponentTemplateResult", component_def(context))
        finally:
            if pending_token is not None:
                _pending_di_parent.reset(pending_token)

        self._async_results = list(context._async_results)
        self._error_captured_hooks = list(context._error_captured_hooks)
        self._merge_transferables(context)

        if self._pending_async_template is None:
            self._async_setup_extracted = True

        if parent_di_scope is not None and len(parent_di_scope._children) > existing_children_count:
            child_di_scope = parent_di_scope._children[-1]

        hooks = context.__get_lifecyclehooks__()
        if (hooks.get("on_mounted") or hooks.get("on_unmounted")) and (
            self._generator is None or self._generator.custom_element_name is None
        ):
            raise WebComPyComponentException(
                "on_mounted/on_unmounted are only available for named custom-element components; "
                "pass a custom element name to @define_component"
            )
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
            "on_mounted": hooks.get("on_mounted", lambda: None),
            "on_unmounted": hooks.get("on_unmounted", lambda: None),
        }

    def _prepare_props_for_setup(self, props: Any) -> Any:
        if self._generator is None or not self._generator.observed_attributes:
            return props
        if props is None:
            props_for_context: ReactiveDict[str, Any] = ReactiveDict({})
        elif isinstance(props, ReactiveDict):
            props_for_context = props
        elif isinstance(props, Mapping):
            props_for_context = ReactiveDict(dict(props))
        else:
            raise WebComPyComponentException("Components with observed_attributes require mapping props (or None)")
        for prop_key in self._generator.observed_prop_keys.values():
            if prop_key not in props_for_context.value:
                props_for_context[prop_key] = None
        self._observed_props = props_for_context
        return props_for_context

    def _init_component(self, property: ComponentProperty):
        generator = self._generator
        if generator is not None and generator.custom_element_name is not None:
            self._tag_name = cast("HtmlTags", generator.custom_element_name)
            self._attrs = {
                "webcompy-component": property["component_name"],
                "webcompy-cid-" + property["component_id"]: True,
            }
            self._event_handlers = {}
            self._ref = None
            self._preserve_children = False
            self._init_children(_normalize_component_template(property["template"]))
            self._property = property
            return
        node = property["template"]
        if not isinstance(node, Element):
            raise WebComPyException("Root Node of Component must be instance of 'Element'")
        self._tag_name = node._tag_name
        self._attrs = {
            **node._attrs,
            "webcompy-component": property["component_name"],
            "webcompy-cid-" + property["component_id"]: True,
        }
        for name, value in self._attrs.items():
            if isinstance(value, _OwnedComputed):
                self.__set_signal_member__(f"__attr_{name}", value)
        self._event_handlers = node._event_handlers
        self._ref = node._ref
        self._preserve_children = node._preserve_children
        self._init_children(node._children)
        self._property = property

    def _cleanup_pending_async(self):
        if self._pending_async_cleanup_done:
            return
        self._pending_async_cleanup_done = True
        self._pending_async_template = None
        try:
            if self._render_state is not None:
                hooks = self._render_state.context.__get_lifecyclehooks__()
                user_on_before_destroy = hooks.get("on_before_destroy", lambda: None)
                framework_cleanup = self._render_state.framework_cleanup

                def on_before_destroy_with_scope_cleanup():
                    framework_cleanup()
                    user_on_before_destroy()

                self._property["on_before_destroy"] = on_before_destroy_with_scope_cleanup
            self._property["on_before_destroy"]()
        except Exception as err:
            from webcompy.elements.types._error_boundary import route_error_deferred

            route_error_deferred(self, err)
        finally:
            self._property["on_before_destroy"] = lambda: None
        self._error_captured_hooks.clear()
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
        if (hooks.get("on_mounted") or hooks.get("on_unmounted")) and (
            self._generator is None or self._generator.custom_element_name is None
        ):
            raise WebComPyComponentException(
                "on_mounted/on_unmounted are only available for named custom-element components; "
                "pass a custom element name to @define_component"
            )
        self._property["on_before_rendering"] = hooks.get("on_before_rendering", lambda: None)
        self._property["on_after_rendering"] = hooks.get("on_after_rendering", lambda: None)
        user_on_before_destroy = hooks.get("on_before_destroy", lambda: None)
        framework_cleanup = self._render_state.framework_cleanup

        def on_before_destroy_with_scope_cleanup():
            framework_cleanup()
            user_on_before_destroy()

        self._property["on_before_destroy"] = on_before_destroy_with_scope_cleanup
        self._property["on_mounted"] = hooks.get("on_mounted", lambda: None)
        self._property["on_unmounted"] = hooks.get("on_unmounted", lambda: None)
        self._async_results = list(context._async_results)
        self._error_captured_hooks = list(context._error_captured_hooks)
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
                except (asyncio.CancelledError, Exception):
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
        try:
            if iscoroutinefunction(on_before):
                await on_before()
            else:
                on_before()
        except Exception as err:
            from webcompy.elements.types._error_boundary import route_error_deferred

            route_error_deferred(self, err)
            return
        await super()._render()
        on_after = self._property["on_after_rendering"]
        app = _active_app_context.get() or _get_app_instance()
        if app is not None and app._defer_depth > 0:
            app._deferred_callbacks.append(on_after)
        else:
            try:
                if iscoroutinefunction(on_after):
                    await on_after()
                else:
                    on_after()
            except Exception as err:
                from webcompy.elements.types._error_boundary import route_error_deferred

                route_error_deferred(self, err)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        if self._pending_async_template is not None:
            self._cleanup_pending_async()
            self._dispose_custom_element_binding()
            return
        if self._head_props is not None:
            if self._instance_id in self._head_props.titles:
                del self._head_props.titles[self._instance_id]
            if self._instance_id in self._head_props.head_metas:
                del self._head_props.head_metas[self._instance_id]
        node = self._node_cache
        if remove_node and node is not None and self._mount_delivered:
            node.remove()
            early_removed = True
        else:
            early_removed = False
        if self._mount_delivered:
            port = self._custom_element_port
            connected = False
            if node is not None:
                if port is not None:
                    connected = port.is_document_connected(node)
                else:
                    connected = bool(getattr(node, "isConnected", False))
            self._mount_delivered = False
            if not connected:
                self._invoke_hook("on_unmounted")
        try:
            self._property["on_before_destroy"]()
        except Exception as err:
            from webcompy.elements.types._error_boundary import route_error_deferred

            route_error_deferred(self, err)
        self._error_captured_hooks.clear()
        super()._remove_element(recursive, remove_node and not early_removed)
        self._dispose_custom_element_binding()

    def _detach_from_node(self) -> None:
        if self._pending_async_template is not None:
            self._cleanup_pending_async()
            self._dispose_custom_element_binding()
            return
        if self._head_props is not None:
            if self._instance_id in self._head_props.titles:
                del self._head_props.titles[self._instance_id]
            if self._instance_id in self._head_props.head_metas:
                del self._head_props.head_metas[self._instance_id]
        node = self._node_cache
        if self._mount_delivered:
            port = self._custom_element_port
            connected = False
            if node is not None:
                if port is not None:
                    connected = port.is_document_connected(node)
                else:
                    connected = bool(getattr(node, "isConnected", False))
            self._mount_delivered = False
            if not connected:
                self._invoke_hook("on_unmounted")
        try:
            self._property["on_before_destroy"]()
        except Exception as err:
            from webcompy.elements.types._error_boundary import route_error_deferred

            route_error_deferred(self, err)
        self._error_captured_hooks.clear()
        super()._detach_from_node()
        self._dispose_custom_element_binding()

    def _get_belonging_component(self):
        return self._property["component_id"]

    def _get_belonging_components(self) -> tuple[Component, ...]:
        return (*self._parent._get_belonging_components(), self)

    def _preserves_all_node_attributes(self) -> bool:
        return self._generator is not None and self._generator.custom_element_name is not None

    def _create_node(self) -> DOMNode:
        generator = self._generator
        if generator is not None and generator.custom_element_name is not None:
            from webcompy.di import inject
            from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

            port = inject(CUSTOM_ELEMENT_PORT_KEY, default=None)
            if port is not None:
                assert generator.definition_key is not None
                port.ensure_defined(
                    generator.custom_element_name,
                    generator.observed_attributes,
                    generator.definition_key,
                )
        return super()._create_node()

    def _init_new_node(self, node: DOMNode) -> None:
        super()._init_new_node(node)
        self._bind_custom_element(node)

    def _adopt_node(self, node: DOMNode) -> None:
        super()._adopt_node(node)
        self._bind_custom_element(node)

    def _bind_custom_element(self, node: DOMNode) -> None:
        generator = self._generator
        if generator is None or generator.custom_element_name is None:
            return
        from webcompy.di import inject
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        port = inject(CUSTOM_ELEMENT_PORT_KEY, default=None)
        if port is None:
            return
        if self._custom_element_binding is not None:
            self._custom_element_binding.dispose()
            self._custom_element_binding = None
        binding = port.bind(
            node,
            observed_attributes=generator.observed_attributes,
            on_connected=self._on_custom_element_connected,
            on_disconnected=self._on_custom_element_disconnected,
            on_attribute_changed=self._on_custom_element_attribute_changed,
        )
        self._custom_element_binding = binding
        self._sync_observed_attributes(node)
        if port.is_document_connected(node):
            self._schedule_connection_flush()

    def _dispose_custom_element_binding(self) -> None:
        self._destroyed = True
        self._mount_delivered = False
        binding = self._custom_element_binding
        self._custom_element_binding = None
        if binding is not None:
            binding.dispose()

    def _sync_observed_attributes(self, node: DOMNode) -> None:
        if self._observed_props is None or self._generator is None:
            return
        from webcompy.di import inject
        from webcompy.ports._keys import FFI_PORT_KEY

        ffi = inject(FFI_PORT_KEY, default=None)
        for attr_name, prop_key in self._generator.observed_prop_keys.items():
            raw = node.getAttribute(attr_name)
            value: str | None = None if raw is None or (ffi is not None and ffi.is_none(raw)) else str(raw)
            if self._observed_props.value.get(prop_key) != value:
                self._observed_props[prop_key] = value

    def _on_custom_element_attribute_changed(self, name: str, new_value: str | None) -> None:
        if self._observed_props is None or self._generator is None:
            return
        prop_key = self._generator.observed_prop_keys.get(name)
        if prop_key is None:
            return
        if self._observed_props.value.get(prop_key) != new_value:
            self._observed_props[prop_key] = new_value

    def _on_custom_element_connected(self) -> None:
        self._schedule_connection_flush()

    def _on_custom_element_disconnected(self) -> None:
        self._schedule_connection_flush()

    def _schedule_connection_flush(self) -> None:
        if self._destroyed or self._flush_scheduled:
            return
        self._flush_scheduled = True
        from webcompy.di import inject
        from webcompy.ports._keys import HOST_PORT_KEY

        host_port = inject(HOST_PORT_KEY, default=None)
        if host_port is not None:
            host_port.schedule_macro_task(self._flush_connection_state)

    def _flush_connection_state(self) -> None:
        self._flush_scheduled = False
        if self._destroyed:
            return
        node = self._node_cache
        if node is None:
            return
        from webcompy.di import inject
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY

        port = inject(CUSTOM_ELEMENT_PORT_KEY, default=None)
        if port is None:
            return
        connected = port.is_document_connected(node)
        if connected and not self._mount_delivered:
            self._mount_delivered = True
            self._invoke_hook("on_mounted")
        elif not connected and self._mount_delivered:
            self._mount_delivered = False
            self._invoke_hook("on_unmounted")

    def _invoke_hook(self, key: str) -> None:
        hook = self._property.get(key)
        if hook is None:
            return
        if iscoroutinefunction(hook):
            from webcompy.aio import resolve_async
            from webcompy.elements.types._error_boundary import route_error_deferred

            resolve_async(hook(), on_error=lambda err: route_error_deferred(self, err))
            return
        try:
            hook()
        except Exception as err:
            from webcompy.elements.types._error_boundary import route_error_deferred

            route_error_deferred(self, err)

    def _set_title(self, title: str):
        if self._head_props is not None:
            self._head_props.titles[self._instance_id] = title

    def _set_meta(self, key: str, attributes: dict[str, str]):
        if self._head_props is not None:
            meta = self._head_props.head_metas.get(self._instance_id, {})
            meta[key] = attributes
            self._head_props.head_metas[self._instance_id] = meta
