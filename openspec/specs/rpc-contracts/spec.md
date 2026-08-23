# RPC Contracts

## Purpose

Declarative, statically typed RPC contracts shared between server and browser: `Procedure`, `StreamingProcedure`, and `Subscription` objects defined in dependency-neutral schema modules, bound to implementations at app startup with registration-time signature validation, and invoked from client code through a `RpcTransport`. Contracts make RPC calls fully type-checked with pyright (contract-name existence, parameter types, result and event inference) without code generation, and turn the schema module into the single source of RPC type truth.

## Requirements

### Requirement: Procedure contracts shall declare a typed single-result RPC call

The framework SHALL provide a `Procedure` contract class (importable from `webcompy.rpc`) declaring a named RPC procedure and its parameter and result types. `Procedure(name, params_type, result_type)` SHALL store the name and types and SHALL reject names starting with `_webcompy.` at construction. `params_type` SHALL be a dataclass type — the parameter value is sent over the wire as the JSON object it encodes to — and non-dataclass parameter types SHALL be rejected at construction. `procedure(transport, params)` SHALL return an `RpcCall[P, R]` (importable from `webcompy.rpc`) that is `Awaitable[R]`; `await procedure(transport, params)` SHALL invoke `transport.call(name, params, result_type=result_type)` and SHALL return a value of the declared result type. The contract SHALL contain no encoding or decoding logic — encoding, `meta` handling, and decoding SHALL remain in the transport layer. Construction of the `RpcCall` SHALL NOT perform I/O until awaited, and the same object SHALL be usable as an argument to `batch` and `notify`.

#### Scenario: Typed call through a contract

- **WHEN** `add = Procedure("add", AddParams, int)` and `await add(client, AddParams(2, 3))` is evaluated with a conforming transport
- **THEN** the transport SHALL receive `("add", AddParams(2, 3))` with `result_type=int`
- **AND** the call SHALL resolve to `5` as an `int`

#### Scenario: Procedure call returns an awaitable RpcCall

- **WHEN** `call_obj = add(client, AddParams(2, 3))` is evaluated
- **THEN** `call_obj` SHALL be an `RpcCall[AddParams, int]` that is awaitable
- **AND** `await call_obj` SHALL resolve to `5` as an `int`
- **AND** `call_obj` SHALL also be usable as an argument to `batch` and `notify`

#### Scenario: Reserved names are rejected at construction

- **WHEN** `Procedure("_webcompy.internal", P, R)` is constructed
- **THEN** an error SHALL be raised identifying the reserved name

#### Scenario: Contract construction validates type arguments

- **WHEN** `Procedure("add", P, R)` is constructed with a non-type `params_type` or `result_type`
- **THEN** an error SHALL be raised

#### Scenario: Non-dataclass parameter type is rejected at construction

- **WHEN** `Procedure("echo", str, str)` is constructed with a non-dataclass `params_type`
- **THEN** an error SHALL be raised stating parameter types must be dataclasses

### Requirement: StreamingProcedure contracts shall declare a call-scoped typed stream

The framework SHALL provide a `StreamingProcedure` contract class declaring a streaming RPC procedure (per the `rpc-streaming` capability) and its parameter and result element types. `params_type` SHALL be a dataclass type, as for `Procedure`. `streaming_procedure(transport, params)` SHALL invoke `transport.stream(name, params, result_type=result_type)` and SHALL return an `RpcStream[T]` where `T` is the declared element type. The returned stream SHALL NOT be awaited (it is the stream handle itself).

#### Scenario: Streaming call through a contract

- **WHEN** `produce = StreamingProcedure("produce", ProduceParams, Item)` and `it = produce(client, ProduceParams(2))` is evaluated with a conforming transport
- **THEN** `it` SHALL be an `RpcStream[Item]` produced by `client.stream("produce", ProduceParams(2), result_type=Item)`

### Requirement: Subscription contracts shall declare a shared infinite event stream

