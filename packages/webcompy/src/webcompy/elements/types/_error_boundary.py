from __future__ import annotations

from collections.abc import Callable
from logging import getLogger
from typing import Any

from webcompy.di import inject
from webcompy.di._keys import ERROR_POLICY_KEY
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _patch_children, _position_element_nodes
from webcompy.exception import WebComPyException

_logger = getLogger(__name__)


def report_unhandled_error(error: Exception) -> None:
    from webcompy.components._component import _active_app_context, _get_app_instance

    app = _active_app_context.get() or _get_app_instance()
    config = getattr(app, "_config", None) if app is not None else None
    handler = getattr(config, "on_error", None) if config is not None else None
    if handler is not None:
        try:
            handler(error)
            return
        except Exception as handler_err:
            from webcompy import logging as wc_logging

            wc_logging.error(f"WebComPyAppConfig.on_error handler raised: {handler_err!r}")
            return
    from webcompy.aio._aio import _log_error

    _log_error(error)


def _find_engaging_boundary(
    source: ElementAbstract | None,
    error: Exception,
    *,
    is_event_error: bool,
) -> tuple[bool, ErrorBoundaryElement | None]:
    from webcompy.components._component import Component

    element: ElementAbstract | None = source
    while element is not None:
        if isinstance(element, Component):
            for hook in getattr(element, "_error_captured_hooks", ()):
                try:
                    veto = hook(error)
                except Exception as hook_err:
                    _logger.warning("on_error_captured hook raised: %r", hook_err)
                    continue
                if veto is False:
                    return True, None
        if (
            isinstance(element, ErrorBoundaryElement)
            and not element._in_fallback
            and not element._swapping
            and (not is_event_error or element._catch_events)
        ):
            return False, element
        element = getattr(element, "_parent", None)
    return False, None


async def route_error(
    source: ElementAbstract | None,
    error: Exception,
    *,
    is_event_error: bool = False,
) -> None:
    handled, boundary = _find_engaging_boundary(source, error, is_event_error=is_event_error)
    if handled:
        return
    if boundary is not None:
        await boundary._engage(error)
        return
    report_unhandled_error(error)


def route_error_sync(
    source: ElementAbstract | None,
    error: Exception,
    *,
    is_event_error: bool = False,
) -> None:
    handled, boundary = _find_engaging_boundary(source, error, is_event_error=is_event_error)
    if handled:
        return
    if boundary is not None:
        from webcompy.elements.types._dynamic import _run_refresh_sync

        _run_refresh_sync(boundary._engage, error)
        return
    report_unhandled_error(error)


def route_error_deferred(
    source: ElementAbstract | None,
    error: Exception,
    *,
    is_event_error: bool = False,
) -> None:
    handled, boundary = _find_engaging_boundary(source, error, is_event_error=is_event_error)
    if handled:
        return
    if boundary is not None:
        from webcompy.aio._aio import aio_run

        aio_run(boundary._engage(error))
        return
    report_unhandled_error(error)


class ErrorBoundaryElement(DynamicElement):
    def __init__(
        self,
        children: Callable[[], ElementChildren],
        fallback: Callable[[Exception, Callable[[], None]], ElementChildren],
        on_error: Callable[[Exception], Any] | None = None,
        catch_events: bool = False,
    ) -> None:
        self._children_generator = children
        self._fallback_generator = fallback
        self._on_error_callback = on_error
        self._catch_events = catch_events
        self._in_fallback = False
        self._swapping = False
        self._error: Exception | None = None
        super().__init__()

    def _on_set_parent(self):
        pass

    def _generate_boundary_children(self, generator: Callable[[], ElementChildren]) -> list[ElementAbstract]:
        ele = self._create_child_element(self, None, generator())
        return [ele] if ele is not None else []

    async def _render(self):
        if not self._children:
            try:
                self._children = self._generate_boundary_children(self._children_generator)
            except WebComPyException:
                raise
            except Exception as err:
                await self._engage(err)
                return
        parent_node = self._parent._get_node()
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            try:
                if child._mounted is None and not self._hydrated:
                    await child._render()
            except WebComPyException:
                raise
            except Exception as err:
                await route_error(child, err)
                return
            idx += child._node_count
        self._hydrated = False
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)

    async def _engage(self, error: Exception) -> None:
        if self._in_fallback:
            return
        if inject(ERROR_POLICY_KEY, default="ssr") == "ssg":
            raise error
        self._in_fallback = True
        self._error = error
        from webcompy import logging as wc_logging

        wc_logging.error(f"ErrorBoundary caught: {error!r}")
        if self._on_error_callback is not None:
            try:
                self._on_error_callback(error)
            except Exception as cb_err:
                _logger.warning("ErrorBoundary on_error callback raised: %r", cb_err)
        try:
            fallback_children = self._generate_boundary_children(lambda: self._fallback_generator(error, self.reset))
        except Exception as fallback_err:
            await route_error(self, fallback_err)
            return
        try:
            await self._swap_children(fallback_children)
        except Exception as render_err:
            await route_error(self, render_err)

    async def _swap_children(self, new_children: list[ElementAbstract]) -> None:
        self._swapping = True
        try:
            old_children = self._children
            self._cancel_pending_render_tasks()
            self._children = _patch_children(old_children, new_children, self._node_idx)
        finally:
            self._swapping = False
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            await child._render()
            idx += child._node_count
        parent_node = self._parent._get_node()
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)

    def reset(self) -> None:
        if not self._in_fallback:
            return
        from webcompy.elements.types._dynamic import _run_refresh_sync

        _run_refresh_sync(self._do_reset)

    async def _do_reset(self) -> None:
        if not self._in_fallback:
            return
        self._in_fallback = False
        self._error = None
        try:
            new_children = self._generate_boundary_children(self._children_generator)
            await self._swap_children(new_children)
        except Exception as err:
            await self._engage(err)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        self._in_fallback = False
        self._error = None
        super()._remove_element(recursive, remove_node)

    def _hydrate_node(self) -> None:
        if not self._children:
            try:
                self._children = self._generate_boundary_children(self._children_generator)
            except Exception as err:
                route_error_deferred(self, err)
                return
        super()._hydrate_node()
