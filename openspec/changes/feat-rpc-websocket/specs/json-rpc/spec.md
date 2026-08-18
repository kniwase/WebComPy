# JSON-RPC Specification (delta)

## ADDED Requirements

### Requirement: The dispatcher shall support a WebSocket transport

The dispatcher's core logic (envelope validation, batch handling, procedure invocation, error mapping, `meta` handling) SHALL be transport-neutral, shared by the HTTP endpoint and a WebSocket endpoint. The framework SHALL provide a Starlette WebSocket endpoint mounted through the same mount mechanism as the HTTP dispatcher, which SHALL feed each incoming text frame through the shared dispatch logic and SHALL write each response back as a text frame. The HTTP POST behavior SHALL be unchanged. The WebSocket endpoint SHALL additionally support server→client notification frames for subscription streams and SHALL clean up all per-connection subscription state when the socket closes.

#### Scenario: WebSocket single call

- **WHEN** a client sends `{"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1}` as a text frame
- **THEN** the endpoint SHALL respond with `{"jsonrpc": "2.0", "result": 3, "id": 1}` as a text frame

#### Scenario: Shared semantics with HTTP

- **WHEN** the same procedure is invoked over HTTP POST and over WebSocket
- **THEN** envelope validation, decoding, and error mapping SHALL behave identically

#### Scenario: Connection close cleans up subscriptions

- **WHEN** a socket with active subscription streams closes
- **THEN** the server SHALL terminate those streams and release their per-connection state

### Requirement: Subscription procedures shall be registrable with a bounded replay buffer

The framework SHALL provide a registration API for subscription procedures (producing an async stream of events). The dispatcher SHALL assign a monotonically increasing `cursor` per event per stream, SHALL forward events to subscribers as notification frames, SHALL retain a bounded replay buffer per stream (default 256 events, configurable at registration), SHALL honor rejoin requests carrying `last_cursor` by replaying buffered events with greater cursors before live delivery, and SHALL answer `resync_required` when `last_cursor` is older than the buffer's replayable range (older than the oldest buffered cursor minus one, i.e. when at least one missed event has been evicted).

#### Scenario: Rejoin within the buffer replays missed events

- **WHEN** a subscriber rejoins with `last_cursor=10` and the buffer holds cursors `8`–`30`
- **THEN** the server SHALL deliver cursors `11`–`30` before resuming live events

#### Scenario: Rejoin beyond the buffer requires resync

- **WHEN** a subscriber rejoins with a cursor older than the buffer's replayable range (at least one missed event has been evicted)
- **THEN** the server SHALL answer `resync_required` and SHALL NOT fabricate or silently skip events