The framework SHALL provide a `Subscription` contract class declaring a subscription procedure (per the `rpc-websocket` capability) and its parameter and event types. `Subscription(name, params_type, event_type, replay_size=256)` SHALL store `replay_size` (default 256, `int` greater than or equal to 1, `bool` rejected) and `bind` SHALL flow it to the subscription's replay buffer. `params_type` SHALL be a dataclass type, as for `Procedure`. `subscription_contract(transport, params)` SHALL invoke `transport.subscribe(name, params, event_type=event_type)` and SHALL return an `RpcSubscription[E]` where `E` is the declared event type. The returned handle SHALL retain the cursor/rejoin/resync semantics of `rpc-websocket`.

#### Scenario: replay_size declared on the contract

- **WHEN** `ticker = Subscription("ticker", TickerParams, Tick, replay_size=10)` is constructed
- **THEN** the contract SHALL store `replay_size=10`
- **AND** binding it SHALL create a subscription buffer of size 10

#### Scenario: Subscription through a contract

- **WHEN** `ticker = Subscription("ticker", TickerParams, Tick)` and `sub = ticker(client, TickerParams("a"))` is evaluated with a conforming transport
- **THEN** `sub` SHALL be an `RpcSubscription[Tick]` produced by `client.subscribe("ticker", TickerParams("a"), event_type=Tick)`

### Requirement: notify shall send RpcCalls as fire-and-forget notifications

The framework SHALL provide a `notify(*calls: RpcCall)` free function (importable from `webcompy.rpc`) that sends 0 or more `RpcCall`s as JSON-RPC notifications (envelopes without `id`) in a single transport round-trip: over `RpcHttpClient` as one HTTP POST with a JSON array (or no request for 0 calls, returning `None`), over `RpcWsClient` as one WebSocket text frame with a JSON array (no `Future`s). All calls SHALL share the same transport instance; mixed transports SHALL raise `RpcError`. Empty input SHALL be a no-op with no I/O and no hydration transfer entry. Streaming or subscription `RpcCall`s SHALL be rejected. Notifications reuse the existing `dispatch_payload` batch wire as an id-less array (server returns `None` → `204` / no frame).

#### Scenario: Single notify

- **WHEN** `c = add(client, AddParams(1, 1))` and `await notify(c)` is evaluated with a conforming transport
- **THEN** one JSON-RPC notification SHALL be sent without `id`
- **AND** no result SHALL be returned

#### Scenario: Multiple notify as one array

- **WHEN** `c1 = add(client, AddParams(1, 0))` and `c2 = add(client, AddParams(2, 0))` and `await notify(c1, c2)` is evaluated
- **THEN** one HTTP POST with a JSON array of id-less envelopes (or one WebSocket array frame) SHALL be sent
- **AND** the server SHALL execute both procedures with no response body

#### Scenario: Empty notify is a no-op

- **WHEN** `await notify()` with no calls is evaluated
- **THEN** no I/O SHALL occur and `None` SHALL be returned

#### Scenario: Mixed transports are rejected in notify

- **WHEN** `c_http = add(http_client, AddParams(1, 0))` and `c_ws = add(ws_client, AddParams(1, 0))` and `await notify(c_http, c_ws)` is evaluated
- **THEN** `RpcError` SHALL be raised indicating mixed transports

#### Scenario: Streaming call is rejected in notify

- **WHEN** `c = produce(client, ProduceParams(2))` for a `StreamingProcedure` and `await notify(c)` is evaluated
- **THEN** `RpcError` SHALL be raised indicating streaming calls cannot be sent as notifications

#### Scenario: Subscription call is rejected in notify

- **WHEN** `c = ticker(client, TickerParams("a"))` for a `Subscription` and `await notify(c)` is evaluated
- **THEN** `RpcError` SHALL be raised indicating subscription calls cannot be sent as notifications

### Requirement: RpcTransport shall define the transport surface consumed by contracts

