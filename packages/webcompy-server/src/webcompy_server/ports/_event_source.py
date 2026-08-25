"""Server-side event source port."""

from __future__ import annotations

from collections.abc import Callable

from webcompy.ports._event_source import EventSourcePort


class ServerEventSourcePort(EventSourcePort):
    """Server-side no-op ``EventSourcePort``.

    ``noop = True`` marks this port as a pure no-op: ``use_event_source`` uses
    it as the signal that SSR/SSG degradation (warning + empty closed handle)
    applies, rather than opening a connection through the port.
    """

    noop = True

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
        """Open an event source connection.

        Args:
            url: Event source URL.
            events: Event types to listen for.
            on_open: Callback when the connection opens.
            on_message: Callback for incoming messages.
            on_error: Callback for errors.
            on_close: Callback when the connection closes.

        Returns:
            Callable that closes the connection.

        """

        def _noop() -> None:
            pass

        return _noop
