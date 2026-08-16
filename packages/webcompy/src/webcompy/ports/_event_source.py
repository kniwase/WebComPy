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
        """
        ...
