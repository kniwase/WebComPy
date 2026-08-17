from __future__ import annotations

from collections.abc import Callable

from webcompy.ports._websocket import WebSocketConnection, WebSocketPort


class ServerWebSocketConnection(WebSocketConnection):
    def send(self, data: str) -> None:
        pass

    def close(self) -> None:
        pass


class ServerWebSocketPort(WebSocketPort):
    """Server-side no-op ``WebSocketPort``.

    ``noop = True`` marks this port as a pure no-op: ``use_websocket`` uses it
    as the signal that SSR/SSG degradation (warning + empty closed handle)
    applies, rather than opening a connection through the port.
    """

    noop = True

    def open(
        self,
        url: str,
        *,
        protocols: tuple[str, ...] = (),
        on_open: Callable[[], None],
        on_message: Callable[[str], None],
        on_binary: Callable[[], None],
        on_error: Callable[[], None],
        on_close: Callable[[int, str, bool], None],
    ) -> WebSocketConnection:
        return ServerWebSocketConnection()
