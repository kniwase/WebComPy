# JSON-RPC (delta)

## MODIFIED Requirements

### Requirement: JSON-RPC 2.0 dispatcher

The framework SHALL provide a JSON-RPC 2.0 dispatcher as an ASGI endpoint, mounted by default at `/_webcompy-rpc` through the same mount mechanism as user-provided ASGI apps (and registrable at a custom path). The dispatcher insertion is framework-internal and SHALL NOT be subject to the user-mount collision validation defined by the `cli` capability. The dispatcher SHALL implement the JSON-RPC 2.0 specification: the `jsonrpc: "2.0"` member, `method`, optional `params` (by-position array or by-name object), `id`, single and batch requests, notifications (requests without `id`, producing no response body), and the standard error codes `-32700`, `-32600`, `-32601`, `-32602`, `-32603`. When no RPC contracts are bound, the endpoint SHALL NOT be added to the route table.

#### Scenario: Single call
- **WHEN** a client POSTs `{"jsonrpc": "2.0", "method": "get_user", "params": {"id": 1}, "id": 1}` with a bound `get_user` procedure
- **THEN** the dispatcher SHALL invoke the procedure and respond with `{"jsonrpc": "2.0", "result": <value>, "id": 1}`

#### Scenario: Positional params relying on defaults
- **WHEN** a client POSTs `{"jsonrpc": "2.0", "method": "add", "params": [5], "id": 1}` for a bound contract procedure
- **THEN** the dispatcher SHALL answer `-32602` (contract procedures take a single object parameter; positional array params do not map to parameters or defaults)

#### Scenario: Object params relying on dataclass defaults
- **WHEN** a client POSTs `{"jsonrpc": "2.0", "method": "add", "params": {"a": 5}, "id": 1}` for a bound procedure with signature `def _add(p: AddParams)` where `AddParams` declares `b: int = 0`
- **THEN** the dispatcher SHALL reconstruct `AddParams(a=5, b=0)` and invoke the procedure with it
- **AND** the response SHALL be `{"jsonrpc": "2.0", "result": 5, "id": 1}`

#### Scenario: Batch call
- **WHEN** a client POSTs an array of valid request objects
- **THEN** the dispatcher SHALL process each entry independently and SHALL return an array of per-entry responses (excluding notifications)

#### Scenario: Notification
- **WHEN** a client sends a request object without an `id`
- **THEN** the procedure SHALL execute and no response body SHALL be returned for that entry

#### Scenario: Unknown method
- **WHEN** a client calls an unbound method name
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

Procedures SHALL be plain Python functions (sync or async) bound to `Procedure` contracts via `ProcedureRegistry.bind(contract, impl)` (or the `bind(contract)` decorator form), per the `rpc-contracts` capability. Subscriptions SHALL be async generator functions bound to `Subscription` contracts, and streaming procedures SHALL be generator functions bound to `StreamingProcedure` contracts. `bind` SHALL validate that the implementation's annotations match the contract's declared types (parameter, result, or event element) and SHALL reject mismatches, unannotated declarations, name collisions, and reserved `_webcompy.*` names at registration time. Procedures SHALL have fully annotated parameters and return types; registrations with untyped parameters or `**kwargs` SHALL be rejected at registration time. The parameter schema SHALL derive from the function's type annotations; the result schema SHALL derive from the return annotation. Procedures may raise exceptions; unhandled exceptions SHALL map to error code `-32603` with a generic message (details logged server-side only).

#### Scenario: Contract binding registers a procedure

- **WHEN** a fully annotated async function is bound to a matching `Procedure` contract
- **THEN** it SHALL be callable via its registered name through the dispatcher

#### Scenario: Decorator registration
- **WHEN** a fully annotated function is decorated with `@app.rpc.bind(contract)` for a matching contract
- **THEN** it SHALL be registered exactly as with the two-argument `bind(contract, impl)` form

#### Scenario: Untyped procedure rejected

- **WHEN** a function with unannotated parameters is bound to a contract
- **THEN** binding SHALL raise an error identifying the offending parameters

#### Scenario: Contract mismatch rejected

