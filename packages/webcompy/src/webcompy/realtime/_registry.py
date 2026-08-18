from __future__ import annotations

import asyncio
import contextlib
import random
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from webcompy.aio._aio import aio_run
from webcompy.aio._stream import _StreamQueue

T = TypeVar("T")

_STOP: Any = object()


class ConnectionState(Enum):
    CONNECTING = "connecting"
    OPEN = "open"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"


@dataclass(frozen=True)
class CloseInfo:
    code: int
    reason: str
    was_clean: bool


_WS_BINARY_MSG = "webcompy realtime: received a binary WebSocket frame; ignoring it"
_WS_RETRY_OPEN_FAILED_MSG = (
    "webcompy realtime: use_websocket reconnection attempt failed to open; "
    "scheduling another attempt or closing per reconnect_max_attempts"
)


class _Subscription:
    __slots__ = ("events", "on_state", "queue")

    def __init__(
        self,
        events: frozenset[str],
        queue: _StreamQueue[Any],
        on_state: Callable[[ConnectionState], None],
    ) -> None:
        self.events = events
        self.queue = queue
        self.on_state = on_state


class _Connection:
    __slots__ = (
        "cleanup",
        "event_types",
        "generation",
        "key",
        "reopening",
        "state",
        "subscribers",
    )

    def __init__(self, key: tuple[str, str]) -> None:
        self.key = key
        self.event_types: set[str] = set()
        self.generation = 0
        self.subscribers: set[_Subscription] = set()
        self.cleanup: Callable[[], None] | None = None
        self.state = ConnectionState.CONNECTING
        self.reopening = False


