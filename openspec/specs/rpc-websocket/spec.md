# RPC WebSocket

## Purpose

RPC over WebSocket: `RpcWsClient` runs the typed JSON-RPC machinery from `json-rpc` over the shared, reference-counted, auto-reconnecting connection from `websocket-composable`. On top of plain call/response it adds server→client subscription streams with a Phoenix-style rejoin-and-catch-up protocol: server-assigned cursors, bounded replay buffers with honest `resync_required` overflow signaling, application-level heartbeat liveness detection, and server-driven reconnection via a reserved close notification. The client is browser-runtime-only: SSR/SSG performs no socket work and transfers no RPC-WS state.

## Requirements

### Requirement: RpcWsClient shall perform JSON-RPC calls over a shared WebSocket

The framework SHALL provide an `RpcWsClient` (importable from `webcompy` and `webcompy.rpc`) that runs JSON-RPC 2.0 over the typed realtime WebSocket layer. Calls SHALL send standard request envelopes as text frames and SHALL correlate responses by `id` via an in-flight map; notifications SHALL fire and forget; error responses SHALL raise the existing `RpcError` with `code`, `message`, and `data`. The underlying socket SHALL be the shared, reference-counted, auto-reconnecting connection from `websocket-composable`. Calls that are in flight when the connection drops SHALL fail with `RpcError` (they are NOT silently retried); subscriptions SHALL heal via the rejoin protocol instead.

#### Scenario: Call round trip
- **WHEN** `client.call("add", {"a": 2, "b": 3}, result_type=int)` is issued over an open connection
- **THEN** the server SHALL receive a standard JSON-RPC request frame
- **AND** the caller SHALL receive `5` as an `int` (typed via `from_json` with `meta`)

#### Scenario: In-flight call fails on disconnect
- **WHEN** a call is awaiting its response and the connection drops abnormally
- **THEN** the pending call SHALL raise `RpcError`
- **AND** subsequent calls after reconnection SHALL work normally

#### Scenario: Unknown method maps to RpcError
- **WHEN** a call targets an unregistered method
- **THEN** the client SHALL raise `RpcError` with code `-32601`

### Requirement: Subscriptions shall deliver server events with cursors as an async iterator

Server procedures marked subscribable SHALL produce event streams; each event SHALL be delivered to subscribers as a server→client notification frame carrying `subscription_id`, a server-assigned monotonically increasing `cursor`, and `data`. Client-side `client.subscribe(method, params, *, event_type=E)` SHALL return an `AsyncIterator[E]` (typed via the `typed-realtime` codec) plus a subscription-state surface. Events SHALL be delivered in cursor order per subscription.

#### Scenario: Subscribe and iterate events
- **WHEN** `sub = client.subscribe("ticker", {}, event_type=Tick)` and the server emits two events
- **THEN** `async for ev in sub:` SHALL yield both `Tick` instances in cursor order

#### Scenario: Unsubscribe stops delivery
- **WHEN** the subscriber detaches (explicit close or component destroy)
- **THEN** the server SHALL be notified to end the stream
- **AND** the iterator SHALL finish
- **AND** a late server response for the subscription SHALL NOT re-activate or re-subscribe it

### Requirement: Reconnection shall rejoin subscriptions with the last received cursor

After a reconnect, the client SHALL automatically re-subscribe every live subscription, including the last received `cursor` for each. A live subscription that has received no event yet SHALL rejoin with `last_cursor: 0`. The server SHALL replay buffered events with `cursor > last_cursor` before resuming live delivery, so no event within the replay buffer is lost and no event is delivered twice. When the client's last cursor is older than the buffer's replayable range (older than the oldest buffered cursor minus one, i.e. at least one missed event has been evicted), the server SHALL respond with a `resync_required` signal and end the stream; the client SHALL surface this on the subscription state (and SHALL NOT fabricate missed events).

#### Scenario: Catch-up after short outage
- **WHEN** a subscription has received events up to cursor `41`, the connection drops, the server emits cursors `42`–`44` during the outage, and the client reconnects
- **THEN** the client SHALL rejoin with `last_cursor=41`
- **AND** the server SHALL replay `42`–`44` before live events resume

