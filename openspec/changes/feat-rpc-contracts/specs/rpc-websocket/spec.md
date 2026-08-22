# RPC WebSocket (delta)

## MODIFIED Requirements

### Requirement: RpcWsClient shall perform JSON-RPC calls over a shared WebSocket

The framework SHALL provide an `RpcWsClient` (importable from `webcompy` and `webcompy.rpc`) that runs JSON-RPC 2.0 over the typed realtime WebSocket layer. `RpcWsClient` SHALL be a transport implementing the `RpcTransport` protocol defined in the `rpc-contracts` capability: RPC calls SHALL be issued through `Procedure` contracts (`await add(client, params)`) via `RpcCall`, which delegates to the `RpcWsClient.call` transport method, multiple `Procedure` calls SHALL be issuable in one round-trip via `batch(*calls: RpcCall, return_exceptions=False)` as a single array text frame reusing the existing batch wire (empty `batch()` is a no-op returning `()` with no I/O), and fire-and-forget notifications SHALL be issuable via `notify(*calls: RpcCall)` as a single array text frame of id-less envelopes (empty `notify()` is a no-op returning `None`). Calls (and batch entries) SHALL send standard request envelopes as text frames and SHALL correlate responses by `id` via an in-flight map; notifications via `notify` SHALL be id-less envelopes sent as a single array frame with no `Future`s and no response; error responses SHALL raise the existing `RpcError` with `code`, `message`, and `data`. The underlying socket SHALL be the shared, reference-counted, auto-reconnecting connection from `websocket-composable`. Calls that are in flight when the connection drops SHALL fail with `RpcError` (they are NOT silently retried); subscriptions SHALL heal via the rejoin protocol instead.

#### Scenario: Call round trip
- **WHEN** `await add(client, AddParams(2, 3))` is issued through an `add = Procedure("add", AddParams, int)` contract over an open connection
- **THEN** the server SHALL receive a standard JSON-RPC request frame
- **AND** the caller SHALL receive `5` as an `int` (typed via `from_json` with `meta`)

#### Scenario: In-flight call fails on disconnect
- **WHEN** a contract call is awaiting its response and the connection drops abnormally
- **THEN** the pending call SHALL raise `RpcError`
- **AND** subsequent calls after reconnection SHALL work normally
#### Scenario: Unknown method maps to RpcError

- **WHEN** a contract targets an unbound method name
- **THEN** the client SHALL raise `RpcError` with code `-32601`

#### Scenario: Batch over WebSocket

- **WHEN** `c1 = add(client, AddParams(1, 0))` and `c2 = add(client, AddParams(2, 0))` and `await batch(c1, c2)` is issued over an open `RpcWsClient`
- **THEN** a single array text frame SHALL be sent and the result SHALL be `tuple[int, int]` in input order via `RpcCall` batch

#### Scenario: Empty batch over WebSocket is a no-op

- **WHEN** `await batch()` with no calls is evaluated over an `RpcWsClient`
- **THEN** no frame SHALL be sent and `()` SHALL be returned

#### Scenario: Notify over WebSocket

- **WHEN** `c1 = add(client, AddParams(1, 0))` and `c2 = add(client, AddParams(2, 0))` and `await notify(c1, c2)` is issued over an open `RpcWsClient`
- **THEN** a single array text frame of id-less envelopes SHALL be sent and `None` SHALL be returned with no response expected

#### Scenario: Empty notify over WebSocket is a no-op

- **WHEN** `await notify()` with no calls is evaluated over an `RpcWsClient`
- **THEN** no frame SHALL be sent and `None` SHALL be returned

### Requirement: Subscriptions shall deliver server events with cursors as an async iterator

Server procedures bound to `Subscription` contracts SHALL produce event streams; each event SHALL be delivered to subscribers as a server→client notification frame carrying `subscription_id`, a server-assigned monotonically increasing `cursor`, and `data`. Client-side subscriptions SHALL be established through `Subscription` contracts (`sub = ticker(client, params)`), which delegate to the `RpcWsClient.subscribe` transport method and SHALL return an `AsyncIterator[E]` typed via the contract's declared event type (the `typed-realtime` codec) plus the subscription-state surface. Events SHALL be delivered in cursor order per subscription.

#### Scenario: Subscribe and iterate events
- **WHEN** `sub = ticker(client, TickerParams("a"))` for a `ticker = Subscription("ticker", TickerParams, Tick)` contract and the server emits two events
- **THEN** `async for ev in sub:` SHALL yield both `Tick` instances in cursor order

#### Scenario: Unsubscribe stops delivery
- **WHEN** the subscriber detaches (explicit close or component destroy)
- **THEN** the server SHALL be notified to end the stream
- **AND** the iterator SHALL finish
- **AND** a late server response for the subscription SHALL NOT re-activate or re-subscribe it

### Requirement: RpcWsClient shall provide a typed stream call

Streaming RPC calls over the WebSocket SHALL be issued through `StreamingProcedure` contracts (`it = produce(client, ProduceParams(2))`), which delegate to the `RpcWsClient.stream` transport method. `RpcWsClient.stream` SHALL return an `RpcStream` per the `rpc-streaming` capability. It SHALL dispatch `_webcompy.event` frames by `stream_id` (separately from `subscription_id` subscription dispatch), map `stream_done` to exhaustion and `stream_error` to `RpcError`, and send `_webcompy.stream_cancel` on close. Calling a streaming contract when the client is closed, unavailable outside the browser, or the socket is not `OPEN` SHALL raise `RpcError` immediately (fail-fast, like contract calls). Frame encoding and params handling SHALL reuse the existing call machinery.

#### Scenario: stream over an open socket returns an RpcStream
- **WHEN** `it = produce(client, ProduceParams(2))` is evaluated with an open connection
- **THEN** an `RpcStream` SHALL be returned whose iteration yields the decoded items

#### Scenario: stream while closed fails fast
- **WHEN** a streaming contract is invoked while the client is closed or the socket is not open
- **THEN** `RpcError` SHALL be raised immediately

#### Scenario: close sends stream_cancel
- **WHEN** `.close()` is called on an active WebSocket `RpcStream`
- **THEN** the client SHALL send `_webcompy.stream_cancel` for that stream
