"""Server-Sent Events composable and its connection handles."""

from __future__ import annotations

import asyncio
import warnings
import weakref
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from webcompy import logging
from webcompy.aio._stream import _StreamQueue
from webcompy.ajax._sse import _SSEParser
from webcompy.di._keys import _REALTIME_CONNECTION_REGISTRY_KEY
from webcompy.di._scope import _get_app_di_scope
from webcompy.ports._keys import EVENT_SOURCE_PORT_KEY, FETCH_PORT_KEY
from webcompy.realtime._registry import (
    _STOP,
    ConnectionState,
    _compute_reconnect_delay,
    _RealtimeRegistry,
)
from webcompy.signal import Signal
from webcompy.utils._environment import ENVIRONMENT

_SSR_MSG = "webcompy realtime: use_event_source called outside the browser; returning an empty closed handle"
_NO_SCOPE_MSG = "webcompy realtime: use_event_source called with no app DI scope; returning a private connection"
_NO_PORT_MSG = "webcompy realtime: use_event_source called with no EventSourcePort; returning an empty closed handle"
_NO_FETCH_PORT_MSG = "webcompy realtime: use_event_source called with no FetchPort; returning an empty closed handle"

_FETCH_RECONNECT_BASE_DELAY = 1.0
_FETCH_RECONNECT_MAX_DELAY = 30.0


def _headers_key(headers: dict[str, str] | None) -> frozenset[tuple[str, str]]:
    """Canonical form of request headers for connection registry keying.

    Header names are lower-cased so equivalent headers spelled differently
    (e.g. ``Content-Type`` vs ``content-type``) key identically, and ``None``
    and ``{}`` both normalize to the empty set.
    """
    return frozenset((name.lower(), value) for name, value in (headers or {}).items())


@dataclass(frozen=True)
class SSEvent:
    """A parsed Server-Sent Event.

    Args:
        event: The event type (defaults to ``"message"``).
        data: The event payload.
        last_event_id: The ``id`` value persisted by the stream.

    Attributes:
        event: The event type (defaults to ``"message"``).
        data: The event payload.
        last_event_id: The ``id`` value persisted by the stream.

    """

    event: str
    data: str
    last_event_id: str


class EventSourceHandle:
    """Async iterator and connection handle for a Server-Sent Events subscription.

    Iterating yields :class:`SSEvent` occurrences in arrival order.
    ``close()`` detaches only this handle's subscription.

    Args:
        state: Signal exposing the shared connection state.
        queue: Per-subscription queue of parsed events.
        detach: Callback releasing this handle's subscription.

    Attributes:
        state: Signal exposing the :class:`ConnectionState` of the
            shared connection.

    """

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
        """The state of the underlying connection.

        Returns:
            A signal exposing :class:`ConnectionState`.

        """
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
        """Detach this subscription and stop iteration.

        Idempotent: closing an already closed handle is a no-op.
        """
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


def _is_event_stream(headers: dict[str, str]) -> bool:
    content_type = next((value for key, value in headers.items() if key.lower() == "content-type"), "")
    return content_type.split(";")[0].strip().lower() == "text/event-stream"


def _schedule_pump(coro: Coroutine[Any, Any, Any]) -> Any:
    from webcompy.aio._aio import _aio_run_task

    task = _aio_run_task(coro)
    if task is None:
        raise RuntimeError("webcompy realtime: cannot schedule the fetch SSE pump without a running event loop")
    return task


def _open_fetch(
    fetch_port: Any,
    url: str,
    *,
    method: str,
    body: str | None,
    headers: dict[str, str] | None,
    on_open: Callable[[], None],
    on_message: Callable[[str, str, str], None],
    on_error: Callable[[], None],
    on_close: Callable[[], None],
) -> Callable[[], None]:
    async def _pump() -> None:
        attempt = 0
        last_event_id = ""
        while True:
            try:
                req_headers = dict(headers or {})
                if last_event_id:
                    req_headers["Last-Event-ID"] = last_event_id
                stream = await fetch_port.stream(url, method=method, headers=req_headers, body=body)
                try:
                    if not stream.ok or not _is_event_stream(stream.headers):
                        raise Exception("SSE handshake failed")
                    on_open()
                    attempt = 0
                    parser = _SSEParser()
                    async for chunk in stream:
                        for event in parser.feed(chunk):
                            if event.last_event_id:
                                last_event_id = event.last_event_id
                            on_message(event.event_type, event.data, event.last_event_id)
                finally:
                    stream.close()
            except asyncio.CancelledError:
                return
            except Exception:
                logging.debug(
                    f"webcompy realtime: fetch SSE connection to {url} failed; retrying (attempt {attempt + 1})"
                )
            on_error()
            attempt += 1
            delay = _compute_reconnect_delay(attempt, _FETCH_RECONNECT_BASE_DELAY, _FETCH_RECONNECT_MAX_DELAY)
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

    task = _schedule_pump(_pump())

    def _cleanup() -> None:
        task.cancel()
        on_close()

    return _cleanup


