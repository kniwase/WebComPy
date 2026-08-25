"""Incremental ``text/event-stream`` parsing and framing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _ParsedSSEvent:
    event_type: str
    data: str
    last_event_id: str


class _SSEParser:
    """Incremental parser for ``text/event-stream`` payloads.

    Feed text chunks via :meth:`feed`; complete events are returned as they
    are delimited by blank lines. A trailing event without a terminating
    blank line is never dispatched. The ``id:`` field persists across events
    and is exposed via :attr:`last_event_id`.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._data_lines: list[str] = []
        self._event_type: str | None = None
        self._last_event_id = ""
        self._has_data = False

    @property
    def last_event_id(self) -> str:
        return self._last_event_id

    def feed(self, chunk: str) -> list[_ParsedSSEvent]:
        self._buffer += chunk
        events: list[_ParsedSSEvent] = []
        while True:
            newline = self._buffer.find("\n")
            if newline == -1:
                break
            line = self._buffer[:newline]
            self._buffer = self._buffer[newline + 1 :]
            line = line.rstrip("\r")
            if line == "":
                if self._has_data:
                    events.append(
                        _ParsedSSEvent(
                            self._event_type or "message",
                            "\n".join(self._data_lines),
                            self._last_event_id,
                        )
                    )
                self._data_lines = []
                self._event_type = None
                self._has_data = False
                continue
            if line.startswith(":"):
                continue
            field, _, value = line.partition(":")
            if value.startswith(" "):
                value = value[1:]
            if field == "event":
                self._event_type = value
            elif field == "data":
                self._data_lines.append(value)
                self._has_data = True
            elif field == "id" and "\x00" not in value:
                self._last_event_id = value
        return events


def _format_sse_event(event_type: str = "message", data: str = "", event_id: str | None = None) -> str:
    """Format an SSE frame that :class:`_SSEParser` can parse back.

    ``event:`` and ``id:`` lines are emitted only when non-default;
    multi-line data emits one ``data:`` line per line; the frame is
    terminated by a blank line.
    """
    lines: list[str] = []
    if event_type != "message":
        lines.append(f"event: {event_type}")
    if event_id:
        lines.append(f"id: {event_id}")
    for line in data.split("\n"):
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"
