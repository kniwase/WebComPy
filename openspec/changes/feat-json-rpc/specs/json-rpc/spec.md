# Spec: json-rpc

## ADDED Requirements

### Requirement: JSON-RPC 2.0 dispatcher
The framework SHALL provide a JSON-RPC 2.0 dispatcher as an ASGI endpoint, mounted by default at `/_webcompy-rpc` through the same mount mechanism as user-provided ASGI apps (and registrable at a custom path). The dispatcher insertion is framework-internal and SHALL NOT be subject to the user-mount collision validation defined by the `cli` capability. The dispatcher SHALL implement the JSON-RPC 2.0 specification: the `jsonrpc: "2.0"` member, `method`, optional `params` (by-position array or by-name object), `id`, single and batch requests, notifications (requests without `id`, producing no response body), and the standard error codes `-32700`, `-32600`, `-32601`, `-32602`, `-32603`. When no procedures are registered, the endpoint SHALL NOT be added to the route table.

#### Scenario: Single call
- **WHEN** a client POSTs `{"jsonrpc": "2.0", "method": "get_user", "params": {"id": 1}, "id": 1}` with a registered `get_user` procedure
- **THEN** the dispatcher SHALL invoke the procedure and respond with `{"jsonrpc": "2.0", "result": <value>, "id": 1}`

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
