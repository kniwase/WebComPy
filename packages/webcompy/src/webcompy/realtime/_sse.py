from __future__ import annotations

import warnings
import weakref
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from webcompy.aio._stream import _StreamQueue
from webcompy.di._keys import _REALTIME_CONNECTION_REGISTRY_KEY
from webcompy.di._scope import _get_app_di_scope
from webcompy.ports._keys import EVENT_SOURCE_PORT_KEY
from webcompy.realtime._registry import (
    _STOP,
    ConnectionState,
    _RealtimeRegistry,
)
from webcompy.signal import Signal
from webcompy.utils._environment import ENVIRONMENT

_SSR_MSG = "webcompy realtime: use_event_source called outside the browser; returning an empty closed handle"
_NO_SCOPE_MSG = "webcompy realtime: use_event_source called with no app DI scope; returning a private connection"
_NO_PORT_MSG = "webcompy realtime: use_event_source called with no EventSourcePort; returning an empty closed handle"


@dataclass(frozen=True)
class SSEvent:
    event: str
    data: str
    last_event_id: str


class EventSourceHandle:
    def __init__(
        self,
        state: Signal[ConnectionState],
        queue: _StreamQueue[Any],
        detach: Callable[[], None],
    ) -> None:
        self._state = state
        self._queue = queue
        self._detach = detach
        self._closed = False
        self._finalizer = weakref.finalize(self, detach)

    @property
    def state(self) -> Signal[ConnectionState]:
        return self._state

    def __aiter__(self) -> AsyncIterator[SSEvent]:
        return self

    async def __anext__(self) -> SSEvent:
        if self._closed:
            raise StopAsyncIteration
        item = await self._queue.get()
        if item is _STOP or self._closed:
            self._closed = True
            raise StopAsyncIteration
        return item

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._detach()
        self._state.value = ConnectionState.CLOSED
        self._queue.put_nowait(_STOP)


def _get_or_create_registry() -> _RealtimeRegistry | None:
    scope = _get_app_di_scope()
    if scope is None:
        return None
    existing = scope.inject(_REALTIME_CONNECTION_REGISTRY_KEY, default=None)
    if existing is None:
        existing = _RealtimeRegistry()
        scope.provide(_REALTIME_CONNECTION_REGISTRY_KEY, existing)
    return existing


def _register_destroy_detach(detach: Callable[[], None]) -> None:
    from webcompy.components._hooks import _register_before_destroy_chained

    _register_before_destroy_chained(detach)


def _open_shared(
    registry: _RealtimeRegistry,
    url: str,
    *,
    events: tuple[str, ...],
    max_queue: int | None,
    port: Any,
) -> EventSourceHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CONNECTING)

    def _set_state(value: ConnectionState) -> None:
        state.value = value

    def _open_fn(
        event_types: tuple[str, ...],
        on_open: Callable[[], None],
        on_message: Callable[[str, str, str], None],
        on_error: Callable[[], None],
        on_close: Callable[[], None],
    ) -> Callable[[], None]:
        return port.open(
            url,
            events=event_types,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

    sub = registry.subscribe(
        "sse",
        url,
        events=events,
        max_queue=max_queue,
        item_factory=SSEvent,
        open_fn=_open_fn,
        on_state=_set_state,
    )

    def _detach() -> None:
        registry.unsubscribe("sse", url, sub)

    handle = EventSourceHandle(state, sub.queue, _detach)
    _register_destroy_detach(handle.close)
    return handle


def _open_private(
    url: str,
    *,
    events: tuple[str, ...],
    max_queue: int | None,
    port: Any,
) -> EventSourceHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CONNECTING)
    queue: _StreamQueue[Any] = _StreamQueue(max_queue)
    events_set = frozenset(events)
    done = False

    def _on_open() -> None:
        state.value = ConnectionState.OPEN

    def _on_error() -> None:
        state.value = ConnectionState.CONNECTING

    def _on_close() -> None:
        state.value = ConnectionState.CLOSED
        queue.put_nowait(_STOP)

    def _on_message(event_type: str, data: str, last_event_id: str) -> None:
        if event_type in events_set:
            queue.put_nowait(SSEvent(event_type, data, last_event_id))

    cleanup = port.open(
        url,
        events=tuple(events),
        on_open=_on_open,
        on_message=_on_message,
        on_error=_on_error,
        on_close=_on_close,
    )

    def _detach() -> None:
        nonlocal done
        if done:
            return
        done = True
        cleanup()

    handle = EventSourceHandle(state, queue, _detach)
    _register_destroy_detach(handle.close)
    return handle


def _build_ssr_handle() -> EventSourceHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CLOSED)
    queue: _StreamQueue[Any] = _StreamQueue(None)
    queue.put_nowait(_STOP)

    def _detach() -> None:
        pass

    return EventSourceHandle(state, queue, _detach)


def use_event_source(
    url: str,
    *,
    events: tuple[str, ...] = ("message",),
    max_queue: int | None = None,
) -> EventSourceHandle:
    """Open a Server-Sent Events connection and return its connection handle.

    The handle is an ``AsyncIterator[SSEvent]`` yielding every received event
    in arrival order (occurrence semantics). ``.state`` is a signal exposing
    ``ConnectionState``; ``.close()`` detaches only the caller's own
    subscription.     Subscriptions with the same URL inside one app DI scope share
    a single underlying connection; a later subscriber requesting event types
    not yet registered reopens the shared connection with the union of types.

    Outside the browser, a connection is opened only when the resolved
    ``EventSourcePort`` is a real implementation (e.g., a testing fake); with
    the server no-op port (or no port at all) an immediately-finished empty
    handle with ``state == CLOSED`` is returned and a warning is emitted.
    """
    from webcompy.di import inject

    port = inject(EVENT_SOURCE_PORT_KEY, default=None)
    if port is None:
        warnings.warn(_NO_PORT_MSG, UserWarning, stacklevel=2)
        return _build_ssr_handle()
    if ENVIRONMENT != "pyscript" and getattr(port, "noop", False):
        warnings.warn(_SSR_MSG, UserWarning, stacklevel=2)
        return _build_ssr_handle()
    registry = _get_or_create_registry()
    if registry is None:
        warnings.warn(_NO_SCOPE_MSG, UserWarning, stacklevel=2)
        return _open_private(url, events=events, max_queue=max_queue, port=port)
    return _open_shared(registry, url, events=events, max_queue=max_queue, port=port)
