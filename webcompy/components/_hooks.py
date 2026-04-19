from __future__ import annotations

from collections.abc import Callable, Coroutine, Iterable
from contextvars import ContextVar
from typing import Any, TypeVar

from webcompy.aio._aio import AsyncWrapper
from webcompy.aio._async_result import AsyncResult
from webcompy.components._libs import Context
from webcompy.di._scope import DIScope
from webcompy.signal._base import CallbackConsumerNode, SignalBase
from webcompy.signal._effect import EffectScope
from webcompy.signal._graph import consumer_destroy

_active_component_context: ContextVar[Context[Any]] = ContextVar("_active_component_context")
_active_effect_scope: ContextVar[EffectScope | None] = ContextVar("_active_effect_scope", default=None)
_active_di_scope: ContextVar[DIScope | None] = ContextVar("_active_di_scope", default=None)

T = TypeVar("T")


def on_before_rendering(func: Callable[[], Any]) -> Callable[[], Any]:
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_before_rendering must be called inside a component setup function") from err
    ctx.on_before_rendering(func)
    return func


def on_after_rendering(func: Callable[[], Any]) -> Callable[[], Any]:
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_after_rendering must be called inside a component setup function") from err
    ctx.on_after_rendering(func)
    return func


def on_before_destroy(func: Callable[[], Any]) -> Callable[[], Any]:
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_before_destroy must be called inside a component setup function") from err
    ctx.on_before_destroy(func)
    return func


def useAsyncResult(
    func: Callable[[], Coroutine[Any, Any, T]],
    *,
    default: T | None = None,
    immediate: bool = True,
    watch: Iterable[SignalBase[Any]] = (),
) -> AsyncResult[T]:
    result = AsyncResult(func, default=default)

    if immediate:
        on_after_rendering(result.refetch)

    watch_nodes: list[CallbackConsumerNode] = []
    for reactive in watch:
        node = reactive.on_after_updating(result.refetch)
        watch_nodes.append(node)

    if watch_nodes:

        def cleanup():
            for node in watch_nodes:
                consumer_destroy(node)

        on_before_destroy(cleanup)

    return result


def useAsync(
    func: Callable[[], Coroutine[Any, Any, Any]],
) -> None:
    wrapped = AsyncWrapper()(func)
    on_after_rendering(wrapped)
