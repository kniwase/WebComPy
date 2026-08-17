# RPC WebSocket Specification (delta)

## ADDED Requirements

### Requirement: RpcWsClient shall perform JSON-RPC calls over a shared WebSocket

The framework SHALL provide an `RpcWsClient` (importable from `webcompy` and `webcompy.rpc`) that runs JSON-RPC 2.0 over the typed realtime WebSocket layer. Calls SHALL send standard request envelopes as text frames and SHALL correlate responses by `id` via an in-flight map; notifications SHALL fire and forget; error responses SHALL raise the existing `RpcError` with `code`, `message`, and `data`. The underlying socket SHALL be the shared, reference-counted, auto-reconnecting connection from `feat-websocket-composable`. Calls that are in flight when the connection drops SHALL fail with `RpcError` (they are NOT silently retried); subscriptions SHALL heal via the rejoin protocol instead.

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

Server procedures marked subscribable SHALL produce event streams; each event SHALL be delivered to subscribers as a server→client notification frame carrying `subscription_id`, a server-assigned monotonically increasing `cursor`, and `data`. Client-side `client.subscribe(method, params, *, event_type=E)` SHALL return an `AsyncIterator[E]` (typed via the `feat-typed-realtime` codec) plus a subscription-state surface. Events SHALL be delivered in cursor order per subscription.

#### Scenario: Subscribe and iterate events

- **WHEN** `sub = client.subscribe("ticker", {}, event_type=Tick)` and the server emits two events
- **THEN** `async for ev in sub:` SHALL yield both `Tick` instances in cursor order

#### Scenario: Unsubscribe stops delivery

- **WHEN** the subscriber detaches (explicit close or component destroy)
- **THEN** the server SHALL be notified to end the stream
- **AND** the iterator SHALL finish

### Requirement: Reconnection shall rejoin subscriptions with the last received cursor

After a reconnect, the client SHALL automatically re-subscribe every live subscription, including the last received `cursor` for each. The server SHALL replay buffered events with `cursor > last_cursor` before resuming live delivery, so no event within the replay buffer is lost and no event is delivered twice. When the client's last cursor is older than the bounded replay buffer floor, the server SHALL respond with a `resync_required` signal and end the stream; the client SHALL surface this on the subscription state (and SHALL NOT fabricate missed events).

#### Scenario: Catch-up after short outage

- **WHEN** a subscription has received events up to cursor `41`, the connection drops, the server emits cursors `42`–`44` during the outage, and the client reconnects
- **THEN** the client SHALL rejoin with `last_cursor=41`
- **AND** the server SHALL replay `42`–`44` before live events resume

#### Scenario: Long overflow requires resync

- **WHEN** the client's last cursor is older than the replay buffer floor at rejoin
- **THEN** the server SHALL answer `resync_required`
- **AND** the client's subscription state SHALL reflect that a full refetch is required

### Requirement: The server replay buffer shall be bounded per subscription stream

The server SHALL retain only the newest N events per subscription stream for replay (default 256, configurable at procedure registration). Overflow SHALL be handled exclusively through `resync_required` (never silent loss).

#### Scenario: Buffer overflow signals resync

- **WHEN** more than N events are emitted during a subscriber's outage
- **THEN** rejoin SHALL produce `resync_required` rather than a partial silent replay

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
