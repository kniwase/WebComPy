"""Server-Sent Events connection port (callback surface)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class EventSourcePort(ABC):
    """Port for Server-Sent Events connections (callback surface).

    Implementations open a connection for the given URL and event types and
    deliver lifecycle transitions and received events to the supplied
    callbacks. The returned cleanup callable closes the connection. The port
    has no component knowledge; all subscriber fan-out is owned by the caller.
    """

    @abstractmethod
    def open(
        self,
        url: str,
        *,
        events: tuple[str, ...],
        on_open: Callable[[], None],
        on_message: Callable[[str, str, str], None],
        on_error: Callable[[], None],
        on_close: Callable[[], None],
    ) -> Callable[[], None]:
        """Open an SSE connection for ``url`` and the named ``events``.

        ``on_message`` receives ``(event_type, data, last_event_id)``.
        The returned cleanup callable closes the underlying connection.

        Args:
            url: SSE endpoint URL to connect to.
            events: Named event types delivered through ``on_message``.
            on_open: Called when the connection is established.
            on_message: Called with ``(event_type, data, last_event_id)``
                for each received event.
            on_error: Called when a connection-level error occurs.
            on_close: Called when the connection closes.

        Returns:
            A cleanup callable closing the underlying connection.

        """
        ...