class _RealtimeRegistry:
    def __init__(self) -> None:
        self._connections: dict[tuple[str, Any], Any] = {}

    def subscribe(
        self,
        transport: str,
        url: str,
        *,
        events: tuple[str, ...],
        max_queue: int | None,
        item_factory: Callable[[str, str, str], T],
        open_fn: Callable[
            [
                tuple[str, ...],
                Callable[[], None],
                Callable[[str, str, str], None],
                Callable[[], None],
                Callable[[], None],
            ],
            Callable[[], None],
        ],
        on_state: Callable[[ConnectionState], None],
    ) -> _Subscription:
        key = (transport, url)
        requested = frozenset(events)
        conn = self._connections.get(key)
        if conn is None:
            conn = _Connection(key)
            self._connections[key] = conn
            conn.event_types = set(requested)
            try:
                conn.cleanup = self._open(conn, open_fn, item_factory)
            except Exception:
                del self._connections[key]
                raise
        elif not requested <= conn.event_types:
            conn.event_types |= requested
            conn.reopening = True
            try:
                try:
                    if conn.cleanup is not None:
                        conn.cleanup()
                finally:
                    conn.reopening = False
                conn.state = ConnectionState.CONNECTING
                self._notify_state(conn)
                conn.cleanup = self._open(conn, open_fn, item_factory)
            except Exception:
                del self._connections[key]
                conn.state = ConnectionState.CLOSED
                self._notify_state(conn)
                for sub in list(conn.subscribers):
                    sub.queue.put_nowait(_STOP)
                raise
        sub = _Subscription(requested, _StreamQueue(max_queue), on_state)
        conn.subscribers.add(sub)
        sub.on_state(conn.state)
        return sub

    def unsubscribe(self, transport: str, url: str, sub: _Subscription) -> None:
        conn = self._connections.get((transport, url))
        if conn is None:
            return
        conn.subscribers.discard(sub)
        if conn.subscribers:
            return
        if self._connections.get(conn.key) is conn:
            del self._connections[conn.key]
        conn.state = ConnectionState.CLOSED
        if conn.cleanup is not None:
            conn.cleanup()

    def dispose(self) -> None:
        connections = list(self._connections.values())
        self._connections.clear()
        for conn in connections:
            if isinstance(conn, _WSConnection):
                self._terminate_ws(conn)
                continue
            conn.state = ConnectionState.CLOSED
            self._notify_state(conn)
            for sub in list(conn.subscribers):
                sub.queue.put_nowait(_STOP)
            if conn.cleanup is not None:
                conn.cleanup()

    def __del__(self) -> None:
        with contextlib.suppress(Exception):
            self.dispose()

    def _open(
        self,
        conn: _Connection,
        open_fn: Callable[
            [
                tuple[str, ...],
                Callable[[], None],
                Callable[[str, str, str], None],
                Callable[[], None],
                Callable[[], None],
            ],
            Callable[[], None],
        ],
        item_factory: Callable[[str, str, str], T],
    ) -> Callable[[], None]:
        conn.generation += 1
        gen = conn.generation

        def _is_stale() -> bool:
            return gen != conn.generation

        def on_open() -> None:
            if _is_stale():
                return
            conn.state = ConnectionState.OPEN
            self._notify_state(conn)

        def on_error() -> None:
            if _is_stale():
                return
            conn.state = ConnectionState.CONNECTING
            self._notify_state(conn)

        def on_close() -> None:
            if _is_stale() or conn.reopening:
                return
            conn.state = ConnectionState.CLOSED
            self._notify_state(conn)
            for sub in list(conn.subscribers):
                sub.queue.put_nowait(_STOP)
            if self._connections.get(conn.key) is conn:
                del self._connections[conn.key]

        def on_message(event_type: str, data: str, last_event_id: str) -> None:
            if _is_stale():
                return
            item = item_factory(event_type, data, last_event_id)
            for sub in list(conn.subscribers):
                if event_type in sub.events:
                    sub.queue.put_nowait(item)

        return open_fn(tuple(conn.event_types), on_open, on_message, on_error, on_close)

    def _notify_state(self, conn: _Connection | _WSConnection) -> None:
        for sub in list(conn.subscribers):
            sub.on_state(conn.state)

    def subscribe_ws(
        self,
        transport: str,
        key_component: Any,
        *,
        max_queue: int | None,
        on_state: Callable[[ConnectionState], None],
        on_close_info: Callable[[CloseInfo | None], None],
        open_fn: Callable[..., Any],
        reconnect: bool,
        base_delay: float,
        max_delay: float,
        max_attempts: int | None,
        buffer_while_disconnected: bool,
    ) -> tuple[_WSSubscription, _WSConnection]:
        key = (transport, key_component)
        conn = self._connections.get(key)
        if conn is None or not isinstance(conn, _WSConnection):
            conn = _WSConnection(
                key,
                open_fn=open_fn,
                reconnect=reconnect,
                base_delay=base_delay,
                max_delay=max_delay,
                max_attempts=max_attempts,
                buffer_while_disconnected=buffer_while_disconnected,
            )
            self._connections[key] = conn
            try:
                self._ws_open(conn)
            except Exception:
                del self._connections[key]
                conn.terminated = True
                raise
        else:
            _warn_on_reconnect_param_mismatch_ws(
                conn,
                reconnect,
                base_delay,
                max_delay,
                max_attempts,
                buffer_while_disconnected,
            )
        sub = _WSSubscription(_StreamQueue(max_queue), on_state, on_close_info)
        conn.subscribers.add(sub)
        sub.on_state(conn.state)
        sub.on_close_info(conn.last_close)
        return sub, conn

    def unsubscribe_ws(self, transport: str, key_component: Any, sub: _WSSubscription) -> None:
        key = (transport, key_component)
        conn = self._connections.get(key)
        if conn is None or not isinstance(conn, _WSConnection):
            return
        conn.subscribers.discard(sub)
        if conn.subscribers:
            return
        if self._connections.get(conn.key) is conn:
            del self._connections[conn.key]
        self._terminate_ws(conn)

    def _ws_open(self, conn: _WSConnection) -> None:
        conn.generation += 1
        gen = conn.generation

        def _is_stale() -> bool:
            return conn.terminated or gen != conn.generation

        def on_open() -> None:
            if _is_stale():
                return
            conn.state = ConnectionState.OPEN
            conn.attempts = 0
            self._notify_state(conn)
            if conn.send_buffer:
                for data in conn.send_buffer:
                    if conn.connection is not None:
                        conn.connection.send(data)
                conn.send_buffer = []

        def on_message(text: str) -> None:
            if _is_stale():
                return
            for sub in list(conn.subscribers):
                sub.queue.put_nowait(text)

        def on_binary() -> None:
            if _is_stale():
                return
            warnings.warn(_WS_BINARY_MSG, UserWarning, stacklevel=2)

        def on_error() -> None:
            if _is_stale():
                return

        def on_close(code: int, reason: str, was_clean: bool) -> None:
            if _is_stale():
                return
            conn.last_close = CloseInfo(code, reason, was_clean)
            old_connection = conn.connection
            conn.connection = None
            if old_connection is not None:
                old_connection.close()
            for sub in list(conn.subscribers):
                sub.on_close_info(conn.last_close)
            if self._should_stop_ws(conn, code):
                self._terminate_ws(conn)
                if self._connections.get(conn.key) is conn:
                    del self._connections[conn.key]
                return
            conn.attempts += 1
            conn.state = ConnectionState.RECONNECTING
            self._notify_state(conn)
            self._schedule_retry_ws(conn)

        conn.connection = conn.open_fn(
            on_open=on_open,
            on_message=on_message,
            on_binary=on_binary,
            on_error=on_error,
            on_close=on_close,
        )

    def _should_stop_ws(self, conn: _WSConnection, code: int) -> bool:
        return (
            not conn.reconnect or code == 1000 or (conn.max_attempts is not None and conn.attempts >= conn.max_attempts)
        )

    def _schedule_retry_ws(self, conn: _WSConnection) -> None:
        conn.retry_token += 1
        token = conn.retry_token
        delay = _compute_reconnect_delay(conn.attempts, conn.base_delay, conn.max_delay)

        async def _retry() -> None:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
            if conn.terminated or token != conn.retry_token:
                return
            if self._connections.get(conn.key) is not conn:
                return
            try:
                self._ws_open(conn)
            except Exception:
                warnings.warn(_WS_RETRY_OPEN_FAILED_MSG, UserWarning, stacklevel=2)
                if conn.terminated:
                    return
                conn.attempts += 1
                if conn.max_attempts is not None and conn.attempts >= conn.max_attempts:
                    self._terminate_ws(conn)
                    if self._connections.get(conn.key) is conn:
                        del self._connections[conn.key]
                    return
                self._schedule_retry_ws(conn)

        aio_run(_retry())

    def _terminate_ws(self, conn: _WSConnection) -> None:
        conn.terminated = True
        conn.retry_token += 1
        conn.state = ConnectionState.CLOSED
        self._notify_state(conn)
        for sub in list(conn.subscribers):
            sub.queue.put_nowait(_STOP)
        if conn.connection is not None:
            conn.connection.close()
            conn.connection = None
        conn.send_buffer = []

    def _ws_abort(self, conn: _WSConnection, code: int, reason: str) -> None:
        """Force an abnormal close that engages the reconnect loop.

        Records a synthetic ``CloseInfo``, closes the underlying socket, and
        bumps the generation so any stale lifecycle event from the old socket
        (e.g. the browser's own close event with code 1000) is ignored. The
        connection is kept in the registry and a retry is scheduled.
        """
        if conn.terminated or conn.state is ConnectionState.CLOSED:
            return
        conn.last_close = CloseInfo(code, reason, False)
        old_connection = conn.connection
        conn.connection = None
        conn.generation += 1
        if old_connection is not None:
            old_connection.close()
        for sub in list(conn.subscribers):
            sub.on_close_info(conn.last_close)
        if not conn.reconnect or (conn.max_attempts is not None and conn.attempts >= conn.max_attempts):
            self._terminate_ws(conn)
            if self._connections.get(conn.key) is conn:
                del self._connections[conn.key]
            return
        conn.attempts += 1
        conn.state = ConnectionState.RECONNECTING
        self._notify_state(conn)
        self._schedule_retry_ws(conn)


