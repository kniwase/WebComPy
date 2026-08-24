"""Lifecycle hooks and async helpers callable inside component setup functions."""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Iterable
from contextvars import ContextVar
from typing import Any, TypeVar

from webcompy.aio._aio import AsyncWrapper
from webcompy.aio._async_result import AsyncResult
from webcompy.components._libs import Context, generate_id
from webcompy.di import inject
from webcompy.di._keys import HYDRATION_DATA_KEY
from webcompy.hydration._payload import TransferAsyncResultEntry
from webcompy.signal import SignalBase
from webcompy.signal._base import CallbackConsumerNode
from webcompy.signal._graph import consumer_destroy

_active_component_context: ContextVar[Context[Any]] = ContextVar("_active_component_context")

T = TypeVar("T")


def on_before_rendering(func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> Callable[[], Any]:
    """Register a hook invoked before the component renders.

    Args:
        func: Hook callback; may be a coroutine function.

    Returns:
        The registered callback.

    Raises:
        LookupError: If called outside a component setup function.

    """
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_before_rendering must be called inside a component setup function") from err
    ctx.on_before_rendering(func)
    return func


def on_after_rendering(func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> Callable[[], Any]:
    """Register a hook invoked after the component renders.

    Args:
        func: Hook callback; may be a coroutine function.

    Returns:
        The registered callback.

    Raises:
        LookupError: If called outside a component setup function.

    """
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_after_rendering must be called inside a component setup function") from err
    ctx.on_after_rendering(func)
    return func


def on_before_destroy(func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> Callable[[], Any]:
    """Register a hook invoked before the component is destroyed.

    Args:
        func: Hook callback; may be a coroutine function.

    Returns:
        The registered callback.

    Raises:
        LookupError: If called outside a component setup function.

    """
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_before_destroy must be called inside a component setup function") from err
    ctx.on_before_destroy(func)
    return func


def _register_before_destroy_chained(cleanup: Callable[[], None]) -> None:
    """Register ``cleanup`` on ``on_before_destroy``, chaining with any existing hook.

    Composable helpers call this so their cleanup runs before a user-registered
    ``on_before_destroy`` hook. Outside component setup this is a no-op.
    """
    try:
        ctx = _active_component_context.get()
    except LookupError:
        return
    previous = ctx.__get_lifecyclehooks__().get("on_before_destroy")
    if previous is None:
        ctx.on_before_destroy(cleanup)
        return

    def _combined() -> None:
        cleanup()
        previous()

    ctx.on_before_destroy(_combined)


def on_mounted(func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> Callable[[], Any]:
    """Register a hook invoked when the component's node enters the DOM.

    Args:
        func: Hook callback; may be a coroutine function.

    Returns:
        The registered callback.

    Raises:
        LookupError: If called outside a component setup function.

    """
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_mounted must be called inside a component setup function") from err
    ctx.on_mounted(func)
    return func


def on_unmounted(func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> Callable[[], Any]:
    """Register a hook invoked when the component's node leaves the DOM.

    Args:
        func: Hook callback; may be a coroutine function.

    Returns:
        The registered callback.

    Raises:
        LookupError: If called outside a component setup function.

    """
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_unmounted must be called inside a component setup function") from err
    ctx.on_unmounted(func)
    return func


def on_error_captured(func: Callable[[Exception], Any]) -> Callable[[Exception], Any]:
    """Register a hook invoked when a descendant error is captured.

    Args:
        func: Hook callback receiving the raised exception.

    Returns:
        The registered callback.

    Raises:
        LookupError: If called outside a component setup function.

    """
    try:
        ctx = _active_component_context.get()
    except LookupError as err:
        raise LookupError("on_error_captured must be called inside a component setup function") from err
    ctx.on_error_captured(func)
    return func


def use_async_result(
    func: Callable[[], Coroutine[Any, Any, T]],
    *,
    default: T | None = None,
    immediate: bool = True,
    watch: Iterable[SignalBase[Any]] = (),
    transfer: bool = True,
) -> AsyncResult[T]:
    """Expose an async operation's state as an ``AsyncResult``.

    Called inside a component setup function, the result is registered
    with the component so its state can be transferred from SSR. Unless
    ``immediate`` is ``False``, the operation starts right after the
    first render; listed ``watch`` signals refetch whenever they change.

    Args:
        func: Async operation factory; run without arguments.
        default: Value exposed while the operation is pending.
        immediate: Whether to start the operation after first render.
        watch: Signals that trigger a refetch upon change.
        transfer: Whether the result state transfers from SSR.

    Returns:
        The ``AsyncResult`` tracking the operation's lifecycle.

    """
    result = AsyncResult(func, default=default)
    result._transferable = transfer

    try:
        ctx = _active_component_context.get()
    except LookupError:
        ctx = None

    if ctx is not None:
        ctx._async_results.append(result)
        from webcompy.components._component import _is_hydration_payload_open

        hydration_data = inject(HYDRATION_DATA_KEY, default=None)
        if hydration_data is not None and _is_hydration_payload_open():
            component_id = getattr(ctx, "_transfer_id", None) or generate_id(ctx._component_name)
            if component_id in hydration_data:
                entry = hydration_data[component_id]
                if isinstance(entry, TransferAsyncResultEntry) and entry.state == "success":
                    result._restore_from_transfer(entry.data)
                    return result

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


def use_async(
    func: Callable[[], Coroutine[Any, Any, Any]],
) -> None:
    """Run an async operation after every component render.

    The wrapped operation is executed after each rendering; results are
    fire-and-forget. Use ``use_async_result()`` when the pending/error
    state must be observable.

    Args:
        func: Async operation factory; run without arguments.

    """
    wrapped = AsyncWrapper()(func)
    on_after_rendering(wrapped)
