"""``RouterView`` element rendering the matched route chain."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from inspect import iscoroutinefunction
from typing import cast

from webcompy.components._component import end_defer_after_rendering, start_defer_after_rendering
from webcompy.di import inject
from webcompy.di._exceptions import InjectionError
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements.typealias._element_property import ElementChildren
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import DynamicElement, _position_element_nodes
from webcompy.elements.types._error_boundary import ErrorBoundaryElement
from webcompy.ports._keys import HOST_PORT_KEY
from webcompy.router._context import TypedRouterContext
from webcompy.router._router import RouteMatch
from webcompy.signal import Computed


class RouterView(DynamicElement):
    """Dynamic element rendering the component for the currently matched route level.

    Each ``RouterView`` renders one level of the matched route chain and
    reuses the mounted component while that level's identity is
    unchanged across navigations.
    """

    _mounted_depth: int | None
    _mounted_component: ElementAbstract | None
    _mounted_identity: tuple | None
    _signal_activated: bool

    def __init__(self) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise RuntimeError("'Router' instance is not provided via DI.") from None
        self._router = router
        self._mounted_depth = None
        self._mounted_component = None
        self._mounted_identity = None
        self._signal_activated = False
        self._navigation_generation = 0
        super().__init__()

    def _count_router_view_ancestors(self) -> int:
        depth = 0
        parent = getattr(self, "_parent", None)
        while parent is not None:
            if isinstance(parent, RouterView):
                depth += 1
            parent = getattr(parent, "_parent", None)
        return depth

    def _on_set_parent(self):
        if getattr(self, "_level_match", None) is not None:
            return
        self._children = []
        router = self._router
        self._level_match = Computed(lambda: router.current_match.value)
        self._add_callback_node(self._level_match.on_after_updating(self._on_match_changed))
        router.after_route_change.append(self._on_navigate_attempt)
        if router._preload:
            router.preload_lazy_routes()

    def _build_identity(self, match: RouteMatch, depth: int) -> tuple:
        node = match.chain[depth]
        accumulated = self._accumulate_params(match, depth)
        return (
            id(node),
            tuple(sorted(accumulated.items())),
            tuple(sorted(match.query.items())),
        )

    def _accumulate_params(self, match: RouteMatch, depth: int) -> dict[str, str]:
        accumulated: dict[str, str] = {}
        for level_params in match.per_level_params[: depth + 1]:
            accumulated.update(level_params)
        return accumulated

    def _ancestor_will_remount(self, match: RouteMatch | None) -> bool:
        depth = self._count_router_view_ancestors()
        if depth == 0:
            return False
        if match is None:
            return True
        ancestor = getattr(self, "_parent", None)
        ancestor_depth = depth - 1
        while ancestor is not None and ancestor_depth >= 0:
            if isinstance(ancestor, RouterView):
                if ancestor_depth >= len(match.chain):
                    return True
                new_identity = ancestor._build_identity(match, ancestor_depth)
                if ancestor._mounted_identity is None or ancestor._mounted_identity != new_identity:
                    return True
                ancestor_depth -= 1
            ancestor = getattr(ancestor, "_parent", None)
        return False

    def _get_or_create_component(self, match: RouteMatch | None):
        depth = self._count_router_view_ancestors()
        if match is None or depth >= len(match.chain):
            if match is None and depth == 0:
                return self._get_or_create_default_component(depth)
            if self._mounted_component is not None:
                self._mounted_component._remove_element()
                self._mounted_component = None
                self._mounted_identity = None
                self._mounted_depth = None
            return None

        identity = self._build_identity(match, depth)
        if self._mounted_component is not None and identity == self._mounted_identity:
            return self._mounted_component

        if self._mounted_component is not None:
            self._mounted_component._remove_element()
        boundary = self._create_level_boundary(lambda: self._create_level_component(match, depth))
        self._mounted_component = boundary
        self._mounted_identity = identity
        self._mounted_depth = depth
        return boundary

    def _create_level_component(self, match: RouteMatch, depth: int) -> ElementChildren:
        node = match.chain[depth]
        context = TypedRouterContext.__create_instance__(
            path=match.path,
            query_params=match.query,
            path_params=self._accumulate_params(match, depth),
            state=match.state,
        )
        return node.component(context)

    def _create_level_boundary(self, generator: Callable[[], ElementChildren]) -> ErrorBoundaryElement:
        return ErrorBoundaryElement(children=generator, fallback=lambda error, reset: None)

    def _get_or_create_default_component(self, depth: int):
        current_path, search = self._router._get_current_path()
        query = self._router._parse_query(search)
        identity = ("__default__", current_path, tuple(sorted(query.items())))
        if self._mounted_component is not None and identity == self._mounted_identity:
            return self._mounted_component
        if self._mounted_component is not None:
            self._mounted_component._remove_element()
        boundary = self._create_level_boundary(self._create_default_component)
        self._mounted_component = boundary
        self._mounted_identity = identity
        self._mounted_depth = depth
        return boundary

    def _create_default_component(self) -> ElementChildren:
        result: ElementChildren = self._router.__default__()
        if isinstance(result, str):
            from webcompy.elements.types._text import TextElement

            return TextElement(result)
        return cast("ElementAbstract", result)

    async def _render(self):
        if not self._signal_activated:
            self._signal_activated = True
            component = self._get_or_create_component(self._level_match.value)
            if component is not None:
                component._parent = self
                component._node_idx = self._node_idx
                self._children = [component]
        await super()._render()

    async def _on_match_changed(self, match: RouteMatch | None):
        self._navigation_generation += 1
        generation = self._navigation_generation
        self._cancel_pending_render_tasks()
        if self._ancestor_will_remount(match):
            return
        old_component = self._mounted_component
        new_component = self._get_or_create_component(match)
        if new_component is old_component:
            return
        if new_component is None:
            self._children = []
            parent_node = self._parent._get_node()
            _position_element_nodes(self, parent_node, self._node_idx)
            self._parent._re_index_children(False)
            return
        new_component._parent = self
        new_component._node_idx = self._node_idx
        self._children = [new_component]

        start_defer_after_rendering()
        try:
            await new_component._render()
        except BaseException:
            end_defer_after_rendering()
            raise
        deferred = end_defer_after_rendering()

        if generation != self._navigation_generation:
            return
        for callback in deferred:
            if iscoroutinefunction(callback):
                from webcompy.aio._aio import aio_run

                callback = lambda cb=callback: aio_run(cb())
            inject(HOST_PORT_KEY).schedule_macro_task(callback)

        parent_node = self._parent._get_node()
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)

    def _on_navigate_attempt(self, _path: str) -> None:
        boundary = self._mounted_component
        if not isinstance(boundary, ErrorBoundaryElement) or not boundary._in_fallback:
            return
        match = self._router.current_match.value
        depth = self._mounted_depth if self._mounted_depth is not None else 0
        if match is not None and depth < len(match.chain):
            if self._build_identity(match, depth) != self._mounted_identity:
                return
        elif not (match is None and depth == 0):
            return
        from webcompy.elements.types._dynamic import _run_refresh_sync

        _run_refresh_sync(self._reset_errored_level, boundary)

    async def _reset_errored_level(self, boundary: ErrorBoundaryElement) -> None:
        self._navigation_generation += 1
        generation = self._navigation_generation
        start_defer_after_rendering()
        try:
            await boundary._do_reset()
        except BaseException:
            end_defer_after_rendering()
            raise
        deferred = end_defer_after_rendering()
        if generation != self._navigation_generation:
            return
        for callback in deferred:
            if iscoroutinefunction(callback):
                from webcompy.aio._aio import aio_run

                callback = lambda cb=callback: aio_run(cb())
            inject(HOST_PORT_KEY).schedule_macro_task(callback)
        parent_node = self._parent._get_node()
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)

    def _remove_element(self, recursive: bool = True, remove_node: bool = True):
        with suppress(ValueError):
            self._router.after_route_change.remove(self._on_navigate_attempt)
        super()._remove_element(recursive, remove_node)

    def _hydrate_node(self):
        self._hydrated = True
        if not self._signal_activated:
            self._signal_activated = True
            component = self._get_or_create_component(self._level_match.value)
            if component is not None:
                component._parent = self
                component._node_idx = self._node_idx
                self._children = [component]
        super()._hydrate_node()