class _WSSubscription:
    __slots__ = ("on_close_info", "on_state", "queue")

    def __init__(
        self,
        queue: _StreamQueue[Any],
        on_state: Callable[[ConnectionState], None],
        on_close_info: Callable[[CloseInfo | None], None],
    ) -> None:
        self.queue = queue
        self.on_state = on_state
        self.on_close_info = on_close_info


class _WSConnection:
    __slots__ = (
        "attempts",
        "base_delay",
        "buffer_while_disconnected",
        "connection",
        "generation",
        "key",
        "last_close",
        "max_attempts",
        "max_delay",
        "open_fn",
        "reconnect",
        "retry_token",
        "send_buffer",
        "state",
        "subscribers",
        "terminated",
    )

    def __init__(
        self,
        key: tuple[str, Any],
        *,
        open_fn: Callable[..., Any],
        reconnect: bool,
        base_delay: float,
        max_delay: float,
        max_attempts: int | None,
        buffer_while_disconnected: bool,
    ) -> None:
        self.key = key
        self.open_fn = open_fn
        self.reconnect = reconnect
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.buffer_while_disconnected = buffer_while_disconnected
        self.subscribers: set[_WSSubscription] = set()
        self.state = ConnectionState.CONNECTING
        self.last_close: CloseInfo | None = None
        self.connection: Any = None
        self.generation = 0
        self.attempts = 0
        self.retry_token = 0
        self.send_buffer: list[str] = []
        self.terminated = False


