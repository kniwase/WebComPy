from __future__ import annotations

import dataclasses
import warnings
import weakref
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any, TypeVar, overload

from webcompy.aio._stream import _StreamQueue
from webcompy.di._keys import _REALTIME_CONNECTION_REGISTRY_KEY
from webcompy.di._scope import _get_app_di_scope
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.realtime._registry import (
    _STOP,
    CloseInfo,
    ConnectionState,
    _RealtimeRegistry,
    _ws_send,
)
from webcompy.signal import Signal
from webcompy.utils._environment import ENVIRONMENT

if TYPE_CHECKING:
    from webcompy.realtime._typed import TypedWebSocketHandle

T = TypeVar("T")

_SSR_MSG = "webcompy realtime: use_websocket called outside the browser; returning an empty closed handle"
_NO_SCOPE_MSG = "webcompy realtime: use_websocket called with no app DI scope; returning a private connection"
_NO_PORT_MSG = "webcompy realtime: use_websocket called with no WebSocketPort; returning an empty closed handle"
_CLOSED_SEND_MSG = "webcompy realtime: use_websocket.send called on a closed handle; discarding the message"


class WebSocketHandle:
    def __init__(
        self,
        state: Signal[ConnectionState],
        last_close: Signal[CloseInfo | None],
        queue: _StreamQueue[Any],
        detach: Callable[[], None],
        send: Callable[[str], None],
    ) -> None:
        self._state = state
        self._last_close = last_close
        self._queue = queue
        self._detach = detach
        self._send = send
        self._closed = False
        self._finalizer = weakref.finalize(self, detach)

    @property
    def state(self) -> Signal[ConnectionState]:
        return self._state

    @property
    def last_close(self) -> Signal[CloseInfo | None]:
        return self._last_close

    def send(self, data: str) -> None:
        if self._closed:
            warnings.warn(_CLOSED_SEND_MSG, UserWarning, stacklevel=2)
            return
        self._send(data)

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
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
    protocols: tuple[str, ...],
    *,
    max_queue: int | None,
    port: Any,
    reconnect: bool,
    base_delay: float,
    max_delay: float,
    max_attempts: int | None,
    buffer_while_disconnected: bool,
) -> WebSocketHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CONNECTING)
    last_close: Signal[CloseInfo | None] = Signal(None)
    key_component = (url, tuple(sorted(protocols)))

    def _set_state(value: ConnectionState) -> None:
        state.value = value

    def _set_close_info(value: CloseInfo | None) -> None:
        last_close.value = value

    def _open_fn(**callbacks: Any) -> Any:
        return port.open(url, protocols=protocols, **callbacks)

    sub, conn = registry.subscribe_ws(
        "ws",
        key_component,
        max_queue=max_queue,
        on_state=_set_state,
        on_close_info=_set_close_info,
        open_fn=_open_fn,
        reconnect=reconnect,
        base_delay=base_delay,
        max_delay=max_delay,
        max_attempts=max_attempts,
        buffer_while_disconnected=buffer_while_disconnected,
    )

    def _detach() -> None:
        registry.unsubscribe_ws("ws", key_component, sub)

    handle = WebSocketHandle(state, last_close, sub.queue, _detach, lambda data: _ws_send(conn, data))
    _register_destroy_detach(handle.close)
    return handle


def _build_ssr_handle() -> WebSocketHandle:
    state: Signal[ConnectionState] = Signal(ConnectionState.CLOSED)
    last_close: Signal[CloseInfo | None] = Signal(None)
    queue: _StreamQueue[Any] = _StreamQueue(None)
    queue.put_nowait(_STOP)

    def _detach() -> None:
        pass

    def _send(data: str) -> None:
        warnings.warn(_CLOSED_SEND_MSG, UserWarning, stacklevel=2)

    return WebSocketHandle(state, last_close, queue, _detach, _send)


@overload
def use_websocket(
    url: str,
    *,
    protocols: tuple[str, ...] | None = None,
    max_queue: int | None = None,
    reconnect: bool = True,
    reconnect_base_delay: float = 1.0,
    reconnect_max_delay: float = 30.0,
    reconnect_max_attempts: int | None = None,
    buffer_while_disconnected: bool = False,
    message_type: None = None,
    strict: bool = True,
) -> WebSocketHandle: ...


@overload
def use_websocket(
    url: str,
    *,
    protocols: tuple[str, ...] | None = None,
    max_queue: int | None = None,
    reconnect: bool = True,
    reconnect_base_delay: float = 1.0,
    reconnect_max_delay: float = 30.0,
    reconnect_max_attempts: int | None = None,
    buffer_while_disconnected: bool = False,
    message_type: type[T],
    strict: bool = True,
) -> TypedWebSocketHandle[T]: ...


