# JSON-RPC (delta)

## ADDED Requirements

### Requirement: The stream extension member shall select streamed responses

Requests MAY carry a `"stream": true` member alongside the standard JSON-RPC members. A single request with `"stream": true` targeting a streaming procedure SHALL produce a streamed response; a single request WITHOUT the member targeting a streaming procedure SHALL answer error `-32600` with a message indicating a stream request is required; a request WITH the member targeting a non-streaming procedure SHALL answer error `-32600` with a message indicating the method is not a streaming procedure. In a batch request, any entry targeting a streaming procedure SHALL answer `-32600` for that entry (streaming in batches is unsupported). Notifications (no `id`) targeting streaming procedures SHALL NOT execute. The member SHALL NOT alter the handling of ordinary procedures.

#### Scenario: Streaming procedure called without the member errors

- **WHEN** a client calls a streaming procedure without `"stream": true`
- **THEN** the response SHALL be a JSON-RPC error with code `-32600`

#### Scenario: Ordinary procedure called with the member errors

- **WHEN** a client calls an ordinary procedure with `"stream": true`
- **THEN** the response SHALL be a JSON-RPC error with code `-32600`

#### Scenario: Streaming entry in a batch errors per entry

- **WHEN** a batch contains a streaming procedure call (with or without the member)
- **THEN** that entry's response SHALL be a JSON-RPC error with code `-32600`
- **AND** other entries SHALL be processed normally

#### Scenario: Notification to a streaming procedure does not execute

- **WHEN** a notification (no `id`) targets a streaming procedure
- **THEN** the procedure SHALL NOT execute and no response SHALL be produced

### Requirement: The HTTP dispatcher shall answer flagged streaming requests with an SSE stream

When the HTTP dispatcher receives a single request with `"stream": true` targeting a streaming procedure, it SHALL respond `200` with `Content-Type: text/event-stream` and `Cache-Control: no-store`, and SHALL stream events produced by iterating the generator: one `item` event per element whose `data` is a JSON object `{"data": <encoded element>, "meta": <transfer meta or null>}` (encoded with the same `encode_with_meta` semantics as ordinary results), followed by a `done` event on exhaustion. If the generator raises mid-stream, the dispatcher SHALL emit an `error` event whose `data` is `{"code": <int>, "message": <str>, "data": <detail or null>}` and SHALL stop. All pre-stream failures (parse errors, unknown method, invalid params, stream-member mismatches, batch/notification rules) SHALL keep the standard `application/json` JSON-RPC error responses. When the client disconnects mid-stream, the dispatcher SHALL stop iterating and close the generator.

#### Scenario: Successful stream emits items then done

- **WHEN** a flagged request targets a streaming procedure yielding two elements
- **THEN** the response SHALL be `text/event-stream` and SHALL emit two `item` events followed by one `done` event

#### Scenario: Mid-stream exception emits error event

- **WHEN** the generator raises after yielding one element
- **THEN** the stream SHALL emit the already-produced `item` event followed by an `error` event carrying the failure details
- **AND** no `done` event SHALL follow

#### Scenario: Invalid params still answer JSON

- **WHEN** a flagged request targets a streaming procedure with invalid params
- **THEN** the response SHALL be `application/json` with a JSON-RPC error body (no SSE stream)

#### Scenario: Client disconnect stops the generator

- **WHEN** the client disconnects while the stream is active
- **THEN** the dispatcher SHALL stop iterating the generator and SHALL close it

### Requirement: The HTTP client shall provide a typed stream call

The framework SHALL provide `rpc.stream(method, params=None, *, result_type=None)` (importable alongside `rpc.call`) that POSTs a `"stream": true` envelope through the streaming fetch capability to the RPC endpoint. When the response is a JSON body (not `text/event-stream`), the client SHALL resolve it as an ordinary JSON-RPC response and SHALL raise `RpcError` for error responses before returning. A non-successful status or a non-stream, non-JSON body SHALL raise `RpcError`. When the response is `text/event-stream`, the client SHALL return an `RpcStream` that parses the event stream with the `sse-parser` codec, maps `item` events to typed items, `error` events to `RpcError` raised from iteration, and `done` to normal exhaustion, per the `rpc-streaming` capability.

#### Scenario: JSON-RPC error answered as JSON raises before iteration

- **WHEN** `rpc.stream("unknown_method")` receives a JSON-RPC error response with `Content-Type: application/json`
- **THEN** `RpcError` SHALL be raised by the `stream()` call itself (no iterator returned)

#### Scenario: SSE stream yields typed items

- **WHEN** `rpc.stream("produce", {"n": 2}, result_type=Item)` is consumed
- **THEN** iteration SHALL yield two decoded `Item` instances and then finish