The framework SHALL define an `RpcTransport` protocol with the methods contracts consume: `call(method, params=None, *, result_type=None)`, `notify(method, params=None)`, `stream(method, params=None, *, result_type=None) -> RpcStream`, and `subscribe(method, params=None, *, event_type=None) -> RpcSubscription`. `RpcWsClient` SHALL implement all four methods. Transport implementations SHALL own all wire encoding and decoding: they SHALL encode contract params through the existing `encode_with_meta` machinery and SHALL send object-form JSON-RPC params (the params object itself, per the `json-rpc` decode rule). Contracts SHALL remain transport-agnostic. Public callers SHALL use `Procedure`/`batch`/`notify` with `RpcCall`, not `RpcTransport` directly.

#### Scenario: RpcWsClient conforms to the protocol

- **WHEN** an `RpcWsClient` is used as a contract transport
- **THEN** calls, streams, and subscriptions SHALL behave per the `rpc-websocket` and `rpc-streaming` capabilities

#### Scenario: Params travel as the object form

- **WHEN** a contract call sends a dataclass params instance
- **THEN** the transport SHALL place the `encode_with_meta` output of the instance in the envelope's `params` member (no wrapper object)

### Requirement: RpcHttpClient shall provide an HTTP transport for browser and server

The framework SHALL provide an `RpcHttpClient` (importable from `webcompy.rpc`) implementing `call`, `notify`, and `stream` over the HTTP JSON-RPC endpoint with the same SSR behavior as the retired module-level client functions: during SSR/SSG, calls SHALL dispatch in-process via the ASGI transport and SHALL be recorded in the hydration transfer cache, notifications SHALL dispatch in-process but SHALL NOT be recorded (HTTP `204` produces no transfer entry), and `stream` SHALL return the immediately-finished empty stream per `rpc-streaming`. `RpcHttpClient.subscribe` SHALL raise `RpcError` (subscriptions are WebSocket-only). `RpcHttpClient` SHALL require no constructor arguments, resolving the registry and ports from the current DI scope like the retired functions.

#### Scenario: HTTP call through RpcHttpClient bakes during SSR

- **WHEN** a component invokes `await add(http_client, AddParams(2, 3))` during SSR
- **THEN** no network I/O SHALL occur
- **AND** the response SHALL be recorded in the hydration transfer cache

#### Scenario: subscribe is rejected on RpcHttpClient

- **WHEN** `http_client.subscribe(...)` is invoked
- **THEN** `RpcError` SHALL be raised

### Requirement: RpcCall shall be the awaitable unit for Procedure calls, batch and notify

The framework SHALL provide an `RpcCall[P, R]` class (importable from `webcompy.rpc`) that is `Awaitable[R]`. `Procedure(transport, params)` SHALL return an `RpcCall` instance that captures the contract name, params, result type, and transport without performing I/O; `await` on the instance SHALL delegate to `transport.call` and SHALL be awaitable exactly once — awaiting the same instance a second time SHALL raise `RuntimeError` (`RpcCall already awaited`); `batch` and `notify` consume the call without prior await. `RpcCall` SHALL be the only accepted element type for `batch` and `notify`; streaming and subscription contracts SHALL NOT produce `RpcCall` and SHALL be rejected by `batch` and `notify`. `RpcCall` SHALL have no truth value: `bool(RpcCall)` and `len(RpcCall)` SHALL raise `TypeError`.

#### Scenario: RpcCall is awaitable once

- **WHEN** `c = add(client, AddParams(2, 3))` and `await c` is evaluated
- **THEN** the call SHALL be performed once and SHALL resolve to `5`

#### Scenario: Double-await is rejected

- **WHEN** `c = add(client, AddParams(2, 3))` and `await c` has already been evaluated and `await c` is evaluated again
- **THEN** `RuntimeError` SHALL be raised indicating the call was already awaited

#### Scenario: Truthiness is not available

- **WHEN** `bool(c)` or `if c:` or `c or fallback` is evaluated for an `RpcCall`
- **THEN** `TypeError` SHALL be raised indicating the call has no truth value

