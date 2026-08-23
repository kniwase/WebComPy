# RPC Streaming

## Purpose

Defines finite, call-scoped streaming responses for RPC procedures: a generator-function procedure produces a bounded stream of typed results for a single call, consumed client-side as an async iterator with per-item typed decoding, explicit termination and error propagation, and cancellation on both transports.

## Requirements

### Requirement: Streaming procedures shall register from generator functions with an iterable return annotation

Streaming procedures SHALL register by binding a generator function to a `StreamingProcedure` contract via `ProcedureRegistry.bind` (per the `rpc-contracts` capability), replacing decorator/`register`-style registration. A procedure whose function is a generator function (async generator for `AsyncIterator[T]` / `AsyncIterable[T]` return annotations; sync generator for `Iterator[T]` / `Iterable[T]` return annotations) SHALL register as a streaming procedure. The result schema SHALL be the element type `T` extracted from the subscripted return annotation. Binding SHALL be rejected when the return annotation is unsubscripted (e.g. bare `AsyncIterator`), when a generator function's return annotation is not an iterable annotation, when a non-generator function declares an iterable return annotation, or when the extracted element type does not equal the contract's declared result type. Streaming procedures SHALL share the procedure namespace with ordinary procedures (name collisions rejected as today).

#### Scenario: Async generator registers with element schema
- **WHEN** an async generator function annotated `-> AsyncIterator[Item]` is bound to a `StreamingProcedure` contract declaring `Item`
- **THEN** the procedure SHALL be registered as streaming
- **AND** its result schema SHALL be `Item`

#### Scenario: Sync generator registers
- **WHEN** a generator function annotated `-> Iterator[int]` is bound to a `StreamingProcedure` contract declaring `int`
- **THEN** the procedure SHALL be registered as streaming with element schema `int`

#### Scenario: Unsubscripted iterable return annotation is rejected
- **WHEN** a generator function annotated `-> AsyncIterator` (no type argument) is bound to a `StreamingProcedure` contract
- **THEN** binding SHALL raise an error identifying the missing element type

#### Scenario: Non-generator function with iterable annotation is rejected
- **WHEN** a plain function (not a generator function) annotated `-> Iterator[int]` is bound to a `StreamingProcedure` contract
- **THEN** binding SHALL raise an error stating that streaming procedures require generator functions

#### Scenario: Element type mismatch with the contract is rejected
- **WHEN** a generator function annotated `-> AsyncIterator[Other]` is bound to a `StreamingProcedure` contract declaring a different element type
- **THEN** binding SHALL raise an error naming the element type

### Requirement: RpcStream shall expose typed async iteration with state and close semantics

The framework SHALL provide an `RpcStream` object returned by the HTTP and WebSocket stream client APIs. `RpcStream` SHALL be an `AsyncIterator[T]` yielding each result item decoded with the same typed codec as ordinary RPC results (`from_json` with the caller-provided `result_type`, plus transfer `meta` restoration). It SHALL expose `.state: Signal[RpcStreamState]` where `RpcStreamState` has exactly `OPEN`, `CLOSED`, and `FAILED` members: `OPEN` while the stream is active, `CLOSED` after normal exhaustion or explicit close, `FAILED` when the stream failed. `.close()` SHALL be idempotent, SHALL terminate the stream, and SHALL cancel the underlying transport. `RpcStream` SHALL support the context-manager protocol so `async with` closes it on exit. On a mid-stream error, `__anext__` SHALL raise `RpcError` (carrying the server-provided code, message, and data when available) and `.state` SHALL become `FAILED`. On normal exhaustion, iteration SHALL finish with `StopAsyncIteration` and `.state` SHALL become `CLOSED`.

#### Scenario: Typed items are decoded per item
- **WHEN** a stream of `{"n": 1}`-shaped items is consumed with `result_type=Item`
- **THEN** each yielded item SHALL be an `Item` instance

#### Scenario: Mid-stream error raises RpcError
- **WHEN** the server reports a mid-stream error with code `-32603`
- **THEN** the next `__anext__` SHALL raise `RpcError` with that code
- **AND** `.state.value` SHALL be `RpcStreamState.FAILED`

#### Scenario: Exhaustion finishes the iterator
- **WHEN** the server finishes the stream normally
- **THEN** iteration SHALL end with `StopAsyncIteration`
- **AND** `.state.value` SHALL be `RpcStreamState.CLOSED`

#### Scenario: close is idempotent and stops the stream
- **WHEN** `.close()` is called twice on an active stream
- **THEN** no exception SHALL be raised
- **AND** no further items SHALL be delivered

#### Scenario: async with closes on exit
- **WHEN** `async with stream(...) as s:` exits (normally or via `break`)
- **THEN** the stream SHALL be closed as if `.close()` had been called

### Requirement: Client close shall cancel the server-side generator

When the client closes an active stream (`.close()`, `async with` exit, or component destroy), the transport SHALL signal cancellation to the server (abort the HTTP fetch, or send the stream-cancel WebSocket notification) and the server SHALL stop the generator: async generators SHALL be `aclose()`d, sync generators SHALL be terminated at their next yield (via the async wrapper). The server SHALL NOT continue producing items after cancellation.

#### Scenario: Closing an HTTP stream aborts the fetch
- **WHEN** `.close()` is called on an active HTTP stream
- **THEN** the underlying fetch SHALL be aborted
- **AND** the server SHALL stop the generator

#### Scenario: Closing a WebSocket stream sends cancel
- **WHEN** `.close()` is called on an active WebSocket stream
- **THEN** the client SHALL send the stream-cancel notification for that stream
- **AND** the server SHALL stop the generator

### Requirement: Component-scoped streams shall be closed on destroy

A stream created inside component setup SHALL be closed automatically on component destroy (chained destroy hook), mirroring subscription cleanup.

#### Scenario: Component destroy closes the stream
- **WHEN** a component that started a stream is destroyed while the stream is active
- **THEN** the stream SHALL be closed and the server-side generator SHALL stop

### Requirement: SSR shall return an empty finished stream with a warning and no transfer

Outside the browser (SSR/SSG), the stream client APIs SHALL NOT perform network or in-process dispatch: they SHALL emit a `UserWarning` and SHALL return an immediately-finished empty stream with `state == CLOSED`. No stream state, items, or cursors SHALL be collected into the hydration transfer payload, and streaming calls SHALL NOT use the fetch transfer cache.

#### Scenario: SSG produces an empty stream
- **WHEN** a page using `rpc.stream(...)` is statically generated
- **THEN** no HTTP request SHALL be issued
- **AND** the returned stream's iterator SHALL be immediately empty with `state == CLOSED`
- **AND** the hydration payload SHALL contain no entry for the stream