def _open_shared_fetch(
    registry: _RealtimeRegistry,
    url: str,
    *,
    method: str,
    body: str | None,
    headers: dict[str, str] | None,
    events: tuple[str, ...],
    max_queue: int | None,
    fetch_port: Any,
) -> EventSourceHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CONNECTING)
    key_component = (url, method, body, _headers_key(headers))

    def _set_state(value: ConnectionState) -> None:
        state.value = value

    def _open_fn(
        event_types: tuple[str, ...],
        on_open: Callable[[], None],
        on_message: Callable[[str, str, str], None],
        on_error: Callable[[], None],
        on_close: Callable[[], None],
    ) -> Callable[[], None]:
        return _open_fetch(
            fetch_port,
            url,
            method=method,
            body=body,
            headers=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

    sub = registry.subscribe(
        "sse",
        key_component,
        events=events,
        max_queue=max_queue,
        item_factory=SSEvent,
        open_fn=_open_fn,
        on_state=_set_state,
        reopen_on_new_types=False,
        on_error_state=ConnectionState.RECONNECTING,
    )

    def _detach() -> None:
        registry.unsubscribe("sse", key_component, sub)

    handle = EventSourceHandle(state, sub.queue, _detach)
    _register_destroy_detach(handle.close)
    return handle


def _open_private_fetch(
    url: str,
    *,
    method: str,
    body: str | None,
    headers: dict[str, str] | None,
    events: tuple[str, ...],
    max_queue: int | None,
    fetch_port: Any,
) -> EventSourceHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CONNECTING)
    queue: _StreamQueue[Any] = _StreamQueue(max_queue)
    events_set = frozenset(events)
    done = False

    def _on_open() -> None:
        state.value = ConnectionState.OPEN

    def _on_error() -> None:
        state.value = ConnectionState.RECONNECTING

    def _on_close() -> None:
        state.value = ConnectionState.CLOSED
        queue.put_nowait(_STOP)

    def _on_message(event_type: str, data: str, last_event_id: str) -> None:
        if event_type in events_set:
            queue.put_nowait(SSEvent(event_type, data, last_event_id))

    cleanup = _open_fetch(
        fetch_port,
        url,
        method=method,
        body=body,
        headers=headers,
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


def use_event_source(
    url: str,
    *,
    events: tuple[str, ...] = ("message",),
    max_queue: int | None = None,
    method: str = "GET",
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> EventSourceHandle:
    """Open a Server-Sent Events connection and return its connection handle.

    The handle is an ``AsyncIterator[SSEvent]`` yielding every received event
    in arrival order (occurrence semantics). ``.state`` is a signal exposing
    ``ConnectionState``; ``.close()`` detaches only the caller's own
    subscription. Subscriptions with the same URL inside one app DI scope share
    a single underlying connection; a later subscriber requesting event types
    not yet registered reopens the shared connection with the union of types.

    With the default ``method="GET"`` the connection is opened through the
    browser-native ``EventSource`` API. Any other non-empty ``method`` opens
    a fetch-based connection through the framework's streaming fetch
    capability, sending ``body`` as the request body and ``headers`` as
    request headers. Fetch-based connections are keyed by
    ``(url, method, body, normalized headers)`` and filter event types per
    subscriber without reopening.

    Outside the browser, a connection is opened only when the resolved
    ``EventSourcePort`` (GET) or ``FetchPort`` (non-GET) is a real
    implementation (e.g., a testing fake); with the server no-op port (or no
    port at all) an immediately-finished empty handle with
    ``state == CLOSED`` is returned and a warning is emitted.

    Args:
        url: Endpoint URL of the event stream.
        events: Event types to subscribe to. Defaults to ``("message",)``.
        max_queue: Optional bound on the per-subscription event queue.
        method: HTTP method used to open the connection; anything other than
            ``"GET"`` selects the fetch-based transport.
        body: Request body for fetch-based connections.
        headers: Request headers for fetch-based connections.

    Returns:
        An :class:`EventSourceHandle` yielding received events.

    Raises:
        TypeError: If ``events``, ``max_queue``, or ``method`` has an
            invalid type, or if an event type is empty.
        ValueError: If ``events`` is empty, ``max_queue`` is less than 1,
            or ``body``/``headers`` are supplied with ``method="GET"``.

    """
    from webcompy.di import inject

    if isinstance(events, str):
        raise TypeError("use_event_source: 'events' must be a tuple of strings, not a bare string")
    if not events:
        raise ValueError("use_event_source: 'events' must contain at least one event type")
    if any(not isinstance(event_type, str) or not event_type for event_type in events):
        raise TypeError("use_event_source: 'events' must contain only non-empty strings")
    if max_queue is not None:
        if isinstance(max_queue, bool) or not isinstance(max_queue, int):
            raise TypeError("use_event_source: 'max_queue' must be an int greater than or equal to 1 or None")
        if max_queue < 1:
            raise ValueError("use_event_source: 'max_queue' must be an int greater than or equal to 1 or None")
    if not isinstance(method, str) or not method:
        raise TypeError("use_event_source: 'method' must be a non-empty string")
    if method == "GET" and (body is not None or headers is not None):
        raise ValueError("use_event_source: 'body' and 'headers' are only valid with non-GET methods")

    if method == "GET":
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

    fetch_port = inject(FETCH_PORT_KEY, default=None)
    if fetch_port is None:
        warnings.warn(_NO_FETCH_PORT_MSG, UserWarning, stacklevel=2)
        return _build_ssr_handle()
    if ENVIRONMENT != "pyscript" and getattr(fetch_port, "noop", False):
        warnings.warn(_SSR_MSG, UserWarning, stacklevel=2)
        return _build_ssr_handle()
    registry = _get_or_create_registry()
    if registry is None:
        warnings.warn(_NO_SCOPE_MSG, UserWarning, stacklevel=2)
        return _open_private_fetch(
            url,
            method=method,
            body=body,
            headers=headers,
            events=events,
            max_queue=max_queue,
            fetch_port=fetch_port,
        )
    return _open_shared_fetch(
        registry,
        url,
        method=method,
        body=body,
        headers=headers,
        events=events,
        max_queue=max_queue,
        fetch_port=fetch_port,
    )