### Requirement: batch shall execute multiple RpcCalls in one round-trip

The framework SHALL provide a `batch(*calls: RpcCall, return_exceptions=False)` free function (importable from `webcompy.rpc`) that executes 0 or more `RpcCall`s in a single transport round-trip: over `RpcHttpClient` as one HTTP POST with a JSON array, over `RpcWsClient` as one WebSocket text frame with a JSON array, reusing the existing `dispatch_payload` batch path. 0 calls SHALL be a no-op returning `()` with no I/O and no hydration transfer entry. All calls SHALL share the same transport instance; mixed transports SHALL raise `RpcError`. Streaming or subscription calls SHALL be rejected. The function SHALL provide 0..6 heterogeneous overloads inferring `tuple[()]` / `tuple[R1, ..., Rn]` (gather-style) with a variadic fallback inferring `tuple[R, ...]`; with `return_exceptions=False` (default) the first per-call `RpcError` SHALL propagate as a raised exception, with `return_exceptions=True` each entry SHALL be `R | RpcError` and the tuple SHALL be returned in input order. Notifications (no `id`) SHALL NOT be batched via `batch` (use `notify` instead).

#### Scenario: Heterogeneous batch over HTTP

- **WHEN** `c1 = add(http_client, AddParams(1, 0))` and `c2 = get_user(http_client, GetUserParams(id=1))` and `await batch(c1, c2)` is evaluated
- **THEN** one HTTP POST with a JSON array SHALL be sent and the result SHALL be `tuple[int, User]` in input order

#### Scenario: Batch over WebSocket

- **WHEN** `c1 = add(ws_client, AddParams(1, 0))` and `c2 = add(ws_client, AddParams(2, 0))` and `await batch(c1, c2)` is evaluated over an open `RpcWsClient`
- **THEN** one WebSocket array frame SHALL be sent and the result SHALL be `tuple[int, int]` in input order

#### Scenario: return_exceptions surfaces per-call errors

- **WHEN** `c_ok = add(client, AddParams(1, 0))` and `c_missing = add(client, AddParams(999, 0))` targeting an unbound path and `await batch(c_ok, c_missing, return_exceptions=True)` is evaluated
- **THEN** the result SHALL be `(value, RpcError(...))` in input order without raising

#### Scenario: Mixed transports are rejected

- **WHEN** `c_http = add(http_client, AddParams(1, 0))` and `c_ws = add(ws_client, AddParams(1, 0))` and `await batch(c_http, c_ws)` is evaluated
- **THEN** `RpcError` SHALL be raised indicating mixed transports

#### Scenario: Streaming call is rejected in batch

- **WHEN** `c = produce(http_client, ProduceParams(2))` for a `StreamingProcedure` and `await batch(c)` is evaluated
- **THEN** `RpcError` SHALL be raised indicating streaming calls cannot be batched

#### Scenario: Subscription call is rejected in batch

- **WHEN** `c = ticker(ws_client, TickerParams("a"))` for a `Subscription` and `await batch(c)` is evaluated
- **THEN** `RpcError` SHALL be raised indicating subscription calls cannot be batched

#### Scenario: Empty batch is a no-op

- **WHEN** `await batch()` with no calls is evaluated
- **THEN** no I/O SHALL occur and `()` SHALL be returned

### Requirement: bind shall register contract implementations with signature validation

`ProcedureRegistry` SHALL provide a single `bind(contract, impl)` method that registers the implementation for a `Procedure`, `StreamingProcedure`, or `Subscription` contract, auto-dispatching on the contract kind. Calling `bind(contract)` without an implementation SHALL return a decorator that registers the decorated function. At registration, the implementation's signature SHALL be validated against the contract and any mismatch SHALL raise an error identifying the offending declaration:

- A `Procedure` implementation SHALL NOT be a generator function, SHALL take exactly one parameter whose annotation equals the contract's `params_type`, and SHALL have a return annotation equal to the contract's `result_type`. Non-generator functions with iterable return annotations SHALL be rejected.
- A `StreamingProcedure` implementation SHALL be a generator function with a subscripted iterable return annotation (per `rpc-streaming` detection) whose element type equals the contract's `result_type`.
- A `Subscription` implementation SHALL be an async generator function whose return annotation is a subscripted `AsyncIterator[T]` (or `AsyncGenerator[T, None]`) with `T` equal to the contract's `event_type`. Unannotated, unsubscripted, and mismatched element types SHALL be rejected.

For `Subscription`, the registry SHALL use `replay_size` from the contract (default 256) for the replay buffer. Name collisions and reserved `_webcompy.*` names SHALL be rejected as before. The registry SHALL continue to derive procedure metadata from the implementation's own annotations, which validation guarantees agree with the contract.

#### Scenario: bind registers a matching implementation

- **WHEN** `app.rpc.bind(add, _add)` is called where `_add(p: AddParams) -> int` matches the contract
- **THEN** the procedure SHALL be registered and callable through the dispatcher

#### Scenario: Parameter mismatch is rejected at registration

- **WHEN** a `Procedure("add", AddParams, int)` is bound to a function taking a different parameter type
- **THEN** `bind` SHALL raise an error naming the offending parameter

#### Scenario: Result mismatch is rejected at registration

- **WHEN** a `Procedure("add", AddParams, int)` is bound to a function returning `str`
- **THEN** `bind` SHALL raise an error naming the return annotation

#### Scenario: Generator bound to a Procedure is rejected

- **WHEN** a generator function is bound to a `Procedure` contract
- **THEN** `bind` SHALL raise an error directing to `StreamingProcedure`

#### Scenario: Non-generator bound to a StreamingProcedure is rejected

- **WHEN** a plain function is bound to a `StreamingProcedure` contract
- **THEN** `bind` SHALL raise an error stating streaming contracts require generator functions

#### Scenario: Subscription element mismatch is rejected at registration

- **WHEN** a `Subscription("ticker", TickerParams, Tick)` is bound to an async generator annotated `-> AsyncIterator[Other]`
- **THEN** `bind` SHALL raise an error naming the element type

#### Scenario: Unannotated subscription element is rejected at registration

- **WHEN** a `Subscription` contract is bound to an async generator whose return annotation is missing, bare, or `object`
- **THEN** `bind` SHALL raise an error requiring a subscripted element annotation

#### Scenario: Decorator form binds the decorated function

- **WHEN** `@app.rpc.bind(produce)` decorates an async generator function matching the contract
- **THEN** the function SHALL be registered exactly as with the two-argument form

### Requirement: Contract schema modules shall import only client-safe core

Contract objects SHALL be defined in dependency-neutral schema modules inside the app package that import only client-safe `webcompy` core modules (`webcompy.rpc`, dataclasses, typing, and sibling schema modules). Schema modules SHALL NOT import server-only modules (`webcompy_server`, server frameworks, or third-party server libraries); server implementations SHALL live in separate server-only modules that import the schema module. This guarantees contracts are importable in the browser bundle without dragging server dependencies.

#### Scenario: Schema module imports only client-safe core

- **WHEN** a schema module containing only contract definitions and core imports is shipped to the browser bundle
- **THEN** the module SHALL import successfully in the browser
- **AND** the bundle SHALL NOT include server-only dependencies

### Requirement: Contracts shall not require a DI scope or app context

Contract construction and invocation SHALL NOT require an active DI scope or app instance: contract objects SHALL be constructible at module import time and SHALL delegate all environment-dependent work to the explicitly passed transport. The app's `rpc` registry and ports SHALL be resolved inside the transport layer, not inside contracts.

#### Scenario: Contracts are constructible at module import time

- **WHEN** a schema module is imported before any app or DI scope exists
- **THEN** `Procedure`, `StreamingProcedure`, and `Subscription` objects SHALL construct without error
