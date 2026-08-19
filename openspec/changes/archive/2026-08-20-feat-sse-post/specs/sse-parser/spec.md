# SSE Parser (delta)

## Purpose

Defines the framework-internal Server-Sent Events framing codec: an incremental parser that assembles complete events from arbitrarily split `text/event-stream` chunks, and a formatter that emits valid SSE frames. It is the shared building block for fetch-based SSE consumption and for future streaming features.

## ADDED Requirements

### Requirement: An incremental SSE parser shall assemble events across arbitrary chunk boundaries

The framework SHALL provide a pure-Python SSE parser in `webcompy/ajax/_sse.py` importable from both browser and server packages. The parser SHALL accept string chunks via repeated calls and SHALL yield complete events as they are delimited. An event SHALL consist of `event_type: str` (default `"message"`), `data: str`, and `last_event_id: str` (empty when no `id:` line was seen). The parser SHALL NOT import component, signal, or browser modules.

The parser SHALL implement the SSE wire format: an event SHALL be dispatched only when a blank line (`\n\n` or `\r\n\r\n`) terminates it; lines beginning with `:` SHALL be ignored (comments); consecutive `data:` lines SHALL be joined with `\n`; the `event:` field SHALL name the event type; the `id:` field SHALL set the event id, which SHALL persist across subsequent events until overridden; a trailing event without a terminating blank line at end of input SHALL NOT be dispatched.

#### Scenario: Event split across chunks parses identically

- **WHEN** the input `"data: hello\n\n"` is fed as the chunks `"data: he"`, `"llo\n"`, `"\n"`
- **THEN** the parser SHALL yield exactly one event with `event_type == "message"` and `data == "hello"`

#### Scenario: Multi-line data is joined with newlines

- **WHEN** the input `"data: a\ndata: b\n\n"` is fed
- **THEN** the parser SHALL yield one event with `data == "a\nb"`

#### Scenario: Named events and ids

- **WHEN** the input `"event: status\nid: 7\ndata: ok\n\n"` is fed
- **THEN** the parser SHALL yield an event with `event_type == "status"`, `data == "ok"`, and `last_event_id == "7"`

#### Scenario: Id persists across events

- **WHEN** the input `"id: 7\ndata: a\n\ndata: b\n\n"` is fed
- **THEN** the second event SHALL carry `last_event_id == "7"`

#### Scenario: Comments are ignored

- **WHEN** the input `": keepalive\ndata: x\n\n"` is fed
- **THEN** the parser SHALL yield exactly one event with `data == "x"`

#### Scenario: Trailing incomplete event is discarded at end of input

- **WHEN** the input `"data: partial"` is fed and the parser is finished without a terminating blank line
- **THEN** the parser SHALL NOT yield the partial event

#### Scenario: CRLF framing

- **WHEN** the input `"data: hi\r\n\r\n"` is fed
- **THEN** the parser SHALL yield one event with `data == "hi"`

### Requirement: An SSE formatter shall emit frames parseable by the parser

The framework SHALL provide an SSE frame formatting helper alongside the parser in `webcompy/ajax/_sse.py` that, given an event type, data string, and optional id, SHALL emit a valid SSE frame (`event:`/`id:` lines when non-default, `data:` lines — multi-line data emitted as one `data:` line per line — terminated by a blank line).

#### Scenario: Formatter output round-trips through the parser

- **WHEN** a frame is produced for `event_type="item"`, `data="a\nb"`, `id="3"`
- **THEN** feeding the frame to the parser SHALL yield an event with `event_type == "item"`, `data == "a\nb"`, and `last_event_id == "3"`