def _compute_reconnect_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Delay before reconnect attempt ``attempt`` (1-based).

    The backoff is ``min(max_delay, base_delay * 2 ** (attempt - 1))``
    multiplied by a uniform random jitter factor in ``[0.5, 1.0]``.
    """
    backoff = min(max_delay, base_delay * (2 ** (attempt - 1)))
    return backoff * random.uniform(0.5, 1.0)


def _ws_send(conn: _WSConnection, data: str) -> None:
    if conn.terminated or conn.state is ConnectionState.CLOSED:
        warnings.warn(
            "webcompy realtime: use_websocket.send called while the connection is closed; discarding the message",
            UserWarning,
            stacklevel=2,
        )
        return
    if conn.state is ConnectionState.OPEN:
        if conn.connection is not None:
            conn.connection.send(data)
        return
    if conn.buffer_while_disconnected:
        conn.send_buffer.append(data)
    else:
        warnings.warn(
            "webcompy realtime: use_websocket.send called while the connection is not open; discarding the message",
            UserWarning,
            stacklevel=2,
        )


def _warn_on_reconnect_param_mismatch_ws(
    conn: _WSConnection,
    reconnect: bool,
    base_delay: float,
    max_delay: float,
    max_attempts: int | None,
    buffer_while_disconnected: bool,
) -> None:
    mismatched: list[str] = []
    if reconnect != conn.reconnect:
        mismatched.append("reconnect")
    if base_delay != conn.base_delay:
        mismatched.append("reconnect_base_delay")
    if max_delay != conn.max_delay:
        mismatched.append("reconnect_max_delay")
    if max_attempts != conn.max_attempts:
        mismatched.append("reconnect_max_attempts")
    if buffer_while_disconnected != conn.buffer_while_disconnected:
        mismatched.append("buffer_while_disconnected")
    if mismatched:
        warnings.warn(
            "webcompy realtime: use_websocket subscribed to a shared connection with different "
            f"reconnection parameter(s): {', '.join(mismatched)}; the existing connection's "
            "parameters apply",
            UserWarning,
            stacklevel=3,
        )
