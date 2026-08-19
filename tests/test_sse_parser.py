from __future__ import annotations

from webcompy.ajax._sse import _format_sse_event, _ParsedSSEvent, _SSEParser


def _parse_all(input_text: str) -> list[_ParsedSSEvent]:
    parser = _SSEParser()
    events: list[_ParsedSSEvent] = []
    events.extend(parser.feed(input_text))
    return events


class TestParserScenarios:
    def test_event_split_across_chunks_parses_identically(self) -> None:
        parser = _SSEParser()
        assert parser.feed("data: he") == []
        assert parser.feed("llo\n") == []
        events = parser.feed("\n")
        assert len(events) == 1
        assert events[0].event_type == "message"
        assert events[0].data == "hello"
        assert events[0].last_event_id == ""

    def test_multi_line_data_is_joined_with_newlines(self) -> None:
        events = _parse_all("data: a\ndata: b\n\n")
        assert len(events) == 1
        assert events[0].data == "a\nb"

    def test_named_events_and_ids(self) -> None:
        events = _parse_all("event: status\nid: 7\ndata: ok\n\n")
        assert len(events) == 1
        assert events[0].event_type == "status"
        assert events[0].data == "ok"
        assert events[0].last_event_id == "7"

    def test_id_persists_across_events(self) -> None:
        events = _parse_all("id: 7\ndata: a\n\ndata: b\n\n")
        assert len(events) == 2
        assert events[0].last_event_id == "7"
        assert events[1].last_event_id == "7"

    def test_comments_are_ignored(self) -> None:
        events = _parse_all(": keepalive\ndata: x\n\n")
        assert len(events) == 1
        assert events[0].data == "x"

    def test_trailing_incomplete_event_is_discarded(self) -> None:
        assert _parse_all("data: partial") == []

    def test_crlf_framing(self) -> None:
        events = _parse_all("data: hi\r\n\r\n")
        assert len(events) == 1
        assert events[0].data == "hi"

    def test_leading_space_after_colon_is_stripped(self) -> None:
        events = _parse_all("data:  spaced\n\n")
        assert events[0].data == " spaced"

    def test_data_without_colon_is_append_only(self) -> None:
        events = _parse_all("data\n\n")
        assert events[0].data == ""

    def test_unknown_fields_are_ignored(self) -> None:
        events = _parse_all("retry: 3000\ndata: x\n\n")
        assert len(events) == 1
        assert events[0].data == "x"

    def test_id_with_null_character_is_ignored(self) -> None:
        parser = _SSEParser()
        events = parser.feed("id: a\x00b\ndata: x\n\n")
        assert events[0].last_event_id == ""

    def test_data_less_event_is_not_dispatched_but_id_persists(self) -> None:
        parser = _SSEParser()
        assert parser.feed("id: 7\n\n") == []
        events = parser.feed("data: x\n\n")
        assert len(events) == 1
        assert events[0].last_event_id == "7"

    def test_id_line_after_data_is_included_in_the_same_event(self) -> None:
        events = _parse_all("data: x\nid: 9\n\n")
        assert len(events) == 1
        assert events[0].last_event_id == "9"

    def test_multiple_events_in_one_chunk(self) -> None:
        events = _parse_all("data: a\n\ndata: b\n\n")
        assert [e.data for e in events] == ["a", "b"]

    def test_empty_chunk_is_a_noop(self) -> None:
        parser = _SSEParser()
        assert parser.feed("") == []
        events = parser.feed("data: x\n\n")
        assert [e.data for e in events] == ["x"]

    def test_last_event_id_is_exposed(self) -> None:
        parser = _SSEParser()
        parser.feed("data: a\n\n")
        assert parser.last_event_id == ""
        parser.feed("id: 5\ndata: b\n\n")
        assert parser.last_event_id == "5"

    def test_split_at_every_byte_position_parses_identically(self) -> None:
        stream = ": keepalive\r\nevent: status\nid: 7\ndata: a\ndata: b\n\r\nid: 8\ndata: c\n\n"
        expected = _parse_all(stream)
        for split in range(len(stream) + 1):
            parser = _SSEParser()
            got: list[_ParsedSSEvent] = []
            got.extend(parser.feed(stream[:split]))
            got.extend(parser.feed(stream[split:]))
            assert got == expected


class TestFormatter:
    def test_default_message_frame(self) -> None:
        assert _format_sse_event(data="x") == "data: x\n\n"

    def test_round_trips_through_the_parser(self) -> None:
        frame = _format_sse_event(event_type="item", data="a\nb", event_id="3")
        events = _parse_all(frame)
        assert len(events) == 1
        assert events[0].event_type == "item"
        assert events[0].data == "a\nb"
        assert events[0].last_event_id == "3"

    def test_omits_default_lines(self) -> None:
        frame = _format_sse_event(event_type="message", data="x", event_id=None)
        assert frame == "data: x\n\n"

    def test_multi_line_data_emits_one_data_line_per_line(self) -> None:
        frame = _format_sse_event(data="a\nb\nc")
        assert frame == "data: a\ndata: b\ndata: c\n\n"
