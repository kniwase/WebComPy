from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from logging import getLogger
from typing import Any

from webcompy.components._component import Component
from webcompy.di._keys import SUSPENSE_RESOLVING_KEY
from webcompy.di._scope import _active_di_scope
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _patch_children, _position_element_nodes
from webcompy.utils._environment import ENVIRONMENT

_logger = getLogger(__name__)


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
    ) -> list[tuple[Component, Coroutine[Any, Any, Any]]]:
        pairs: list[tuple[Component, Coroutine[Any, Any, Any]]] = []

        def _walk(element: ElementAbstract) -> None:
            if isinstance(element, Component) and element._pending_async_template is not None:
                pairs.append((element, element._pending_async_template))
            if hasattr(element, "_children") and isinstance(element._children, (list, tuple)):
                for child in element._children:
                    _walk(child)

        for child in self._children:
            _walk(child)
        return pairs

    def _resolve_component_templates(
        self,
        pairs: list[tuple[Component, Coroutine[Any, Any, Any]]],
        results: list[Any],
    ) -> None:
        for (component, _), result in zip(pairs, results, strict=False):
            if isinstance(result, Exception):
                continue
            component._pending_async_template = None
            component._property["template"] = result
            component.__init_component(component._property)

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
                coroutines = [coro for _, coro in pairs]
                try:
                    results = await asyncio.wait_for(
                        asyncio.gather(*coroutines, return_exceptions=True),
                        timeout=self._timeout,
                    )
                except TimeoutError:
                    _logger.warning("Suspense timed out after %ss, rendering fallback", self._timeout)
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
                            self._children = self._generate_children(self._error_fallback_generator)
                            return
                        else:
                            raise result
                self._resolve_component_templates(pairs, results)
        finally:
            if scope is not None:
                scope.__exit__(None, None, None)

    async def _browser_render(self):
        fallback = self._generate_fallback()
        self._children = fallback
        self._resolved = False
        task = asyncio.ensure_future(self._browser_resolve())
        self._pending_tasks.append(task)
        task.add_done_callback(lambda t: self._pending_tasks.remove(t) if t in self._pending_tasks else None)

    async def _browser_resolve(self):
        original_scope = _active_di_scope.get(None)
        scope = original_scope.create_child() if original_scope is not None else None
        if scope is not None:
            scope.provide(SUSPENSE_RESOLVING_KEY, True)
            scope.__enter__()
        try:
            children = self._generate_children(self._children_generator)
            pairs = self._collect_pending_coroutines()
            if pairs:
                coroutines = [coro for _, coro in pairs]
                results = await asyncio.gather(*coroutines, return_exceptions=True)
                for _idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        raise result
                self._resolve_component_templates(pairs, [r for r in results if not isinstance(r, Exception)])
            self._resolve(children)
        except Exception as e:
            self._handle_error(e)
        finally:
            if scope is not None:
                scope.__exit__(None, None, None)

    def _resolve(self, new_children: list[ElementAbstract]) -> None:
        old_children = self._children
        self._children = _patch_children(old_children, new_children, self._node_idx)
        self._resolved = True
        parent_node = self._parent._get_node()
        _position_element_nodes(self, parent_node, self._node_idx)

    def _handle_error(self, error: Exception) -> None:
        if self._error_fallback_generator is not None:
            error_fallback = self._generate_children(self._error_fallback_generator)
            old_children = self._children
            self._children = _patch_children(old_children, error_fallback, self._node_idx)
            self._resolved = True
            parent_node = self._parent._get_node()
            _position_element_nodes(self, parent_node, self._node_idx)
        else:
            _logger.warning("Suspense child async raised without error_fallback: %s", error)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()
        super()._remove_element(recursive, remove_node)

    def _hydrate_node(self) -> None:
        from webcompy.components._component import Component
        from webcompy.hydration import has_resolved_data

        all_resolved = True
        test_children = self._generate_children(self._children_generator) if not self._children else self._children

        def _check_resolved(element: ElementAbstract) -> bool:
            if isinstance(element, Component):
                cid = element._property.get("component_id", "")
                if not has_resolved_data(cid):
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
            original_scope = _active_di_scope.get(None)
            scope = original_scope.create_child() if original_scope is not None else None
            if scope is not None:
                scope.provide(SUSPENSE_RESOLVING_KEY, True)
                scope.__enter__()
            try:
                self._children = test_children
                self._resolved = True
            finally:
                if scope is not None:
                    scope.__exit__(None, None, None)
        else:
            fallback = self._generate_fallback()
            self._children = fallback
            task = asyncio.ensure_future(self._browser_resolve())
            self._pending_tasks.append(task)
            task.add_done_callback(lambda t: self._pending_tasks.remove(t) if t in self._pending_tasks else None)
        super()._hydrate_node()
