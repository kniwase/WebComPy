from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from logging import getLogger
from typing import Any

from webcompy.components._component import Component
from webcompy.components._context_manager import component_context
from webcompy.di import inject
from webcompy.di._keys import SUSPENSE_RESOLVING_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _patch_children, _position_element_nodes
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.utils._environment import ENVIRONMENT

_logger = getLogger(__name__)

_UNSET: Any = object()


async def _resolve_with_context(component: Component, coro: Coroutine[Any, Any, Any]) -> Any:
    with component_context(component._render_state):
        return await coro


def _restore_suspense_di_scope(
    scope: DIScope | None,
    original_scope: DIScope | None,
) -> None:
    """Exit the resolution scope and restore the pre-Suspense active scope.

    ``provide()`` during a Suspense child's setup switches ``_active_di_scope``
    to the component's child scope without a token. ``DIScope.__exit__`` is
    identity-guarded (it only unwinds when it is the active scope), so it can
    silently no-op when such a descendant remains active. Restoring the parent
    scope explicitly prevents the descendant from leaking into Suspense
    siblings and surrounding code.

    The scope argument may be ``None`` (e.g., the browser fast path never
    enters a resolution scope); the drift check still restores the captured
    parent scope in that case.
    """
    if scope is not None:
        scope.__exit__(None, None, None)
    if _active_di_scope.get(None) is not original_scope:
        _active_di_scope.set(original_scope)  # type: ignore[arg-type]


