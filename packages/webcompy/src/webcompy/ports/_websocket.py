from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class WebSocketConnection(ABC):
    """Handle for an open WebSocket connection.

    Implementations wrap a single native (or fake) socket and expose the send
    and close operations. ``send`` writes one text frame; ``close`` closes the
    socket and removes its listeners. The port has no component knowledge.
    """

    @abstractmethod
    def send(self, data: str) -> None:
        """Send one text frame."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection and remove its listeners."""
        ...


class WebSocketPort(ABC):
    """Port for WebSocket connections (callback surface).

    Implementations open a connection for the given URL and optional
    subprotocols and deliver lifecycle transitions and received frames to the
    supplied callbacks. The returned handle exposes send/close. All subscriber
    fan-out is owned by the caller.
    """

    @abstractmethod
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
        """Open a WebSocket connection for ``url`` and ``protocols``.

        ``on_message`` receives the text payload of each text frame; binary
        frames are reported via ``on_binary``. ``on_close`` receives
        ``(code, reason, was_clean)``.
        """
        ...