- **WHEN** a function whose annotations disagree with the contract's declared types is bound
- **THEN** binding SHALL raise an error naming the mismatch

#### Scenario: Reserved name rejected

- **WHEN** a contract or binding targets a `_webcompy.*` method name
- **THEN** an error SHALL be raised

### Requirement: Server-side typed decoding with mandatory allowlist

Contract-bound procedures and subscriptions take exactly one parameter, whose schema is the contract's `params_type` (a dataclass). The dispatcher SHALL decode object-form `params` by treating the params object itself as the parameter value: `from_json(params_type, params, strict=True)`. Array-form `params` SHALL answer `-32602` for contract-bound procedures (there are no positional arguments to map). The dispatcher SHALL decode using schemas derived from the implementation's annotations — never from request content. Type restoration from request `meta` SHALL be limited to the closed set of built-in type tags plus types explicitly registered through an allowlist registration API. The dispatcher SHALL NOT import or resolve classes from client-controlled names under any circumstances.

#### Scenario: Typed params reconstruction
- **WHEN** a procedure bound to `def f(p: User) -> ...` is called with `params: {"name": "ann", ...}` (the `User` object form)
- **THEN** the procedure SHALL receive a reconstructed `User` instance
- **AND** extra keys in the payload SHALL be rejected with error `-32602` (strict decoding)

#### Scenario: Array-form params are rejected for contract procedures
- **WHEN** a contract-bound procedure is called with array-form `params`
- **THEN** the dispatcher SHALL respond with error `-32602`

#### Scenario: Unregistered type tag rejected
- **WHEN** request metadata references a type tag outside the closed set and not in the allowlist registry
- **THEN** the dispatcher SHALL respond with error `-32602` and SHALL NOT attempt class resolution

### Requirement: Typed browser client over FetchPort

The framework SHALL provide a typed HTTP client for JSON-RPC via the `RpcHttpClient` transport defined in the `rpc-contracts` capability; RPC calls SHALL be issued through `Procedure` contracts (`await add(http_client, params)`) via `RpcCall`, streaming calls through `StreamingProcedure` contracts, and multiple `Procedure` calls in one round-trip via `batch(*calls: RpcCall, return_exceptions=False)` (importable from `webcompy.rpc`; HTTP array POST and WebSocket array frame per the `rpc-contracts` capability, reusing the existing batch wire). The module-level `rpc.call`, `rpc.notify`, and `rpc.stream` functions SHALL NOT exist as public API (the `batch` name exists only as the typed `batch(*RpcCall)` helper). During SSR/SSG, calls and batch arrays SHALL dispatch self-site in-process via ASGI transport and results SHALL be recorded in the hydration transfer cache (bake) as a single array entry, with the `transfer=False` opt-out applying as for other self-site fetches. JSON-RPC error responses SHALL raise a dedicated `RpcError` carrying `code`, `message`, and `data`. Result decoding SHALL apply `from_json` with response `meta`.

#### Scenario: RPC during SSR is baked

- **WHEN** a component performs a contract-based RPC call during SSR against the same app's dispatcher
- **THEN** no network I/O SHALL occur
- **AND** the response SHALL be recorded in the hydration transfer cache so the browser replays it without re-calling

#### Scenario: Batch during SSR is baked as an array

- **WHEN** a component performs `await batch(add(http_client, p1), add(http_client, p2))` during SSR
- **THEN** no network I/O SHALL occur
- **AND** the single array POST SHALL be recorded in the hydration transfer cache so the browser replays it without re-calling

#### Scenario: Error mapping

- **WHEN** the dispatcher returns a JSON-RPC error
- **THEN** the client SHALL raise `RpcError` with the error's code, message, and data

#### Scenario: No module-level call/stream functions

- **WHEN** a module attempts to import `call`, `notify`, or `stream` from `webcompy.rpc`
- **THEN** the import SHALL fail (the names are not exported)
- **AND** `batch` SHALL be importable as `batch(*calls: RpcCall, return_exceptions=False)`

### Requirement: The dispatcher shall support a WebSocket transport