class SuspenseElement(DynamicElement):
    _resolved: bool

    def __init__(
        self,
        fallback: Callable[[], ElementChildren],
        children: Callable[[], ElementChildren],
        error_fallback: Callable[[], ElementChildren] | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._fallback_generator = fallback
        self._children_generator = children
        self._error_fallback_generator = error_fallback
        self._timeout = timeout
        self._resolved = False
        self._pending_tasks: list[asyncio.Task[Any]] = []
        super().__init__()

    def _on_set_parent(self):
        pass

    def _generate_children(self, generator: Callable[[], ElementChildren]) -> list[ElementAbstract]:
        ele = self._create_child_element(self._parent, None, generator())
        return [ele] if ele is not None else []

    def _generate_fallback(self) -> list[ElementAbstract]:
        return self._generate_children(self._fallback_generator)

    def _collect_pending_coroutines(
        self,
        children: list[ElementAbstract] | None = None,
    ) -> list[tuple[Component, Coroutine[Any, Any, Any]]]:
        pairs: list[tuple[Component, Coroutine[Any, Any, Any]]] = []
        source = children if children is not None else self._children

        def _walk(element: ElementAbstract) -> None:
            if isinstance(element, Component) and element._pending_async_template is not None:
                pairs.append((element, element._pending_async_template))
            if hasattr(element, "_children") and isinstance(element._children, (list, tuple)):
                for child in element._children:
                    _walk(child)

        for child in source:
            _walk(child)
        return pairs

    def _resolve_component_templates(
        self,
        pairs: list[tuple[Component, Coroutine[Any, Any, Any]]],
        results: list[Any],
    ) -> None:
        for (component, _), result in zip(pairs, results, strict=True):
            component._pending_async_template = None
            component._property["template"] = result
            component._refresh_async_setup_results()
            component._init_component(component._property)

    def _cleanup_pending_pairs(
        self,
        pairs: list[tuple[Component, Coroutine[Any, Any, Any]]] | None,
    ) -> None:
        if pairs is None:
            return
        for component, _ in pairs:
            component._cleanup_pending_async()

    async def _render(self):
        if not self._children:
            is_server = ENVIRONMENT != "pyscript"
            if is_server:
                await self._server_render()
            else:
                await self._browser_render()
        elif self._resolved:
            self._resolved = False
        await super()._render()

    async def _server_render(self):
        original_scope = _active_di_scope.get(None)
        scope = original_scope.create_child() if original_scope is not None else None
        if scope is not None:
            scope.provide(SUSPENSE_RESOLVING_KEY, True)
            scope.__enter__()
        try:
            children = self._generate_children(self._children_generator)
            self._children = children
            pairs = self._collect_pending_coroutines()
            if pairs:
                coroutines = [_resolve_with_context(component, coro) for component, coro in pairs]
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*coroutines, return_exceptions=True),
                        timeout=self._timeout,
                    )
                except TimeoutError:
                    _logger.warning("Suspense timed out after %ss, rendering fallback", self._timeout)
                    self._cleanup_pending_pairs(pairs)
                    fallback = self._generate_fallback()
                    self._children = fallback
                    return
                for _idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        if self._error_fallback_generator is not None:
                            _logger.warning(
                                "Suspense child async setup raised, rendering error_fallback: %s",
                                result,
                            )
                            self._cleanup_pending_pairs(pairs)
                            self._children = self._generate_children(self._error_fallback_generator)
                            return
                        else:
                            self._cleanup_pending_pairs(pairs)
                            raise result
                self._resolve_component_templates(pairs, results)
        finally:
            if scope is not None:
                _restore_suspense_di_scope(scope, original_scope)

    async def _browser_render(self):
        original_scope = _active_di_scope.get(None)
        children = self._generate_children(self._children_generator)
        pairs = self._collect_pending_coroutines(children)
        if not pairs:
            self._children = children
            self._resolved = True
            _restore_suspense_di_scope(None, original_scope)
            return
        fallback = self._generate_fallback()
        self._children = fallback
        self._resolved = False
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        task = scheduler.schedule(self._browser_resolve(children, pairs, original_scope=original_scope))
        self._pending_tasks.append(task)
        task.add_done_callback(lambda t: self._pending_tasks.remove(t) if t in self._pending_tasks else None)

    async def _browser_resolve(self, children=None, pairs=None, *, original_scope: Any = _UNSET):
        if original_scope is _UNSET:
            original_scope = _active_di_scope.get(None)
        scope = original_scope.create_child() if original_scope is not None else None
        if scope is not None:
            scope.provide(SUSPENSE_RESOLVING_KEY, True)
            scope.__enter__()
        try:
            if children is None:
                children = self._generate_children(self._children_generator)
            if pairs is None:
                pairs = self._collect_pending_coroutines(children)
            if pairs:
                coroutines = [_resolve_with_context(component, coro) for component, coro in pairs]
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*coroutines, return_exceptions=True),
                        timeout=self._timeout,
                    )
                except TimeoutError:
                    _logger.warning(
                        "Suspense resolution timed out after %ss, keeping fallback",
                        self._timeout,
                    )
                    self._cleanup_pending_pairs(pairs)
                    return
                for _idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        raise result
                self._resolve_component_templates(pairs, results)
            old_children = self._children
            self._cancel_pending_render_tasks()
            self._children = _patch_children(old_children, children, self._node_idx)
            self._resolved = True
            idx = self._node_idx
            for child in self._children:
                child._node_idx = idx
                await child._render()
                idx += child._node_count
            parent_node = self._parent._get_node()
            _position_element_nodes(self, parent_node, self._node_idx)
            self._parent._re_index_children(False)
        except asyncio.CancelledError:
            self._cleanup_pending_pairs(pairs)
            raise
        except Exception as e:
            self._cleanup_pending_pairs(pairs)
            await self._handle_error(e)
        finally:
            if scope is not None:
                _restore_suspense_di_scope(scope, original_scope)

    async def _handle_error(self, error: Exception) -> None:
        if self._error_fallback_generator is not None:
            error_fallback = self._generate_children(self._error_fallback_generator)
            old_children = self._children
            self._cancel_pending_render_tasks()
            self._children = _patch_children(old_children, error_fallback, self._node_idx)
            self._resolved = True
            idx = self._node_idx
            for child in self._children:
                child._node_idx = idx
                await child._render()
                idx += child._node_count
            parent_node = self._parent._get_node()
            _position_element_nodes(self, parent_node, self._node_idx)
            self._parent._re_index_children(False)
        else:
            from webcompy.elements.types._error_boundary import route_error_deferred

            _logger.error("Suspense child async raised without error_fallback: %s", error)
            route_error_deferred(self, error)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()
        super()._remove_element(recursive, remove_node)

    def _hydrate_node(self) -> None:
        from webcompy.components._component import Component, _active_app_context, _get_app_instance
        from webcompy.hydration import has_resolved_data

        original_scope = _active_di_scope.get(None)
        all_resolved = True
        test_children = self._generate_children(self._children_generator) if not self._children else self._children

        def _check_resolved(element: ElementAbstract) -> bool:
            if isinstance(element, Component):
                key = element._property.get("transfer_id") or element._property.get("component_id", "")
                if not has_resolved_data(key):
                    return False
            if hasattr(element, "_children") and isinstance(element._children, (list, tuple)):
                for child in element._children:
                    if not _check_resolved(child):
                        return False
            return True

        for child in test_children:
            if not _check_resolved(child):
                all_resolved = False
                break

        if all_resolved:
            scope = original_scope.create_child() if original_scope is not None else None
            if scope is not None:
                scope.provide(SUSPENSE_RESOLVING_KEY, True)
                scope.__enter__()
            try:
                self._children = test_children
                self._resolved = True
            finally:
                if scope is not None:
                    _restore_suspense_di_scope(scope, original_scope)
        else:
            app_ctx = _active_app_context.get() or _get_app_instance()
            probe_depth = getattr(app_ctx, "_transfer_probe_depth", 0) if app_ctx is not None else 0
            if app_ctx is not None:
                app_ctx._transfer_probe_depth = probe_depth + 1
            try:
                fallback = self._generate_fallback()
            finally:
                if app_ctx is not None:
                    app_ctx._transfer_probe_depth = probe_depth
            self._children = fallback
            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            task = scheduler.schedule(self._browser_resolve(test_children, original_scope=original_scope), render=True)
            self._pending_tasks.append(task)
            task.add_done_callback(lambda t: self._pending_tasks.remove(t) if t in self._pending_tasks else None)
        super()._hydrate_node()
