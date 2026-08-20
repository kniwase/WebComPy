# JSON-RPC

## Purpose

Provide a JSON-RPC 2.0 procedure-call layer for WebComPy applications. Procedures are plain Python functions registered by name on the app; the browser client calls them with typed arguments and results over `FetchPort`, with in-process dispatch and hydration baking during SSR/SSG. A strict allowlist guards server-side decoding of client-controlled typed payloads.

## Requirements

### Requirement: JSON-RPC 2.0 dispatcher
The framework SHALL provide a JSON-RPC 2.0 dispatcher as an ASGI endpoint, mounted by default at `/_webcompy-rpc` through the same mount mechanism as user-provided ASGI apps (and registrable at a custom path). The dispatcher insertion is framework-internal and SHALL NOT be subject to the user-mount collision validation defined by the `cli` capability. The dispatcher SHALL implement the JSON-RPC 2.0 specification: the `jsonrpc: "2.0"` member, `method`, optional `params` (by-position array or by-name object), `id`, single and batch requests, notifications (requests without `id`, producing no response body), and the standard error codes `-32700`, `-32600`, `-32601`, `-32602`, `-32603`. When no procedures are registered, the endpoint SHALL NOT be added to the route table.

#### Scenario: Single call
- **WHEN** a client POSTs `{"jsonrpc": "2.0", "method": "get_user", "params": {"id": 1}, "id": 1}` with a registered `get_user` procedure
- **THEN** the dispatcher SHALL invoke the procedure and respond with `{"jsonrpc": "2.0", "result": <value>, "id": 1}`

#### Scenario: Positional params relying on defaults
- **WHEN** a client POSTs `{"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1}` for a procedure `def add(a: int, b: int = 0) -> int`
- **THEN** the dispatcher SHALL invoke the procedure with `a=5` and `b=0` (the declared default)
- **AND** the response SHALL be `{"jsonrpc": "2.0", "result": 5, "id": 1}`

#### Scenario: Batch call
- **WHEN** a client POSTs an array of valid request objects
- **THEN** the dispatcher SHALL process each entry independently and SHALL return an array of per-entry responses (excluding notifications)

#### Scenario: Notification
- **WHEN** a client sends a request object without an `id`
- **THEN** the procedure SHALL execute and no response body SHALL be returned for that entry

#### Scenario: Unknown method
- **WHEN** a client calls an unregistered method name
- **THEN** the response SHALL be a JSON-RPC error with code `-32601`

#### Scenario: Malformed request
- **WHEN** a client POSTs invalid JSON or an object failing envelope validation
- **THEN** the response SHALL use error code `-32700` or `-32600` respectively

#### Scenario: Batch containing only notifications
- **WHEN** a client POSTs a batch array whose entries are all notifications
- **THEN** the procedures SHALL execute
- **AND** the server SHALL return no response body at all (NOT even an empty array), per JSON-RPC 2.0

#### Scenario: Empty batch array
- **WHEN** a client POSTs an empty JSON array as the batch
- **THEN** the response SHALL be a JSON-RPC error with code `-32600`

### Requirement: Procedure registration by annotated signature
Procedures SHALL be plain Python functions (sync or async) registered by name, via decorator or explicit registry call. Procedures SHALL have fully annotated parameters and return types; registrations with untyped parameters or `**kwargs` SHALL be rejected at registration time. The parameter schema SHALL derive from the function's type annotations; the result schema SHALL derive from the return annotation. Procedures may raise exceptions; unhandled exceptions SHALL map to error code `-32603` with a generic message (details logged server-side only).

#### Scenario: Decorator registration
- **WHEN** a fully annotated async function is decorated with the procedure decorator
- **THEN** it SHALL be callable via its registered name through the dispatcher

#### Scenario: Untyped procedure rejected
- **WHEN** a function with unannotated parameters is registered
- **THEN** registration SHALL raise an error identifying the offending parameters

### Requirement: Server-side typed decoding with mandatory allowlist
The dispatcher SHALL decode `params` using `from_json(schema, params, strict=True)` with schemas derived from procedure annotations — never from request content. Type restoration from request `meta` SHALL be limited to the closed set of built-in type tags plus types explicitly registered through an allowlist registration API. The dispatcher SHALL NOT import or resolve classes from client-controlled names under any circumstances.

#### Scenario: Typed params reconstruction
- **WHEN** a procedure `def f(user: User) -> ...` is called with `params: {"user": {...}}`
- **THEN** the procedure SHALL receive a reconstructed `User` instance
- **AND** extra keys in the payload SHALL be rejected with error `-32602` (strict decoding)

#### Scenario: Unregistered type tag rejected
- **WHEN** request metadata references a type tag outside the closed set and not in the allowlist registry
- **THEN** the dispatcher SHALL respond with error `-32602` and SHALL NOT attempt class resolution

### Requirement: Metadata extension member
Requests and responses MAY carry a `meta` member alongside `params`/`result` containing transfer metadata in the `typed-response` wire format (path→type-tag map). The extension SHALL NOT alter standard JSON-RPC members, and peers ignoring `meta` SHALL interoperate normally. Result encoding SHALL use `encode_with_meta` semantics for non-JSON-native values.

#### Scenario: Typed result with metadata
- **WHEN** a procedure returns a dataclass containing `bytes` and `Decimal` fields
- **THEN** the response `result` SHALL contain pristine JSON and `meta` SHALL record those types
- **AND** the framework client SHALL restore the original Python types

#### Scenario: Generic client interoperability
- **WHEN** a non-WebComPy JSON-RPC client calls a procedure with plain JSON params and ignores `meta`
- **THEN** the call SHALL succeed per the JSON-RPC 2.0 specification

### Requirement: Typed browser client over FetchPort
The framework SHALL provide a client API (e.g. `rpc.call(method, params, result_type=T)`) that posts envelopes through `FetchPort`. During SSR/SSG, self-site dispatch SHALL be in-process via ASGI transport and results SHALL be recorded in the hydration transfer cache (bake), with the `transfer=False` opt-out applying as for other self-site fetches. JSON-RPC error responses SHALL raise a dedicated `RpcError` carrying `code`, `message`, and `data`. Result decoding SHALL apply `from_json` with response `meta`.

#### Scenario: RPC during SSR is baked
- **WHEN** a component performs an RPC call during SSR against the same app's dispatcher
- **THEN** no network I/O SHALL occur
- **AND** the response SHALL be recorded in the hydration transfer cache so the browser replays it without re-calling

#### Scenario: Error mapping
- **WHEN** the dispatcher returns a JSON-RPC error
- **THEN** the client SHALL raise `RpcError` with the error's code, message, and data

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