#### Scenario: Rejoin with no received events replays the whole buffer
- **WHEN** a subscription was confirmed but received no event before the connection dropped, and the client reconnects
- **THEN** the client SHALL rejoin with `last_cursor=0`
- **AND** the server SHALL replay the whole buffer when it still covers cursor `0` (no event silently skipped)
- **AND** when the buffer no longer covers cursor `0` (events were evicted), the server SHALL answer `resync_required` instead

#### Scenario: Long overflow requires resync
- **WHEN** the client's last cursor is older than the replay buffer floor at rejoin
- **THEN** the server SHALL answer `resync_required`
- **AND** the client's subscription state SHALL reflect that a full refetch is required

#### Scenario: Resync ends the subscription permanently
- **WHEN** the server answers `resync_required` for a rejoin
- **THEN** the client SHALL end the subscription with its state set to `RESYNC_REQUIRED`
- **AND** the client SHALL NOT re-subscribe that subscription on subsequent reconnects

### Requirement: Subscriptions shall end when the connection terminates permanently

When the underlying connection terminates permanently (reconnection disabled, `reconnect_max_attempts` exhausted, or a clean close), the client SHALL end every live and pending subscription: their state SHALL transition to `CLOSED`, their iterators SHALL finish, and they SHALL NOT be re-subscribed on any later connection.

#### Scenario: Permanent termination finishes all subscriptions
- **WHEN** the connection is closed permanently while a subscription is `ACTIVE` or `PENDING`
- **THEN** the subscription state SHALL become `CLOSED`
- **AND** the subscription iterator SHALL finish

### Requirement: The server replay buffer shall be bounded per subscription stream

The server SHALL retain only the newest N events per subscription stream for replay (default 256, configurable at procedure registration). Overflow SHALL be handled exclusively through `resync_required` (never silent loss). A stream whose source has ended (the async generator finished or raised) SHALL be released after the idle grace period and SHALL NOT be reused for new subscriptions (a later subscribe SHALL start a fresh stream).

#### Scenario: Buffer overflow signals resync
- **WHEN** more than N events are emitted during a subscriber's outage
- **THEN** rejoin SHALL produce `resync_required` rather than a partial silent replay

#### Scenario: Finished streams are not reused
- **WHEN** a subscription stream's source has ended and the stream has been released
- **THEN** a later subscribe to the same method and params SHALL create a fresh stream
- **AND** SHALL NOT attach to the finished stream (which would silently deliver nothing)

### Requirement: Application-level heartbeat shall detect dead connections

When enabled (default: `heartbeat_interval=30.0`, `heartbeat_timeout=10.0`), the client SHALL send a heartbeat notification every interval and SHALL expect any server frame within the timeout; on timeout it SHALL force an abnormal close of the underlying socket so the reconnect loop engages. Passing `heartbeat_interval=None` SHALL disable the heartbeat. The heartbeat SHALL use reserved JSON-RPC notification method names that cannot collide with registered procedures.

#### Scenario: Dead connection is detected and reconnected
- **WHEN** no frame arrives within `heartbeat_timeout` after a heartbeat
- **THEN** the client SHALL force-close the socket abnormally
- **AND** `.state` SHALL transition through `RECONNECTING` back to `OPEN` on recovery

### Requirement: The WS endpoint shall support server-initiated reconnection via a reserved close notification

The WS endpoint SHALL handle a `_webcompy.close` notification by closing the socket abnormally (code `1011`), so the client reconnect loop engages. Reserved `_webcompy.*` method names SHALL NOT be registrable as user procedures.

#### Scenario: Server-driven reconnection
- **WHEN** the client sends a `_webcompy.close` notification on an open connection
- **THEN** the server SHALL close the socket with code `1011`
- **AND** the client SHALL transition through `RECONNECTING` back to `OPEN` on recovery

### Requirement: RpcWsClient shall be browser-runtime-only with SSR no-op

During SSR/SSG, constructing or using `RpcWsClient` SHALL emit a warning and perform no socket work; SSR-time RPC SHALL continue to use the existing HTTP client and transfer cache. No subscription state, cursors, or in-flight calls SHALL be collected into the hydration transfer payload.

#### Scenario: SSG performs no WS work
- **WHEN** a page that constructs `RpcWsClient` is statically generated
- **THEN** no WebSocket SHALL be opened
- **AND** the hydration payload SHALL contain no RPC-WS state

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
