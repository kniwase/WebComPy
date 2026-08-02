from __future__ import annotations

from inspect import iscoroutinefunction
from typing import Any

from webcompy.components._component import end_defer_after_rendering, start_defer_after_rendering
from webcompy.di import inject
from webcompy.di._exceptions import InjectionError
from webcompy.di._keys import _ROUTER_KEY
from webcompy.elements.types._dynamic import DynamicElement, _position_element_nodes
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, HOST_PORT_KEY
from webcompy.router._context import TypedRouterContext
from webcompy.signal import Computed


class RouterView(DynamicElement):
    _depth: int | None
    _mounted_component: Any
    _mounted_identity: tuple | None
    _signal_activated: bool

    def __init__(self) -> None:
        try:
            router = inject(_ROUTER_KEY)
        except InjectionError:
            raise RuntimeError("'Router' instance is not provided via DI.") from None
        self._router = router
        self._depth = None
        self._mounted_component = None
        self._mounted_identity = None
        self._signal_activated = False
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
        if router._preload:
            router.preload_lazy_routes()

    def _build_identity(self, match, depth: int) -> tuple:
        node = match.chain[depth]
        accumulated = self._accumulate_params(match, depth)
        return (
            id(node),
            tuple(sorted(accumulated.items())),
            tuple(sorted(match.query.items())),
        )

    def _accumulate_params(self, match, depth: int) -> dict[str, str]:
        accumulated: dict[str, str] = {}
        for level_params in match.per_level_params[: depth + 1]:
            accumulated.update(level_params)
        return accumulated

    def _get_or_create_component(self, match):
        depth = self._count_router_view_ancestors()
        self._depth = depth
        if match is None or depth >= len(match.chain):
            if match is None and depth == 0:
                return self._get_or_create_default_component()
            if self._mounted_component is not None:
                self._mounted_component._remove_element()
                self._mounted_component = None
                self._mounted_identity = None
            return None

        identity = self._build_identity(match, depth)
        if self._mounted_component is not None and identity == self._mounted_identity:
            return self._mounted_component

        if self._mounted_component is not None:
            self._mounted_component._remove_element()
        node = match.chain[depth]
        context = TypedRouterContext.__create_instance__(
            path=match.path,
            query_params=match.query,
            path_params=self._accumulate_params(match, depth),
            state=match.state,
        )
        component = node.component(context)
        self._mounted_component = component
        self._mounted_identity = identity
        return component

    def _get_or_create_default_component(self):
        current_path, search = self._router._get_current_path()
        query = self._router._parse_query(search)
        identity = ("__default__", current_path, tuple(sorted(query.items())))
        if self._mounted_component is not None and identity == self._mounted_identity:
            return self._mounted_component
        if self._mounted_component is not None:
            self._mounted_component._remove_element()
        result = self._router.__default__()
        if isinstance(result, str):
            from webcompy.elements.types._text import TextElement

            component = TextElement(result)
        else:
            component = result
        self._mounted_component = component
        self._mounted_identity = identity
        return component

    async def _render(self):
        if not self._signal_activated:
            self._signal_activated = True
            component = self._get_or_create_component(self._level_match.value)
            if component is not None:
                component._parent = self
                component._node_idx = self._node_idx
                self._children = [component]
        await super()._render()

    async def _on_match_changed(self, match):
        self._cancel_pending_render_tasks()
        old_component = self._mounted_component
        new_component = self._get_or_create_component(match)
        if new_component is old_component:
            return
        if new_component is None:
            self._children = []
            return
        new_component._parent = self
        new_component._node_idx = self._node_idx
        self._children = [new_component]

        start_defer_after_rendering()
        await new_component._render()
        deferred = end_defer_after_rendering()
        for callback in deferred:
            if iscoroutinefunction(callback):
                from webcompy.aio._aio import aio_run

                callback = lambda cb=callback: aio_run(cb())
            inject(HOST_PORT_KEY).schedule_macro_task(callback)

        parent_node = self._parent._get_node()
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)

    def _hydrate_node(self):
        self._hydrated = True
        if not self._signal_activated:
            self._signal_activated = True
            component = self._get_or_create_component(self._level_match.value)
            if component is not None:
                component._parent = self
                component._node_idx = self._node_idx
                self._children = [component]
        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            child._hydrate_node()
            idx += child._node_count
            if not child._mounted:
                task = scheduler.schedule(child._render())
                self._pending_render_tasks.append((child, task))
                task.add_done_callback(self._on_hydrate_render_done)
        self._parent._re_index_children(False)