def use_websocket(
    url: str,
    *,
    protocols: tuple[str, ...] | None = None,
    max_queue: int | None = None,
    reconnect: bool = True,
    reconnect_base_delay: float = 1.0,
    reconnect_max_delay: float = 30.0,
    reconnect_max_attempts: int | None = None,
    buffer_while_disconnected: bool = False,
    message_type: type[T] | None = None,
    strict: bool = True,
) -> WebSocketHandle | TypedWebSocketHandle[T]:
    """Open a WebSocket connection and return its connection handle.

    The handle is an ``AsyncIterator[str]`` yielding every received text
    message in arrival order (occurrence semantics). ``.state`` is a signal
    exposing ``ConnectionState`` (including ``RECONNECTING`` while a dropped
    connection is being re-established); ``.last_close`` is a signal holding
    a ``CloseInfo`` for the most recent close event. ``.send(data)`` sends one
    text frame; while disconnected it warns and discards by default, or
    buffers FIFO (flushed on reopen) when ``buffer_while_disconnected=True``.
    ``.close()`` detaches only the caller's own subscription.

    Subscriptions with the same URL and subprotocols inside one app DI scope
    share a single underlying connection. The first subscriber's reconnection
    parameters apply to the shared connection.

    Outside the browser, a connection is opened only when the resolved
    ``WebSocketPort`` is a real implementation (e.g., a testing fake); with
    the server no-op port (or no port at all) an immediately-finished empty
    handle with ``state == CLOSED`` is returned and a warning is emitted.

    When ``message_type`` is a dataclass type, the handle becomes an
    ``AsyncIterator[T]`` and ``.send()`` accepts instances of ``T``: each text
    frame is a JSON object carrying the payload fields plus the
    ``__webcompy_transfer_meta__`` member (typed-response body wire mode), and
    metadata-typed fields are restored on receive. Frames that fail JSON
    parsing, type-tag validation, or schema reconstruction are skipped and
    surfaced on ``.last_error`` (a ``Signal[Exception | None]``) with a
    warning; the subscription and connection survive. Reconstruction uses
    ``strict=True`` by default (rejecting unknown or missing fields), or
    ``strict=False`` for lenient coercion. Custom types can be registered via
    ``register_realtime_type_handler`` within the app DI scope.
    """
    from webcompy.di import inject
    from webcompy.realtime._typed import TypedWebSocketHandle, _get_or_create_type_registry

    def _wrap(handle: WebSocketHandle) -> WebSocketHandle | TypedWebSocketHandle[T]:
        if message_type is None:
            return handle
        return TypedWebSocketHandle(handle, message_type, strict=strict, registry=_get_or_create_type_registry())

    if isinstance(protocols, str):
        raise TypeError("use_websocket: 'protocols' must be a tuple of strings, not a bare string")
    if protocols is not None and any(not isinstance(p, str) or not p for p in protocols):
        raise TypeError("use_websocket: 'protocols' must contain only non-empty strings")
    if max_queue is not None:
        if isinstance(max_queue, bool) or not isinstance(max_queue, int):
            raise TypeError("use_websocket: 'max_queue' must be an int greater than or equal to 1 or None")
        if max_queue < 1:
            raise ValueError("use_websocket: 'max_queue' must be an int greater than or equal to 1 or None")
    for name, value in (("reconnect_base_delay", reconnect_base_delay), ("reconnect_max_delay", reconnect_max_delay)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"use_websocket: '{name}' must be a number greater than 0")
        if value <= 0:
            raise ValueError(f"use_websocket: '{name}' must be a number greater than 0")
    if reconnect_max_attempts is not None and (
        isinstance(reconnect_max_attempts, bool) or not isinstance(reconnect_max_attempts, int)
    ):
        raise TypeError("use_websocket: 'reconnect_max_attempts' must be an int greater than or equal to 1 or None")
    if reconnect_max_attempts is not None and reconnect_max_attempts < 1:
        raise ValueError("use_websocket: 'reconnect_max_attempts' must be an int greater than or equal to 1 or None")
    if message_type is not None and (not isinstance(message_type, type) or not dataclasses.is_dataclass(message_type)):
        raise TypeError(
            "use_websocket: 'message_type' must be a dataclass type, got "
            f"{getattr(message_type, '__name__', message_type)!r}; typed realtime messages require "
            "a top-level JSON object (typed-response body wire mode)"
        )
    if not isinstance(strict, bool):
        raise TypeError("use_websocket: 'strict' must be a bool")

    protocol_tuple = tuple(protocols or ())

    port = inject(WEBSOCKET_PORT_KEY, default=None)
    if port is None:
        warnings.warn(_NO_PORT_MSG, UserWarning, stacklevel=2)
        return _wrap(_build_ssr_handle())
    if ENVIRONMENT != "pyscript" and getattr(port, "noop", False):
        warnings.warn(_SSR_MSG, UserWarning, stacklevel=2)
        return _wrap(_build_ssr_handle())
    registry = _get_or_create_registry()
    if registry is None:
        warnings.warn(_NO_SCOPE_MSG, UserWarning, stacklevel=2)
        registry = _RealtimeRegistry()
    return _wrap(
        _open_shared(
            registry,
            url,
            protocol_tuple,
            max_queue=max_queue,
            port=port,
            reconnect=reconnect,
            base_delay=reconnect_base_delay,
            max_delay=reconnect_max_delay,
            max_attempts=reconnect_max_attempts,
            buffer_while_disconnected=buffer_while_disconnected,
        )
    )
