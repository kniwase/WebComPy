from __future__ import annotations

import contextlib
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from webcompy.aio._stream import _StreamQueue

T = TypeVar("T")

_STOP: Any = object()


class ConnectionState(Enum):
    CONNECTING = "connecting"
    OPEN = "open"
    CLOSED = "closed"


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
        "key",
        "reopening",
        "state",
        "subscribers",
    )

    def __init__(self, key: tuple[str, str]) -> None:
        self.key = key
        self.event_types: set[str] = set()
        self.subscribers: set[_Subscription] = set()
        self.cleanup: Callable[[], None] | None = None
        self.state = ConnectionState.CONNECTING
        self.reopening = False


class _RealtimeRegistry:
    def __init__(self) -> None:
        self._connections: dict[tuple[str, str], _Connection] = {}

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
        def on_open() -> None:
            conn.state = ConnectionState.OPEN
            self._notify_state(conn)

        def on_error() -> None:
            conn.state = ConnectionState.CONNECTING
            self._notify_state(conn)

        def on_close() -> None:
            if conn.reopening:
                return
            conn.state = ConnectionState.CLOSED
            self._notify_state(conn)
            for sub in list(conn.subscribers):
                sub.queue.put_nowait(_STOP)
            if self._connections.get(conn.key) is conn:
                del self._connections[conn.key]

        def on_message(event_type: str, data: str, last_event_id: str) -> None:
            item = item_factory(event_type, data, last_event_id)
            for sub in list(conn.subscribers):
                if event_type in sub.events:
                    sub.queue.put_nowait(item)

        return open_fn(tuple(conn.event_types), on_open, on_message, on_error, on_close)

    def _notify_state(self, conn: _Connection) -> None:
        for sub in list(conn.subscribers):
            sub.on_state(conn.state)
