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
        def _noop() -> None:
            pass

        return _noop
