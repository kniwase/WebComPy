# RPC WebSocket (delta)

## ADDED Requirements

### Requirement: The WebSocket transport shall stream flagged calls per stream_id

A single request frame with `"stream": true` targeting a streaming procedure SHALL be answered with `{"jsonrpc": "2.0", "result": {"stream_id": <str>}, "id": <id>}`. Each element SHALL be delivered as an existing `_webcompy.event` notification frame whose `params` SHALL contain `stream_id` (instead of `subscription_id`), the encoded `data`, and transfer `meta` — with NO cursor. Generator exhaustion SHALL emit a `_webcompy.stream_done` notification with `stream_id`; a mid-stream generator exception SHALL emit a `_webcompy.stream_error` notification whose params SHALL contain `stream_id`, `code`, `message`, and optional `data`. The client SHALL send a `_webcompy.stream_cancel` notification with `stream_id` to cancel an active stream. The stream-member mismatch and batch/notification rules from the `json-rpc` capability SHALL apply identically on the WebSocket transport.

#### Scenario: Flagged call acks with a stream id

- **WHEN** a client sends a flagged streaming call with `id: 7`
- **THEN** the endpoint SHALL answer `{"jsonrpc": "2.0", "result": {"stream_id": <str>}, "id": 7}`

#### Scenario: Items flow as event frames without cursors

- **WHEN** a streaming procedure yields two elements
- **THEN** the endpoint SHALL send two `_webcompy.event` frames carrying the `stream_id`, their encoded `data` and `meta`, and no `cursor` field

#### Scenario: Exhaustion emits stream_done

- **WHEN** the generator finishes normally
- **THEN** the endpoint SHALL send `_webcompy.stream_done` with the `stream_id`

#### Scenario: Mid-stream exception emits stream_error

- **WHEN** the generator raises mid-stream
- **THEN** the endpoint SHALL send `_webcompy.stream_error` with the `stream_id`, `code`, `message`, and `data`
- **AND** no `stream_done` SHALL follow

#### Scenario: Stream cancel stops the generator

- **WHEN** the client sends `_webcompy.stream_cancel` for an active stream
- **THEN** the server SHALL stop that stream's generator

### Requirement: Stream calls shall be per-call with fail-fast on disconnect

Each streaming call SHALL create its own generator instance and stream task (no sharing between callers, no replay buffer, no idle grace period, no rejoin). When the socket closes or terminates, the endpoint SHALL cancel all of that connection's active stream tasks, and the client SHALL fail each affected stream by raising `RpcError` from iteration (never silently retried or resubscribed), matching `call()` in-flight behavior.

#### Scenario: Streams are not shared across callers

- **WHEN** two clients call the same streaming procedure with identical params
- **THEN** two independent generator instances SHALL run

#### Scenario: Socket close cancels server-side streams

- **WHEN** a socket with active streams closes
- **THEN** the server SHALL cancel all stream tasks belonging to that connection

#### Scenario: Disconnect fails the client stream

- **WHEN** the underlying socket drops while a stream is active
- **THEN** the client's next `__anext__` SHALL raise `RpcError`
- **AND** the stream SHALL NOT be resubscribed

### Requirement: RpcWsClient shall provide a typed stream call

`RpcWsClient` SHALL provide `stream(method, params=None, *, result_type=None)` returning an `RpcStream` per the `rpc-streaming` capability. It SHALL dispatch `_webcompy.event` frames by `stream_id` (separately from `subscription_id` subscription dispatch), map `stream_done` to exhaustion and `stream_error` to `RpcError`, and send `_webcompy.stream_cancel` on close. Outside the browser `stream()` SHALL return an immediately-finished empty `RpcStream` (mirroring `subscribe()` and the `rpc-streaming` SSR contract); when the client is closed or the socket is not `OPEN` in the browser, `stream()` SHALL raise `RpcError` immediately (fail-fast, like `call()`). Frame encoding and params handling SHALL reuse the existing call machinery.

#### Scenario: stream over an open socket returns an RpcStream

- **WHEN** `client.stream("produce", {"n": 2}, result_type=int)` is called with an open connection
- **THEN** an `RpcStream` SHALL be returned whose iteration yields the decoded items

#### Scenario: stream while closed fails fast

- **WHEN** `client.stream(...)` is called while the client is closed or the socket is not open
- **THEN** `RpcError` SHALL be raised immediately

#### Scenario: close sends stream_cancel

- **WHEN** `.close()` is called on an active WebSocket `RpcStream`
- **THEN** the client SHALL send `_webcompy.stream_cancel` for that stream