The dispatcher's core logic (envelope validation, batch handling, procedure invocation, error mapping, `meta` handling) SHALL be transport-neutral, shared by the HTTP endpoint and a WebSocket endpoint, with the contract-bound single object param rule per the `rpc-contracts` capability (array-form `params` SHALL answer `-32602`). The framework SHALL provide a Starlette WebSocket endpoint mounted through the same mount mechanism as the HTTP dispatcher, which SHALL feed each incoming text frame through the shared dispatch logic and SHALL write each response back as a text frame. The HTTP POST behavior SHALL be unchanged. The WebSocket endpoint SHALL additionally support server→client notification frames for subscription streams and SHALL clean up all per-connection subscription state when the socket closes.

#### Scenario: WebSocket single call

- **WHEN** a client sends `{"jsonrpc": "2.0", "method": "add", "params": {"a": 1, "b": 2}, "id": 1}` as a text frame for a bound contract procedure
- **THEN** the endpoint SHALL respond with `{"jsonrpc": "2.0", "result": 3, "id": 1}` as a text frame

#### Scenario: WebSocket array params are rejected

- **WHEN** a client sends `{"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1}` for a contract-bound procedure over WebSocket
- **THEN** the endpoint SHALL respond with error `-32602`

#### Scenario: Shared semantics with HTTP

- **WHEN** the same contract-bound procedure is invoked over HTTP POST and over WebSocket with object-form params
- **THEN** envelope validation, decoding, and error mapping SHALL behave identically

#### Scenario: Connection close cleans up subscriptions

- **WHEN** a socket with active subscription streams closes
- **THEN** the server SHALL terminate those streams and release their per-connection state

### Requirement: The HTTP client shall provide a typed stream call

The framework SHALL provide HTTP streaming through the `RpcHttpClient.stream` transport method defined in the `rpc-contracts` capability, invoked through `StreamingProcedure` contracts. The module-level `rpc.stream` function SHALL NOT exist as public API. The HTTP stream wire behavior SHALL be unchanged: a `"stream": true` envelope POST through the streaming fetch capability, `Content-Type` branching (a JSON body resolves as an ordinary JSON-RPC response and SHALL raise `RpcError` for error responses before returning; a `text/event-stream` body returns an `RpcStream` parsed with the `sse-parser` codec), and the `rpc-streaming` capability's item/error/done mapping.

#### Scenario: JSON-RPC error answered as JSON raises before iteration

- **WHEN** a streaming contract targets an unknown method and the dispatcher responds with a JSON-RPC error body
- **THEN** `RpcError` SHALL be raised by the contract invocation itself (no stream returned)

#### Scenario: SSE stream yields typed items

- **WHEN** `it = produce(http_client, ProduceParams(2))` for a bound streaming procedure is consumed
- **THEN** iteration SHALL yield the decoded `Item` instances and then finish

### Requirement: Subscription procedures shall be registrable with a bounded replay buffer

The framework SHALL provide subscription registration via `ProcedureRegistry.bind` with a `Subscription` contract (per the `rpc-contracts` capability), replacing `register_subscription`. All wire and lifecycle semantics SHALL be unchanged: the dispatcher SHALL assign a monotonically increasing `cursor` per event per stream, SHALL forward events to subscribers as notification frames, SHALL retain a bounded replay buffer per stream (default 256 events, configurable at registration via `replay_size`), SHALL honor rejoin requests carrying `last_cursor` by replaying buffered events with greater cursors before live delivery, and SHALL answer `resync_required` when `last_cursor` is older than the buffer's replayable range (older than the oldest buffered cursor minus one, i.e. when at least one missed event has been evicted).

#### Scenario: Rejoin within the buffer replays missed events

- **WHEN** a subscriber rejoins with `last_cursor=10` and the buffer holds cursors `8`–`30`
- **THEN** the server SHALL deliver cursors `11`–`30` before resuming live events

#### Scenario: Rejoin beyond the buffer requires resync

- **WHEN** a subscriber rejoins with a cursor older than the buffer's replayable range (at least one missed event has been evicted)
- **THEN** the server SHALL answer `resync_required` and SHALL NOT fabricate or silently skip events
